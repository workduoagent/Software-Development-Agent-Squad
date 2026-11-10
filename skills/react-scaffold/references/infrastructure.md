# 公共基础设施

## 1. 入口装配（main.tsx）

顺序不可乱：**mock 必须先于首次渲染装好**，否则首屏请求漏到真实后端。

```tsx
async function bootstrap() {
  if (import.meta.env.VITE_USE_MOCK === 'true') {
    const { setupMock } = await import('@/api/mock'); // 动态引入：生产构建整块不进产物
    setupMock();
  }
  createRoot(document.getElementById('root')!).render(
    <Provider store={store}>
      <ThemeProvider>   {/* ConfigProvider + AntdApp，提供静态方法上下文 */}
        <App>           {/* 应用壳：启动恢复 + FeedbackBridge */}
          <AppRouter />
        </App>
      </ThemeProvider>
    </Provider>,
  );
}
```

## 2. 请求封装（api/request.ts + types.ts）

契约基线：`Result<T> = { code: number; msg: string; data: T }`，`code === 200` 成功；字段是 **msg 不是 message**。

- 请求拦截：从 `appStore.getState()` 取 token 注入 `Authorization: Bearer`（React 外取 store 的标准方式）。
- 响应拦截：`unwrap()` 统一拆包——成功返回 `data`；失败弹 `toastError` 并抛 `BizError(code, msg)`；`responseType === 'blob'` 透传完整响应（下载场景要读 headers）。
- 401（HTTP 或业务码）：清登录态 → 跳 `/login?redirect=<当前地址>`。
- HTTP 错误码 → 中文提示映射表（400/403/404/429/500/502/503/504）；断网/超时给兜底文案。
- 类型收口：`get/post/put/del<T>(url, ...): Promise<T>` 统一出口，屏蔽 axios 签名与拆包后实际返回值的差异。
- `types.ts` 另备：`PageQuery`（pageNum 从 1 起 + pageSize）、`PageResult<T>`（list/total/pageNum/pageSize）、`IdString = string`（雪花 ID 防精度丢失）、错误码按域分段常量。

## 3. Mock 体系（api/mock/）

- `setupMock()`：`new MockAdapter(requestInstance, { onNoMatch: 'passthrough' })`——未命中规则真实发出，「哪些接口没接上」显式可见；幂等装配。
- **mock 走完整 axios 链路**（请求拦截 → 序列化 → mock adapter → 响应拦截），拦截器行为在 mock 下同样被验证；mock 返回同样的 Result 结构。
- 按域注册：`mock/{domain}.ts` 导出 `registerXxxMocks(adapter)`，在 `mock/index.ts` 统一调用。
- `mock/helper.ts` 工具箱：`ok/fail`（Result 构造）、`readBody`（已序列化的请求体还原）、`readBearerToken`（AxiosHeaders 取值防大小写）、`signMockToken`（三段式假 JWT，让解析/exp 链路真实可走）、`fingerprint`（种子数据指纹：本地假表与种子文件不一致时重新铺底，防"代码改了页面没变"）、`idFromUrl`、`queryParams`。

## 4. 全局反馈桥（api/feedback.ts + components/FeedbackBridge）

axios 拦截器在 React 树外，拿不到 `App.useApp()` 的 message 实例：

- `FeedbackBridge` 挂在 `<AntdApp>` 内，把 message 实例注册到模块级桥，不渲染 UI。
- 拦截器只调 `toastError/toastSuccess`；同文案 1500ms 窗口去重（并发失败防刷屏）；桥未注册时兜底 console.warn，不静默。
- **所有接口失败都必须有用户可见反馈**，不允许只在 console 报错。

## 5. Store（store/index.ts）

- 只放跨页面共享状态：theme / system / auth / user / menu。页面数据走 useRequest。
- 导出三件套：`appStore`（原始实例，供 axios 拦截器等 React 外环境）、`useAppDispatch` / `useAppSelector`（类型安全 hooks，组件内只用这两个）。
- `RootState = ReturnType<typeof appStore.getState>`；`devTools: import.meta.env.DEV`。

## 6. useRequest（页面级异步数据唯一入口）

```tsx
const { data, loading, error, refresh } = useRequest(() => get<User[]>('/users'), []);
```

- 内部 `cancelled` 标记防卸载/竞态 setState；`refresh()` 手动重拉；deps 变化自动重拉。
- 禁止在页面里手写 useEffect + setState 重复这套逻辑。

## 7. App 壳启动恢复（App.tsx）

刷新页面后的用户态恢复两段式：

1. 先用 JWT claims **同步**还原基础用户态（不闪屏）；token 格式异常直接清掉交给守卫跳登录。
2. 再异步调当前用户接口补全展示字段（昵称/头像等）；补全失败不阻断——真实鉴权失败由下次请求的 401 统一处理。

⚠️ effect 依赖陷阱：不要把 `isAuthenticated` 放进依赖——它在 effect 内被翻成 true 会触发重跑，cleanup 取消在途请求，导致展示字段永远补不全。用 `appStore.getState()` 读最新值。

## 8. JWT 工具（utils/jwt.ts，资产已通用化）

`parseTokenClaims<T>()`（base64url 解码 + UTF-8 修复，非法返回 null）、`isTokenExpired()`（预留 30s 时钟偏移）。仅用于 UI 展示控制，**不构成鉴权依据**。