/**
 * 全局反馈桥：axios 响应拦截器运行在 React 组件树之外，拿不到 App.useApp() 的 message 实例。
 * 由 FeedbackBridge 挂载时注册实例，拦截器经 toastError / toastSuccess 弹提醒，保证接口异常都有可见反馈。
 */
import type { MessageInstance } from 'antd/es/message/interface';

/** 由 FeedbackBridge 在挂载时注册，未注册前调用会被安全忽略 */
let messageApi: MessageInstance | null = null;

/** 同一文案在窗口期内只弹一次：并发失败时防刷屏。只记最后一条，不做全量表 */
const DEDUP_WINDOW_MS = 1500;
let lastText = '';
let lastAt = 0;

export function registerFeedbackApi(api: MessageInstance): void {
  messageApi = api;
}

export function unregisterFeedbackApi(): void {
  messageApi = null;
}

/** 同文案且在窗口期内判为重复；否则刷新记录的文案与时间 */
function isDuplicate(text: string): boolean {
  const now = Date.now();
  if (text === lastText && now - lastAt < DEDUP_WINDOW_MS) {
    return true;
  }
  lastText = text;
  lastAt = now;
  return false;
}

/** 全局错误提醒：所有接口失败都应经过这里 */
export function toastError(text: string): void {
  const msg = text || '操作失败';
  if (isDuplicate(msg)) return;
  if (messageApi) {
    messageApi.error(msg);
  } else {
    // 兜底：桥未挂载（极早期失败）时直接 console，避免静默
    console.warn('[feedback:error]', msg);
  }
}

/** 全局成功提醒：供缺少页面级成功提示的写操作使用 */
export function toastSuccess(text: string): void {
  const msg = text || '操作成功';
  if (isDuplicate(msg)) return;
  if (messageApi) {
    messageApi.success(msg);
  } else {
    console.warn('[feedback:success]', msg);
  }
}
