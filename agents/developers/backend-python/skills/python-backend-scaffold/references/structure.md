# 目录蓝图与分层规则

## 目录蓝图

```
<project>/
├── src/
│   └── app/
│       ├── main.py               # 应用装配：FastAPI 实例、路由注册、全局异常处理器、traceId 中间件
│       ├── config/
│       │   └── settings.py       # pydantic-settings（复制 assets/config/settings.py），全部来自环境变量
│       ├── common/
│       │   ├── result.py         # Result 统一响应（复制 assets/common/result.py）
│       │   ├── errors.py         # 错误码枚举（与契约 x-error-codes 一一对应）
│       │   ├── context.py        # contextvars 请求上下文（用户/租户/traceId），谁写谁 finally reset
│       │   └── security/
│       │       ├── jwt.py        # 签发与校验
│       │       └── deps.py       # 鉴权与审计依赖（require_login / require_permission / audit）
│       ├── persistence/
│       │   ├── base.py           # 六大基石基类（复制 assets/persistence/base.py）
│       │   ├── models/           # ORM 模型，禁止出现在路由签名
│       │   └── repository/       # 单表访问，不写跨表业务
│       ├── schemas/              # Pydantic 契约镜像：XxxIn / XxxOut / ErrXxx，字段与契约逐字一致
│       ├── services/             # 业务与事务；每条契约错误码对应一个 BusinessException 抛出点
│       └── routers/              # 只做契约转换与校验；显式挂鉴权与审计依赖
├── alembic/
│   └── versions/                 # 版本化迁移（六大基石 + tenant 前导索引），写法取 database-ops/assets
├── tests/
│   ├── unit/                     # service 层单测
│   └── contract/                 # 契约镜像测试（httpx AsyncClient + 契约 Mock 样例）
├── pyproject.toml                # ruff / mypy(strict) / pytest 配置
└── requirements.txt              # 钉版本，取 python-backend-scaffold/requirements.txt 基线
```

## 分层规则（不可穿透）

| 层 | 允许 | 禁止 |
| --- | --- | --- |
| routers | 解析请求、依赖注入声明鉴权与审计、调 service、包装 Result | 业务逻辑、直接访问 ORM/Repository、读环境配置 |
| services | 业务规则、事务边界、抛 BusinessException（错误码对齐契约） | 解析 HTTP 对象、拼 SQL |
| repository | 单表 CRUD、租户与属主条件过滤 | 跨表业务、事务提交（由 service 管） |
| schemas | Pydantic In/Out 模型 | 逻辑；ORM 模型不得混入 |

## 配置

- 全部经 `settings.py`（环境变量前缀 `SQUAD_`）；数据库连接串由 host/端口/库名 + 环境变量口令组装，只有 host 与凭据走环境变量，池参数按 `database-ops` 规范写死在模板内。
- 设备环境事实（本机 JDK/Conda/数据源地址）取值真源是本机仓库根 `device-env.md`；口令只记环境变量名。
