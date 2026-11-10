# 测试基线（vitest + Testing Library）

单测是交付门禁的一部分（frontend-react prompt §三）：无全绿日志的交付 PM 必打回。

## 工具链（已入 assets/config/package.json 基线）

| 包 | 版本基线 | 用途 |
| --- | --- | --- |
| vitest | ^3.0.0 | 测试运行器（复用 vite.config.ts，jsdom 环境） |
| @vitest/coverage-v8 | ^3.0.0 | 覆盖率（默认门槛 70%） |
| jsdom | ^26.0.0 | 浏览器环境模拟 |
| @testing-library/react | ^16.2.0 | 组件渲染与查询（用户视角） |
| @testing-library/user-event | ^14.6.0 | 交互模拟（点击/输入） |
| @testing-library/jest-dom | ^6.6.3 | DOM 断言扩展（toBeInTheDocument 等） |
| axios-mock-adapter | ^2.1.0 | 复用开发期 mock 体系拦截请求 |

## 目录与命名

- 测试文件统一放项目根 `tests/`，结构镜像 `src/`：`src/pages/UserList/index.tsx` → `tests/pages/UserList.test.tsx`。
- 全局初始化 `src/test/setup.ts`（复制 `assets/testing/setup.ts`）：jest-dom 扩展 + 每用例后 cleanup。
- vitest 配置在 `vite.config.ts` 的 `test` 块（environment/setupFiles/include/coverage 已配好，勿另建 vitest.config.ts 造成双源）。

## 必测清单（每任务最低要求）

1. **异步组件四态闭环**：Loading / Empty / Error / Success 全覆盖，Error 态必须测「重试后恢复」路径（示范见 `assets/testing/example.test.tsx`）。
2. **表单**：必填校验、格式校验（与契约 schema 约束一致）、防重复提交（提交中按钮 disabled）。
3. **api 层契约一致性**：用 MockAdapter 断言请求 method/path/body 与冻结契约一致、Result 拆包正确、错误码分支（401 跳登录等）行为正确。
4. **纯函数 utils**（jwt 解析、格式化等）：正向 + 边界 + 非法输入。

## 纪律

- 单测禁止发真实网络请求：只用独立 axios 实例挂 MockAdapter，或复用项目 `src/api/mock` 体系。
- 断言用户可见行为（文本 / role / 可访问性标签），不断言组件实现细节（state 值、内部函数名）。
- **禁止快照测试**：脆且无 review 价值。
- `example.test.tsx` 是教学 demo，参考写法后替换为业务测试，禁止原样留在交付中。
- 覆盖率是门槛不是目标：先满足必测清单，再谈数字；门槛可按项目 Tech Spec 上调（改 vite.config.ts `test.coverage.thresholds`）。

## 门禁与凭证（与 PM 物理验收对齐）

交付前必须依次执行并留存真实输出：

```bash
npm run typecheck                        # 0 errors
npm test 2>&1 | tee logs/test-run.log    # 全绿，Exit Code 0
npm run coverage                         # 任务卡要求覆盖率时执行
bash scripts/check_security.sh src       # 前端安全机检 F001–F008（SEC-8 / DP-3 / 凭据存储），必须 SECURITY CHECK PASSED
```

日志物理文件路径写进提测报告的「验证凭证」节（模板见 `agents/developers/frontend-react/prompt.md` §五）。

> 环境坑：若 `npm install` 提示 esbuild 的 install script 被 allow-scripts 拦截（vitest/vite 依赖 esbuild 二进制），执行 `npm approve-scripts esbuild` 后重新 `npm install`，否则 vitest 启动即报模块加载错误。

## 可复制资产

| 资产 | 复制到项目位置 |
| --- | --- |
| `assets/testing/setup.ts` | `src/test/setup.ts` |
| `assets/testing/example.test.tsx` | `tests/example.test.tsx`（教学用，交付前替换为业务测试） |
