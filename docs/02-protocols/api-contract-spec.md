# 接口契约标准（API Contract Spec）

跨角色协作契约的权威标准。契约由 architect 智能体产出、经 `skills/contract_validator/` 机器校验与指纹锁定、由 PM 核验凭证后登记冻结。第二至第六节的条款与 `lint.py` 检查项一一对应（契约不满足任一 ERROR 级条款即拒绝冻结），第七节的变更分级由 `diff.py` 判定；第八节的安全与审计声明目前靠人工对账，机检现状见 8.5。

## 一、 文件与流程约定

- **格式**：OpenAPI **3.1.x** YAML，UTF-8 编码。
- **位置与命名**：`{root_dir}/contracts/{domain}-api-v{N}.yaml`（如 `auth-api-v1.yaml`）。
- **流程**：architect 产出 → `lint.py` 校验（0 errors）→ `freeze.py` 生成 sha256 锁文件 → 交付 PM → PM 核验凭证后登记项目 `contracts` 表（path / version / sha256 / frozen_at）。登记即冻结生效点。
- **变更**：任何修改必须递增 `info.version`，由 `diff.py` 与上一冻结版本比对；检出 `BREAKING_CHANGE` 时须附总架构师决策结论，重新校验、重新冻结、重新登记。出现 `BREAKING_CHANGE` 必须开辟新大版本文件（如 `api-v2.yaml`），严禁就地覆盖旧版本破坏旧客户端；严禁任何私下口头约定变更。

## 二、 统一响应包装（Result）

所有接口的 2xx 响应必须使用统一包装，`components.schemas.Result` 为固定名称：

```yaml
Result:
  type: object
  required: [code, msg]
  properties:
    code: { type: integer }   # 业务码，0 表示成功
    msg:  { type: string }    # 人类可读提示
    data: {}                  # 业务载荷；错误时为 null
```

- 响应 schema 必须 `$ref: '#/components/schemas/Result'`，或通过 `allOf` 组合 Result 与业务 data 结构；禁止匿名内联包装。
- 扩展字段（如 timestamp）必须显式定义进 Result schema，禁止契约外私加。

## 三、 错误码登记表（x-error-codes）

契约顶层必须携带 `x-error-codes` 登记表，作为全项目错误码唯一真源：

```yaml
x-error-codes:
  - code: 40101          # 业务码（integer，全局唯一，非 0）
    http_status: 401     # HTTP 状态码映射
    message: 账号或密码错误
    trigger: 登录时密码错误或账号不存在   # 触发条件，供前后端与 QA 对齐
```

- 每个 operation 必须定义至少一个 4xx/5xx 错误响应；错误响应样例中的 `code` 值必须已在登记表内。
- 开发角色（前端错误提示、后端异常分支）与 QA（错误路径用例）只允许使用登记表内的错误码。

## 四、 Mock 样例

- 每个 operation 的 2xx 响应必须携带 `examples`（或 `example`），作为正向 Mock 报文真源；错误响应同样应携带样例。
- **样例质量红线**：`example` 严禁无意义占位符（如 `"string"`、`0`、空串），必须语义完备；分页列表样例必须含多条数据与分页元数据（`pageNum`/`pageSize`/`total`）；登记表内每个错误码必须 100% 被至少一个错误响应样例使用（E011 机器校验）。
- `mock_gen.py` 从样例/Schema 提取生成标准 Mock JSON，前端 mock 体系（axios-mock-adapter）以契约样例为准，禁止手敲漂移报文；Schema 降级构造的报文（source: schema）仅供兜底，不得替代契约样例红线。

## 五、 数据模型纪律

- **ID 一律字符串**：`components.schemas` 中名为 `id`、`*Id`、`*_id` 的字段必须 `type: string`（雪花/Long ID 防前端精度丢失）。
- **入参必须带约束**：requestBody 与 parameters 必须有 schema；字符串入参应携带 `format` / `pattern` / `enum` / `maxLength` 至少其一（缺失记 WARN）。
- **分页统一**：查询分页参数固定 `pageNum`（从 1 起）+ `pageSize`；使用 page/current/offset/limit 等别名记 WARN。
- **持久层六大基石字段**：DDL/迁移脚本中的业务表必须含 `id`（雪花 ID，严禁自增）、`created_at`、`updated_at`、`created_by`、`updated_by`、`tenant`（须显式单列索引），缺任一项 PM 强制否决；逻辑删除/乐观锁启用时追加 `is_deleted`、`version`（细则见 architect prompt 第五节，不由 lint 校验 OpenAPI）。

## 六、 lint 检查项对照表

| 检查项 | 级别 | 规则 |
| --- | --- | --- |
| E100 | ERROR | OpenAPI 3.1 语法校验失败（openapi-spec-validator） |
| E001 | ERROR | `openapi` 版本非 3.1.x |
| E002 | ERROR | `info.title` / `info.version` 缺失，或 version 非 semver |
| E003 | ERROR | operation 缺 `operationId` 或全局重复 |
| E004 | ERROR | 缺 2xx JSON 响应，或其 schema 未使用 Result 包装 |
| E005 | ERROR | `components.schemas.Result` 缺失，或 code/msg/data 定义不合规 |
| E006 | ERROR | `x-error-codes` 缺失/条目字段不全；operation 缺错误响应；错误样例 code 未登记 |
| E007 | ERROR | 2xx 响应缺 Mock 样例（examples / example） |
| E008 | ERROR | requestBody / parameter 缺 schema |
| E009 | ERROR | ID 类字段（id / *Id / *_id）非 `type: string` |
| E011 | ERROR | `x-error-codes` 登记的错误码未被任何错误响应样例使用（覆盖率不足 100%） |
| W001 | WARN | 字符串入参无 format/pattern/enum/maxLength 约束 |
| W002 | WARN | 分页参数未使用 pageNum/pageSize |
| W003 | WARN | 错误响应缺样例 |

