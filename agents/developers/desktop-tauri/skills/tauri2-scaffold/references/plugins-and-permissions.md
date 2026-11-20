# 插件注册与 capability 权限

## 1. 铁律：注册 ≠ 授权，两处都要配

Tauri 2 的每个插件必须在 `lib.rs` 的 `Builder` 链上**显式注册**，且必须在 `src-tauri/capabilities/default.json` 里**声明权限**，两者缺一不可。

| 只做了 | 症状 |
| --- | --- |
| 注册了插件、没配权限 | 前端调用报 `xxx not allowed` |
| 配了权限、没注册插件 | 前端调用报 `plugin not found` |

这是桌面工程最常见、也最难被静态检查发现的一类缺陷（当前无机检脚本覆盖，见 SKILL.md 未覆盖清单 #1/#2）。

## 2. 注册写法速查

| 插件 | 注册写法 |
| --- | --- |
| `fs` / `dialog` / `opener` / `notification` / `shell` / `http` / `log` | `tauri_plugin_xxx::init()` |
| `sql` | `tauri_plugin_sql::Builder::default().build()` |
| `store` | `tauri_plugin_store::Builder::new().build()` |

⚠️ `sql` 与 `store` 是 Builder 模式，写 `::init()` **编译不过**。

## 3. 前端依赖清单

```json5
// package.json
"dependencies": {
  "@tauri-apps/api": "^2",
  "@tauri-apps/plugin-sql": "^2",         // SQLite
  "@tauri-apps/plugin-fs": "^2",          // 文件读写
  "@tauri-apps/plugin-dialog": "^2",      // 系统对话框
  "@tauri-apps/plugin-opener": "^2",      // 打开外部链接/路径
  "@tauri-apps/plugin-http": "^2",        // 前端直发 HTTP
  "@tauri-apps/plugin-notification": "^2",// 系统通知
  "@tauri-apps/plugin-store": "^2"        // 键值存储
}
```

只登记需要的那几项。**新增依赖只改 `package.json` / `Cargo.toml`，AI 与脚本不执行安装命令**。

## 4. 权限声明：最小权限原则

`capabilities/default.json` 按"这个窗口实际会调什么"逐项声明，不要图省事开通配。判据：

1. 未使用的插件权限必须删掉——权限即攻击面（对应安全基线「六 入侵防范」）。
2. `fs` 权限必须限定到具体 scope 路径，禁止 `$APPDATA/**` 一把梭。
3. `shell` / 执行外部程序类能力默认禁止；确需时子命令走白名单且 `shell=false`，不接受"先开着方便调试"。
4. `http` 权限若开放，域名白名单须写进契约文档，与 `core/config` 的 `API_BASE` 一致。
5. 每次新增插件权限都是一次契约变更，走 PM 登记与总架构师确认，不得由开发自行加。

完整模板见 `assets/src-tauri/capabilities-default.json`。

## 5. 交付前核对动作

对照本表逐条打勾，缺一项不得提测：

- [ ] §2 表里本项目用到的每个插件，`lib.rs` 都有对应 `.plugin(...)`
- [ ] 每个用到的插件，`capabilities/default.json` 都有对应权限项
- [ ] 没有"开了但没用"的权限
- [ ] `sql` / `store` 用的是 Builder 写法而非 `::init()`
- [ ] `Cargo.toml` 里插件 crate 与 `package.json` 里 `@tauri-apps/plugin-*` 版本对得上
