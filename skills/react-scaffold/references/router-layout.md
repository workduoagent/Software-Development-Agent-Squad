# 路由与布局体系

## 路由设计：壳路由 + 菜单驱动动态路由

路由表只保留**壳**：登录页、用户端布局（`/`）、管理端布局（`/admin`）、404。业务页面不逐条登记，壳下 `index` + `*` 交给 DynamicView 按 pathname 反查菜单数据渲染。

为什么这么做：

1. `createBrowserRouter` 的路由表创建后不宜增删，逐条 addRoute 会让整棵路由重挂载、切页丢状态；只留 `*` 则菜单怎么改都不碰 router。
2. 「新建菜单立即可访问」天然成立，无需刷新或重建路由。
3. **动态的是入口和层级，不是页面内容**：渲染哪个组件由 `router/views.ts` 注册表决定，未注册的 componentCode 落占位页（「先挂入口、页面后补」是常态）。

菜单数据契约（后端/菜单管理提供）：`path`、`name`、`icon`、`componentCode`、`permission`、`menuType`（目录/页面/外链）、`url`、`terminal`（PORTAL/ADMIN）。`/admin` 前缀归管理端，其余归用户端。

## 文件分工（防循环依赖是关键约束）

| 文件 | 职责 | 约束 |
| --- | --- | --- |
| `routes.ts` | 壳路由表 + `AppRouteMeta` + HOME 常量 | 纯数据模块，不 import 守卫/组件 |
| `router.tsx` | `withGuards` 递归装配 + 模式选择 | 见下 |
| `AuthGuard.tsx` | 登录/过期/角色/权限守卫 | 只控制 UI 渲染 |
| `DynamicView.tsx` | 菜单反查 → 渲染判定 | 被路由懒加载，**禁止反向 import router.tsx** |
| `fallbacks.tsx` | PageLoading / Forbidden | 独立成文件供两处复用，防循环 |
| `views.ts` | componentCode → lazy 组件注册表 | 新页面在此登记一行 |
| `index.tsx` | RouterProvider 出口 | — |

## withGuards 装配（router.tsx）

- 递归遍历路由表：lazy 路由包装为 `AuthGuard(meta) → Suspense(PageLoading) → 页面`，守卫逻辑全团队只写这一遍。
- lazy 路由必须设 `hydrateFallbackElement`，否则数据路由在懒加载期间控制台告警。
- 模式：`VITE_ROUTER_MODE` 选 `createBrowserRouter` / `createHashRouter`；另导出 `createTestRouter`（createMemoryRouter）供单测/SSR。

## AppRouteMeta（仅静态路由生效）

`{ title?: string; public?: boolean; permission?: string; roles?: string[] }`

动态页面的权限在 DynamicView 判（它才拿得到菜单行）；静态 handle 拿不到。

## AuthGuard 规则

1. `meta.public` 免登录（登录页、404）。
2. 无 token / token 过期（前端读 exp 提前判）→ 清 token 跳 `/login?redirect=...`。
3. 已登录但角色（任一命中）/权限点不匹配 → 渲染 403；超管不受限。
4. `document.title` 同步：只在当前路由自己声明了 title 时才写——守卫逐层嵌套，父级也写会在子级之后把标题冲掉（effect 子先父后）。

## DynamicView 判定顺序（顺序不可乱）

菜单未加载 → PageLoading（不能提前判 404）→ 查不到 path → 404 → 权限点不符 → 403 → 外链类型 → IFrameView → 注册表取组件（Suspense 包裹）。标题跟着菜单名写（handle 为空，与 AuthGuard 不冲突）。

## 布局体系（layout/）

- **admin/**：左侧可折叠 Sider（Logo + Menu + 底部折叠/主题/用户区）+ 右侧内容浮岛。菜单 key 约定：叶子用 path（全局唯一、选中态直接对 pathname），目录退菜单 ID（只用于展开）。深链接刷新时要把所属分组并入 openKeys（只并入不清空，保留用户手动展开）。
- **portal/**：一行顶栏（品牌 + 胶囊导航 + 主题/头像）+ 内容区。导航选中块用滑动指示器：ResizeObserver 测量，视口坐标差**补回 scrollLeft** 才是内容坐标（否则横向滚动后错位）。
- **shared/**：BrandMark、ThemeToggle、useUserMenu、图标映射等双端共用件。
- 内容区 `key={location.pathname}` 强制换页重挂载，页面进入动画才会重放。
- 品牌名统一读 `VITE_APP_BRAND || VITE_APP_TITLE`，两端同源。

## PageContainer（components/）

菜单页统一容器，只管内容区尺寸与纵向填充，**不渲染页头**（菜单高亮 + 浏览器标题已定位，页头属重复信息）。页面级操作按钮放各自卡片标题栏（Card extra）。结构约定：`.pageContainer > .pageBody > 页面内容`，配套 `frozen-toolbar` mixin 实现工具条冻结。