**严重度语义**：ERROR ≥ 1 → 拒绝冻结（`freeze.py` 直接失败）；WARN 不阻断，但 architect 必须在交付报告中逐条说明。

## 七、 变更分级（diff.py）

| 分类 | 情形 | 处置 |
| --- | --- | --- |
| BREAKING_CHANGE | 删除路径/operation/参数/字段；字段类型变更；请求新增必填项；响应字段 required 取消；枚举值删除；错误响应删除 | 必须上报总架构师拍板，决策结论写入交付报告后方可重新冻结 |
| ADDITIVE | 新增路径/operation/可选参数/可选字段/枚举值/错误码；请求必填项放宽 | 可直接重新校验冻结，version 递增 |

> 安全例外：第八节的 `security` / `x-permissions` / `x-audit` / `x-sensitive` 与顶层 `x-roles` 发生**任何**变化（含放宽、含新增声明），
> 即使按结构分类属于 ADDITIVE，也必须上报总架构师拍板并把结论写入交付报告——权限收紧会打断客户端，放宽会扩大攻击面，两者都不能默认放行。
> `diff.py` 当前不比对这些扩展键，因此该条走人工对账，不靠脚本兜底。

## 八、 安全与审计的契约侧声明

要求本体只在 `docs/02-protocols/security-baseline.md` 维护；本节规定**这些要求在契约文件里长什么样**，供 architect 产出、PM 登记前对账、评审判据引用。

### 8.1 鉴权与角色（对应基线 AC-1 / AC-4）

```yaml
components:
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer, bearerFormat: JWT }
x-roles: [SYS_ADMIN, ADMIN, USER]            # 全项目角色唯一真源；取值由 Tech Spec 定，此处仅为示例形态
paths:
  /api/resource/admin:
    post:
      operationId: createAdminResource
      security: [ { bearerAuth: [] } ]        # 缺失 = 未授权，禁止把"漏写"当成"公开"
      x-permissions:
        roles: [ADMIN]                        # 取值必须来自顶层 x-roles
        points: [resource:create]             # 粒度到"资源 + 操作"，禁止 * 通配
```

- 每个 operation 必须显式写 `security`；确实公开（如登录、验证码）也要显式声明 `security: []` 并在 `description` 注明理由。
- 管理端接口禁止用"已登录"充当权限校验；写操作必须给出权限点。
- 角色与权限点是**契约的一部分**：前端守卫/按钮控制与后端鉴权注解都从这里取值，不得各写一套字符串。

### 8.2 敏感字段标注（对应 DP-1 / DP-3 / SEC-8）

- 口令、Token、密钥类入参：`writeOnly: true`，且禁止出现在任何响应 schema、错误样例或 URL 路径/查询参数里。
- 个人信息字段（手机号、身份证、银行卡、邮箱、姓名）标注 `x-sensitive: phone | id_card | bank_card | email | name`；后端落日志与审计 `detail` 的脱敏规则、前端展示态格式化都由该标注驱动，禁止各处自行判断"这个字段要不要打码"。
- 样例报文里的敏感值必须是虚构测试值，禁止使用真实用户数据。

### 8.3 审计事件声明（对应 AU-1 / AU-2）

每个写操作（POST / PUT / PATCH / DELETE）必须携带 `x-audit`，事件类型只能取自基线 AU-1 枚举：

```yaml
x-audit:
  event_type: DATA_CREATE     # 基线 12 值枚举，禁止自造事件名
  object_type: resource       # 被操作资源类型，与审计八要素 object 的 type 部分同源
  on_fail: true               # 失败分支是否也记（越权拒绝、校验失败默认必须记）
```

- 登录、登出、发令牌、配置变更类接口必须声明对应事件（LOGIN_SUCCESS + LOGIN_FAIL / LOGOUT / AUTH_ISSUE / CONFIG_CHANGE）。
- 后端 `@AuditLog` 的事件类型与 QA 的审计覆盖率用例以 `x-audit` 为对账基准；契约缺声明即视为契约缺口，走变更流程补齐，不由开发自行假定。

### 8.4 错误响应不外泄（对应 SEC-5）

- `x-error-codes` 的 `message` 面向最终用户，`trigger` 面向内部对齐；两者都不得写堆栈、SQL 片段、内部路径或密钥。
- 5xx 只允许通用兜底文案 + `traceId`，禁止按内部异常类型细分透出。

### 8.5 机检现状（不得口头声称已机检）

- `lint.py` 只覆盖第六节对照表里的既有项（E001~E009 / E011 / E100 + W001~W003）；`diff.py` 只比对路径、参数、字段与响应状态，
  两者都**不看** `security` / `x-roles` / `x-permissions` / `x-sensitive` / `x-audit`，即本节 8.1~8.3 尚无机器校验，
  由 architect 自检 + PM 登记前人工对账 + `review-criteria.md` 的安全与审计判据兜住。
- 是否把上述声明补成 lint 项（如"写操作未声明 `x-audit`"告警）属基线变更，需总架构师拍板后实施；拍板前本文不声称其已被脚本校验。

## 九、 制品清单

| 制品 | 生成者 | 路径约定 |
| --- | --- | --- |
| lint 报告 | `lint.py --report` | 调用方指定（建议 `{root_dir}/contracts/reports/{name}-lint.json`） |
| 冻结锁文件 | `freeze.py` | `{契约文件}.lock.json`（sha256、frozen_at、lint 结论） |
| diff 报告 | `diff.py --report` | 调用方指定 |
| Mock 报文集 | `mock_gen.py` | 调用方指定（建议 `{root_dir}/src/api/mock/{name}.mocks.json`） |
