# 全局样式与明暗主题

## 三层体系（方向不可逆）

```
styles/theme.css        颜色唯一真源：:root.light / :root.dark 下定义 --color-* CSS 变量
        ↓ 映射
styles/variables.scss   sass 变量（$color-primary: var(--color-primary)）+ 通用 mixin
        ↓ 被 Vite additionalData 注入每个 .scss
styles/global.scss      全局基础样式（reset、字体、滚动条、工具类）
        ↓
页面/组件 index.scss     只消费变量与 mixin，根类名包裹防泄漏
```

## 纪律

1. **hex 只许写在 theme.css**。业务样式硬编码 hex/rgba 即违规；阴影色也用 `var(--shadow-color)`（随主题变化）。
2. **variables.scss 禁止输出任何 CSS 规则**（只许变量/mixin/函数）：它被注入每个 .scss 头部，输出规则会成百上千份重复打包。
3. `<html>` 的 `.light/.dark` 类**只由 ThemeProvider 写**；组件切换主题只调 `useTheme().setTheme()`。
4. antd 主题由 ThemeProvider 的 ConfigProvider 驱动（darkAlgorithm/defaultAlgorithm + token），**antd token 色值必须与 theme.css 同色系**，改色两处一起改。
5. Tooltip/Modal 等 portal 渲染在 body 下、页面根类之外——这类样式只能放 global.scss，不能写进页面 scss。

## ThemeProvider 三职责（唯一执行者）

1. `matchMedia('(prefers-color-scheme: dark)')` 监听系统主题 → 写 systemSlice；
2. resolvedTheme 写到 `<html>` class + `style.colorScheme`（同步原生滚动条/表单配色）；
3. 驱动 antd 算法与 token。

状态分工：themeSlice 存用户选择（light/dark/system，localStorage 持久化）；systemSlice 存系统解析结果；`resolvedTheme = mode === 'system' ? system.resolved : mode`。业务组件只消费 resolvedTheme。

## variables.scss 内容分区

- 语义色映射：品牌/成功/警告/错误/信息 + 各自的 -bg/-border 浅底变体；
- 文字四级（primary/secondary/tertiary/inverse）、背景分层（body/container/elevated/subtle/hover/mask）、边框两档（border 主描边 / border-secondary 内部分隔，明度差要拉开）；
- 尺寸/圆角（sm 4 / md 8 / lg 12 / xl 16）/阴影三档/层级/动效曲线；
- 通用 mixin：`ellipsis`、`ellipsis-multi`、`flex-center`、`card-surface`、`card-hover`（含 focus-visible 可访问性）、`card-grid`、`custom-scrollbar`、`no-scrollbar`、`frozen-toolbar`（工具条冻结：.pageBody 定高 flex 列 + 列表滚动 containment + scrollbar-gutter 防抖动）。

完整文件直接复制 `assets/styles/`（theme.css / variables.scss / global.scss / page-loading.scss）。

## 换品牌色步骤

1. `theme.css`：改 `:root.light` 与 `:root.dark` 两处的主色族（primary/hover/active/bg，暗色提亮一档）；
2. `ThemeProvider.tsx`：antdTokens 的 colorPrimary/colorInfo 同步（info 跟随主色，不留第二支蓝）；
3. 其余语义色不动，业务样式零改动（全部走变量）。

## 页面样式约定

- 页面 scss 与 index.tsx 同目录，根类名包裹（如 `.userManage { ... }`）；
- 布局尺寸变量（顶栏高度、内容 padding）从 variables.scss 取，不写魔数；
- 暗色适配免费获得：颜色全走变量即自动适配，禁止写两套明暗样式。