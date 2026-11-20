# Rust 侧规范（src-tauri/）

## 1. 模块分层

| 位置 | 职责 |
| --- | --- |
| `main.rs` / `lib.rs` | 入口、命令注册（集中）、启动钩子 |
| `<modules>/` | 业务模块（自建） |
| `logging.rs` | tracing 初始化 |
| `fs_helper.rs` | 文件读写助手 |
| `net.rs` | HTTP 封装 |
| `db.rs` | 数据库连接（引擎侧） |

`main.rs` 只做一件事：调 `lib.rs` 的 `run()`。命令注册集中在 `lib.rs`，禁止散落到各模块。

## 2. 命令注册与插件注册完整模板

```rust
mod logging;
mod fs_helper;
mod net;

use serde::Serialize;

#[derive(Serialize)]
struct PingResult { pong: bool }

#[tauri::command]
fn ping() -> PingResult {
    PingResult { pong: true }
}

pub fn run() {
    logging::init();
    tauri::Builder::default()
        // 插件必须在此注册——用了哪些就注册哪些，顺序不敏感
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        // 以下两个初始化方式与普通插件不同（Builder 模式）
        .plugin(tauri_plugin_sql::Builder::default().build())
        .plugin(tauri_plugin_store::Builder::new().build())
        .invoke_handler(tauri::generate_handler![ping])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

`ping` 探活命令建议常留：新工程第一件事就是让前端调通它，用来隔离"壳没起来"与"我的命令有问题"两类故障。

## 3. 架构纪律（不变量）

1. **消息序列闭环**：每条调用 id 必有结果；事件契约只增不改，破坏性变更升版本。
2. **终态铁律**：不挂死、不丢锁、不残留孤儿任务；长任务异步 + 可取消。
3. **能力事实源**：能力可用性由注册表决定，prompt 与注释不能替代注册。
4. **插件必须注册 + 必须授权**：见 `plugins-and-permissions.md`，两者缺一不可。
5. **SQL 幂等**：所有 DDL 可重跑；SQL 集中在前端 `core/mapper/` 与 `core/db/`，Rust 侧直读 DB 仅限引擎内部。
6. **日志**：用 `tracing`，带关键 id 可排障；前端关键链路可经 `log_frontend` 命令透传到同一份日志，避免桌面场景两份日志各说各话。
7. **异步任务必须有超时 + 兜底决策**，禁止无限等待；`tokio` features 按 `sync rt time process` 开，不要 `full`。

## 4. 日志初始化

```rust
use tracing_subscriber::{fmt, EnvFilter};

pub fn init() {
    let filter = EnvFilter::try_from_env("APP_LOG")
        .unwrap_or_else(|_| EnvFilter::new("info"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .init();
}
```

生产形态须加 `tracing-appender` 滚动文件，落 `AppData`/`~/Library/Logs` 下，且**日志内不得出现凭据、完整手机号/身份证/银行卡**（脱敏走统一工具，禁止手写截断）。

## 5. 工具链与自检

| 检查 | 命令 | 判据 |
| --- | --- | --- |
| 编译门禁 | `cd src-tauri && cargo check` | 改动必过，0 error |
| 逻辑测试 | `cargo test` | 涉逻辑必跑并留日志 |
| 依赖 | 只改 `Cargo.toml` | AI 不执行 `cargo add` / `cargo install` |

红线：

- 禁止插件拼任意 shell（子命令白名单 + `shell=false`）。
- `unsafe` 必须带理由注释，且属总架构师评审面。
- 命令返回值与 `types/core.d.ts` 同批改：改了 struct 不改 TS 类型，按缺陷处理，不接受"运行时没问题"。

## 6. 提测前自检

- [ ] `cargo check` / `cargo test` 通过并留日志路径
- [ ] 命令与事件契约文档已同步
- [ ] 新增插件已注册 + 权限已声明
- [ ] 取消/超时路径有效、无孤儿任务
- [ ] SQL 变更幂等可重跑
- [ ] `types/core.d.ts` 与 Rust struct 逐字段一致（含 `Option` → `T | null`、`serde(rename_all)`）
