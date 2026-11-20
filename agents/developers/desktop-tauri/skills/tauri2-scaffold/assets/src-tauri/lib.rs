mod logging;

use serde::Serialize;

#[derive(Serialize)]
struct PingResult {
    pong: bool,
}

// 探活命令常留：用它隔离「壳没起来」与「我的命令有问题」两类故障。
#[tauri::command]
fn ping() -> PingResult {
    PingResult { pong: true }
}

pub fn run() {
    logging::init();
    tauri::Builder::default()
        // 用了哪些插件就注册哪些；漏注册的症状是前端报 plugin not found。
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        // sql 与 store 是 Builder 模式，写 ::init() 编译不过。
        .plugin(tauri_plugin_sql::Builder::default().build())
        .plugin(tauri_plugin_store::Builder::new().build())
        .invoke_handler(tauri::generate_handler![ping])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
