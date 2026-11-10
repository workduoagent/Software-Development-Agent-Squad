# 前端安全与可追溯性落地（React / Vite）

要求本身只有一份：[`docs/02-protocols/security-baseline.md`](../../../docs/02-protocols/security-baseline.md)（等保二级开发侧基线，机检编号：后端 S0xx、前端 F0xx）。
本文件只回答「前端能做到哪、做不到的是谁的活」，**不重复条款**。

## 一、先划清边界

| 基线域 | 前端义务 | 不属于前端 |
| --- | --- | --- |
| ID 身份鉴别 | 口令只走 HTTPS 请求体，不进 URL / 日志 / 埋点；登录失败提示不区分"账号不存在"与"口令错误"以外的细节（按契约文案） | 复杂度校验、锁定计数、双因素都在服务端 |
| AC 访问控制 | 守卫与权限点**只控制 UI 渲染**，是体验不是安全；不得因为"入口藏起来了"就认为接口安全 | 每个请求的鉴权判定在服务端（基线第三节已明写） |
| AU 安全审计 | 不产审计记录，但要保证可追溯：错误提示带 `traceId` 展示给用户以便对账；请求可被后端审计（不私自改 Header 里的身份字段） | 审计写入、留存、防篡改全在后端 |
| DP 数据保护 | 凭据与个人信息不落到浏览器持久化存储；展示走脱敏后的服务端字段 | 存储加密、脱敏口径由后端与契约决定 |
| SEC 代码安全 | XSS、开放重定向、动态执行、依赖漏洞、明文端点 | 服务端注入、文件上传校验 |

前端"自己写一份操作日志存 localStorage"不是审计——它可被用户与脚本任意删改，也不满足留存与保护要求，基线 AU-3 直接判不符合。**禁止实现**。

权限点与角色的字符串同样来自契约：路由守卫与按钮的权限判断值对应契约 `x-permissions.points` / `roles`（形态见 `docs/02-protocols/api-contract-spec.md` §8.1）。
契约里没有的权限点不要在前端"先加一个再说"——那会让 UI 权限与后端判定长期两套字典，走变更流程由 architect 补进契约。

## 二、凭据与登录态（F002）

- Token 只存**内存 store**（Redux / 状态容器），刷新页面后靠 **httpOnly Cookie** 会话恢复或重新登录；
  `localStorage` / `sessionStorage` 明文存 Token = XSS 一次性全拿走。
- 若业务确实需要"刷新不掉线"且后端没给 httpOnly Cookie：**上报由总架构师裁定**，不要在任务里自行选 localStorage。
- `Authorization: Bearer` 注入只在 `api/request.ts` 拦截器里做（业务代码不碰 Token）。
- 401 统一清态跳 `/login?redirect=...`；**`redirect` 必须校验为站内相对路径**，否则就是开放重定向。
- Token 不进 URL 查询串、不进埋点与错误上报的 payload、不进 `console`。

## 三、XSS 与动态内容（F001 / F005）

- 富文本渲染只能用 `dangerouslySetInnerHTML`，且**同一文件内必须先过 sanitizer**（`DOMPurify.sanitize`）；
  门禁按"文件里有 sanitize 痕迹"判定，宁可误报不漏报。
- 禁止 `innerHTML` 拼接、禁止把服务端返回的字符串当 HTML 插进 DOM、禁止 `eval` / `new Function` 执行接口数据。
- 外链 `target="_blank"` 一律带 `rel="noopener noreferrer"`（F006）。
- 下载/预览直链要走后端鉴权，前端不得凭资源 ID 拼出可分享的免鉴权 URL。

## 四、控制台与调试信息（F003）

- 构建配置**没有**剥掉 `console`：拦截器把 `console.warn` 当"桥未注册"的兜底信号，全局 `drop: ["console"]` 会把这个信号一起削掉。
  所以 console 纪律靠两件事：**代码里不打印用户数据**（F003 ERROR）+ 提测前清残留 `console.log`（F003 WARN）。
- 若项目明确要求生产包剥 console，改 `vite.config.ts` 的 esbuild 配置并**保留 warn 通道**（例如只 `drop: ['debugger']` + 自定义 `pure`），改完必须重新出包验证，不许只在报告里声称已剥。

## 五、端点与环境变量（F004）

- 业务端点一律 `https://`；`http://` 只允许 `localhost` / `127.0.0.1` 本地联调（已在门禁白名单）。
- 只有 `VITE_` 前缀会进包，因此**任何密钥都不允许放 `.env`**；后端凭据、内部服务地址、租户密钥出现即算事故。
- `.env.development` 里 `VITE_USE_MOCK=true` 是设计如此；`.env.production` 出现 true 会被 F007 拦下（出包带 Mock = 接口全是假数据）。

## 六、依赖与供应链（F008 / S009）

```bash
npm audit --omit=dev --audit-level=high     # 高危未处置不得提测
```

- lockfile 必须提交；新增依赖走任务卡片，禁止"顺手装一个包"。
- 扫描脚本判不了 CVE，这条只能在 CI / 提测前真实执行并把输出附进报告。

## 七、机检项一览（`scripts/check_security.sh`）

| 编号 | 检查 | 级别 | 对应基线 |
| --- | --- | --- | --- |
| F001 | `dangerouslySetInnerHTML` / `document.write` 所在文件无 sanitizer | ERROR | SEC-8 |
| F002 | web storage 写入凭据（两步判定：文件里同时出现 storage 写入与凭据语义，覆盖 `setItem(STORAGE_KEY, token)` 这类常量写法） | ERROR | SEC-8 / ID-3 |
| F003 | 控制台打印凭据/个人信息；残留 `console.log` | ERROR / WARN | DP-3 |
| F004 | 明文 `http://` 端点（本地联调白名单除外） | ERROR | ID-3 / DP-2 |
| F005 | `eval` / `new Function` 动态执行 | ERROR | SEC-4 |
| F006 | `target="_blank"` 缺 `rel="noopener noreferrer"` | WARN | SEC-8 |
| F007 | 非开发环境 `VITE_USE_MOCK=true` | WARN | 质量红线 |
| F008 | 依赖扫描提醒（脚本只钉命令，执行在 CI） | INFO | SEC-7 / S009 |

豁免：行尾 `// nosec-fe: 理由`。理由必须是"确经评估的非敏感用法"，空理由按未处理打回。

## 八、交付门禁（前端四条）

```bash
npm run typecheck                          # 0 errors
npm test 2>&1 | tee logs/test-run.log      # 全绿，Exit Code 0
bash scripts/check_security.sh src         # 期望 SECURITY CHECK PASSED，[INFO] 取证段一并带上
npm audit --omit=dev --audit-level=high    # 高危须处置或说明缓解
```

## 九、实测过的行为（别凭印象改脚本）

- 对 `skills/react-scaffold/assets/` 全量跑：PASSED，无 ERROR。
- 对提炼来源的旧项目 `we-edu-web/src` 跑：命中 **F002 ERROR**——`authSlice.ts` 把 Token 写进 `localStorage`（键名走常量，早期只看同一行的写法会漏，因此改成文件级两步判定）与 **F006 WARN**。这正是本基线改用内存 store 的原因，属于**已知偏差**，不是脚本误报。
- 合成用例覆盖 F001–F005 全部命中；合规样例（内存 store 取 Token + `https` 端点 + 主题写 localStorage）不误报。
