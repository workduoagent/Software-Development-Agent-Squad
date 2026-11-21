# 等保二级安全项与日志审计（Python 侧落地）

> 要求本身只有一份：软件团队知识库 安全与日志审计基线.md。本文件只写 FastAPI/SQLAlchemy 怎么实现；基线第九节待拍板参数不得自行假定取值。

## 鉴权与越权（两道校验）

1. **角色道（路由级）**：鉴权用 FastAPI 依赖显式声明——每个路由挂 `Depends(require_permission("<角色>", "<权限点>"))`；公开接口显式 `Depends(require_login(False))`。权限点取值来自契约顶层 `x-roles` 与各 operation 的 `x-permissions`。
2. **数据道（查询级）**：repository 每条查询强制带租户与属主条件（`tenant = ctx.tenant AND <属主字段>`），由基类/公共查询构造器保证，禁止裸查全表再内存过滤。

## 参数化 SQL

- ORM 全程绑定参数，天然参数化；确需原生 SQL 时用 `text()` 绑定参数，禁止 f-string/`%`/`+` 拼接 SQL 片段（机检与评审红线）。

## 审计（失败分支也要记）

- 写操作路由统一挂审计依赖：成功与失败（401/403/429/业务失败）都落审计事件；`event_type` 取基线 AU-1 枚举，禁止自造事件名。
- 审计落库表含八要素列（who/when/where/what/how-which/result/…，形态见基线）；落文件方案写明承载工程与配置（≥180 天）。
- `detail` 落盘前一律过统一脱敏工具：口令与 Token 完全不落，手机号/身份证走 mask。

## 脱敏与敏感数据

- 敏感字段（契约 `x-sensitive`）在 Pydantic Out 模型上标注；序列化出口统一走脱敏器。
- 日志不落敏感明文；traceId 贯穿（中间件生成 → contextvars → structlog 绑定）。

## 机密

- 全部环境变量（settings.py）；代码、日志、异常消息不得出现明文口令/Token/内网地址。
- 交付前必跑：`python python-backend-scaffold/scripts/check_secrets.py "{root_dir}/src"`，命中即失败，行内 `#nosec` 豁免需在交付报告说明理由。
