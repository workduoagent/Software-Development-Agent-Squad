# IPC 封装与 Rust↔TS 类型契约

## 1. 唯一入口

业务代码只从 `core/ipc` 调后端，禁止裸 `invoke`——命令名散落字符串无法对账，改名时 `tsc` 也追不到调用点。

```ts
// src/core/ipc/index.ts
import { invoke } from '@tauri-apps/api/core'

/** 所有后端命令在此登记，避免散落字符串 */
export const COMMANDS = {
  // ping: 'ping',
} as const

export function invokeCommand<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return invoke<T>(cmd, args)
}

/** 订阅后端事件，返回取消订阅函数 */
export async function listenEvent<T>(
  event: string,
  handler: (payload: T) => void
): Promise<() => void> {
  const unlisten = await import('@tauri-apps/api/event').then((m) =>
    m.listen<T>(event, (e) => handler(e.payload))
  )
  return unlisten
}
```

```ts
// ✅ 正确
import { invokeCommand } from '@/core/ipc'
const data = await invokeCommand<MyType>('get_items', { id: 1 })

// ❌ 禁止：业务代码裸调 invoke
import { invoke } from '@tauri-apps/api/core'
```

## 2. 类型契约铁律

所有与 Rust 交互的接口类型，**必须与 Rust 侧 `struct` 字段严格对齐**（名称、类型、可选性一一对应），统一维护在 `types/core.d.ts` / `types/database.d.ts`。

原因：Tauri 的前后端类型转换发生在运行时，TypeScript **无法在编译期发现**字段名拼写不一致——只能在运行时拿到 `undefined`。把契约集中到类型文件，改 Rust 时同步改类型，才能在 IDE 里立刻看到所有受影响调用点。

```ts
// types/core.d.ts —— 与 Rust struct ItemInfo 字段严格对齐
export interface ItemInfo {
  id: string
  name: string
  createdAt: number    // Rust: i64 epoch 毫秒
  extra: string | null // Rust: Option<String>
}
```

### 类型映射表

| Rust | TypeScript | 备注 |
| --- | --- | --- |
| `String` / `&str` | `string` | |
| `i64` / `u64` | `number` | 超 `Number.MAX_SAFE_INTEGER` 须改 `string` 传输 |
| `f64` | `number` | |
| `bool` | `boolean` | |
| `Option<T>` | `T \| null` | serde 默认序列化为 `null`，不是 `undefined` |
| `Vec<T>` | `T[]` | |
| `HashMap<String, V>` | `Record<string, V>` | |
| `chrono::DateTime` | `number` | 统一 epoch 毫秒，ISO 只在 mapper 层互转 |
| `serde(tag = "type")` 枚举 | 判别联合 | 判别字段名两侧必须一致 |

Rust 侧默认按字段名原样序列化；若 Rust 用 `snake_case` 而 TS 用 `camelCase`，必须在 struct 上加 `#[serde(rename_all = "camelCase")]` 并把它写进契约，否则静默拿到 `undefined`。

## 3. 命令与事件的契约口径

- 命令（`invoke`）＝请求-响应；事件（`emit` / `listen`）＝单向推送。二者都属契约，**必须先写契约再实现**。
- 事件契约**只增不改**：新增字段可以，改语义或删字段属破坏性变更，须升版本并走总架构师决策。
- 桌面工程不套 Web 的 `Result<T> = {code,msg,data}`（裁决见 SKILL.md #3）：Rust 命令返回 `Ok(data)` / `Err(AppError)`，前端在 `core/ipc` 统一 catch 后转 `useNotify()`。错误码枚举仍须在契约与 `types/` 里显式定义，供 QA 断言。

## 4. 数据层 mapper 范式

SQL 全部封装在 `core/mapper/`，页面不接触 SQL 细节：

```ts
// core/mapper/item-mapper.ts
import { invokeCommand } from '@/core/ipc'

export async function listItems(): Promise<Item[]> {
  return invokeCommand<Item[]>('list_items')
}
```

直接走 `tauri-plugin-sql` 时同层封装，遵守：

- 建表语句唯一写在 `core/db/`（或 `assets/sql/init.sql`），**mapper 内禁止 `CREATE TABLE`**——多次启动重复建表会报错。
- 占位符用 `?`，参数走数组绑定，禁止字符串拼接（注入面）。
- 时间统一 epoch 毫秒，ISO 在 mapper 层互转。
- **DDL 变更红线**：`ALTER TABLE` 后 `tsc` 查不出占位符错位，必须人工核对每个 `INSERT INTO` 的三要素——列清单 / `VALUES` 的 `?` 数量 / 参数数组长度，三者相等且顺序一致。
