import { invoke } from '@tauri-apps/api/core'

// 所有后端命令在此登记：命令名字面量散落会让 Rust 侧改名时前端追不到调用点。
export const COMMANDS = {
  ping: 'ping',
} as const

export function invokeCommand<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return invoke<T>(cmd, args)
}

// event 走动态 import：只有真正用到订阅的工程才会把 event 模块打进主包。
export async function listenEvent<T>(
  event: string,
  handler: (payload: T) => void,
): Promise<() => void> {
  const unlisten = await import('@tauri-apps/api/event').then((m) =>
    m.listen<T>(event, (e) => handler(e.payload)),
  )
  return unlisten
}
