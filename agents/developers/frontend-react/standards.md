# React 前端规范（Standards）

工程规范权威来源：[`skills/react-scaffold/`](../../../skills/react-scaffold/SKILL.md) —— 目录设计、基础依赖、请求封装、Mock 体系、路由布局、三层 Sass 主题体系、单测与交付门禁的具体规范、细节与约束全部以 Skill 为准，本文件不重复维护。

跨技术栈通用的交付纪律权威来源：[`agents/developers/README.md`](../README.md)。

| 需要查的内容 | 去处 |
| --- | --- |
| 目录分层与工程骨架 | `references/directory.md` |
| 依赖版本基线、环境变量 | `references/dependencies.md` |
| 入口装配、请求封装、Mock、store 与公共 hooks | `references/infrastructure.md` |
| 路由体系与布局体系 | `references/router-layout.md` |
| 全局 Sass 与明暗主题 | `references/styling.md` |
| 单测四态闭环与交付门禁命令 | `references/testing.md` |
| 凭据存储、XSS、控制台泄露、依赖扫描、F0xx 机检项 | `references/security.md` |

> 安全与日志审计的**要求本身**只有一个来源：[`docs/02-protocols/security-baseline.md`](../../../docs/02-protocols/security-baseline.md)（等保二级基线）；
> `references/security.md` 只写前端侧的落地写法，本文件只做索引。项目级补充约束（如特有组件约定、设计令牌）在此登记，与 Skill 或基线冲突时以 Skill / 基线为准。