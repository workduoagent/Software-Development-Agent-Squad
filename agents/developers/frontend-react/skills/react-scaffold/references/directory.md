# 目录设计

## 工程蓝图

```
project-root/
├── index.html                  # 入口 HTML（#root 容器）
├── package.json
├── vite.config.ts              # alias @ / scss 注入 / dev 代理 / 分包
├── tsconfig.json               # 项目引用（app + node 两份）
├── tsconfig.app.json           # src 严格类型检查
├── tsconfig.node.json          # vite.config.ts 类型检查
├── .env.development            # VITE_ 前缀，可提交，禁密钥
├── .env.production
└── src/
    ├── main.tsx                # 入口：mock → Provider 链 → Router
    ├── App.tsx                 # 应用壳：启动期用户态恢复、全局桥挂载
    ├── vite-env.d.ts           # ImportMetaEnv 类型声明
    ├── api/
    │   ├── request.ts          # axios 实例 + 拦截器 + get/post/put/del
    │   ├── types.ts            # Result / BizError / 错误码 / 分页 / IdString
    │   ├── feedback.ts         # 全局反馈桥（React 外弹提示）
    │   ├── modules/            # 业务接口函数，按域一个文件
    │   ├── schema/             # 契约类型定义，与 modules 按域对齐
    │   └── mock/               # 开发期 mock：index.ts 装配 + helper.ts + 按域模块
    ├── components/             # 跨页通用组件（FeedbackBridge / PageContainer / UserAvatar）
    ├── hooks/                  # 通用 hooks（useRequest / useTheme / useAuth / usePermission）
    ├── layout/
    │   ├── admin/              # 管理端布局（侧栏菜单 + 内容浮岛）
    │   ├── portal/             # 用户端布局（顶栏胶囊导航 + 内容区）
    │   └── shared/             # 双端共用（BrandMark / ThemeToggle / useUserMenu / icons）
    ├── pages/                  # 页面目录：每页一个文件夹，index.tsx + index.scss 同置
    ├── router/
    │   ├── routes.ts           # 壳路由表 + AppRouteMeta（纯数据，防循环引用）
    │   ├── router.tsx          # withGuards 装配 + 路由模式选择
    │   ├── AuthGuard.tsx       # 登录/过期/角色/权限点守卫
    │   ├── DynamicView.tsx     # 菜单驱动的动态路由解析
    │   ├── views.ts            # 页面组件注册表（componentCode → lazy 组件）
    │   ├── fallbacks.tsx       # PageLoading / Forbidden（独立文件防循环依赖）
    │   └── index.tsx           # RouterProvider 出口
    ├── store/
    │   ├── index.ts            # configureStore + typed hooks + appStore 原始实例
    │   ├── ThemeProvider.tsx   # 主题运行时唯一执行者
    │   └── slices/             # theme / system / auth / user / menu
    ├── styles/
    │   ├── theme.css           # 颜色唯一真源（.light / .dark CSS 变量）
    │   ├── variables.scss      # sass 变量映射 + mixin（全局注入，零规则输出）
    │   ├── global.scss         # 全局基础样式与工具类
    │   └── page-loading.scss   # 路由懒加载兜底
    └── utils/                  # 纯函数工具（jwt 解析等）
```

## 分层职责

| 层 | 职责 | 禁止 |
| --- | --- | --- |
| `api/modules` | 声明接口函数（url + 类型），一行一个调用 | 写业务逻辑、直接 import axios |
| `api/schema` | 与冻结契约对齐的 TS 类型 | 手写与契约漂移的类型 |
| `api/mock` | 按域注册 mock 规则，返回 Result 结构 | 在业务代码里写 mock 分支 |
| `pages` | 页面组装与页面级状态（useRequest） | 把页面数据塞进 Redux |
| `components` | 无业务归属的通用组件 |  import 业务 store slice |
| `layout` | 导航框架与 Outlet | 写页面业务 |
| `store/slices` | 跨页共享状态 | 放单页数据 |

## 命名与组织约定

- 页面：`src/pages/{PageName}/index.tsx` + 同目录 `index.scss`；页面样式用根类名包裹防泄漏。
- 接口三件套按域对齐：`modules/user.ts` ↔ `schema/user.ts` ↔ `mock/user.ts`。
- 通用组件一个目录：`components/{Name}/index.tsx`（+ 可选 `index.scss`）。
- 路径一律 `@/` 别名（`src/`），tsconfig `paths` 与 vite `resolve.alias` 必须同步。