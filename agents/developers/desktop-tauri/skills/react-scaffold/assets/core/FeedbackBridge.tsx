/**
 * 全局反馈桥：挂在 <AntdApp> 内部，把 App.useApp() 的 message 实例注册到 api/feedback.ts，
 * 供 axios 拦截器等 React 外的调用方弹全局提醒。本组件不渲染 UI。
 */
import { useEffect } from 'react';
import { App } from 'antd';
import { registerFeedbackApi, unregisterFeedbackApi } from '@/api/feedback';

export default function FeedbackBridge() {
  const { message } = App.useApp();

  useEffect(() => {
    registerFeedbackApi(message);
    return () => unregisterFeedbackApi();
  }, [message]);

  return null;
}
