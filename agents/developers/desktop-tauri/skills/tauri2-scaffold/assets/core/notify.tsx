import { App } from 'antd'

// 静态 import { message } from 'antd' 会脱离 <App> 上下文：主题不跟随、位置被顶栏遮挡。
export function useNotify() {
  const { message, notification, modal } = App.useApp()
  return { message, notification, modal }
}
