# 公共基础设施

四个必备件：统一响应、错误码、业务异常、请求上下文。加上 JWT 与全局异常处理，构成任何 Java 后端工程的最小骨架。

## 一、Result —— 契约的运行时镜像

`assets/common/Result.java` → `common/Result.java`

```java
Result.success(data)        // {code:200, msg:"操作成功", data:{...}}
Result.fail(code, msg)      // 业务失败
Result.fail(code, msg, data)// 失败也要回带明细（如字段级校验结果）
```

- 字段是 `code` / `msg` / `data`，**不是** `message`、不是 `errorMessage`。前端拦截器按这三个键拆包。
- Controller 一律返回 `Result<T>`，包括错误路径；不要抛出去让 Spring 渲染默认错误页。
- 成功码取 `ErrorCodeEnum.SUCCESS`（200），非 200 一律视为业务失败并触发前端提示。

## 二、ErrorCodeEnum —— 与 x-error-codes 双向对齐

`assets/common/ErrorCodeEnum.java` → `common/ErrorCodeEnum.java`

编码规则（与 `docs/02-protocols/api-contract-spec.md` 的登记表一致）：**HTTP 状态码 × 100 + 两位序号**。

| 码 | 含义 |
| --- | --- |
| 200 | 成功 |
| 400xx | 参数/请求体问题 |
| 401xx | 未认证（凭证缺失/失效/账号密码错） |
| 403xx | 已认证但无权限（含跨租户访问） |
| 404xx | 资源不存在 |
| 409xx | 状态冲突（重复注册、唯一约束） |
| 429xx | 限流 |
| 500xx | 服务端异常、下游调用失败 |

对齐纪律（评审硬项）：

1. 代码里出现的每个码，契约 `x-error-codes` 必须有同名条目 —— 否则 `contract_validator` E006 拦截。
2. 契约登记的每个码，必须被某个 operation 的错误样例用到 —— E011 拦截。
3. 参考项目历史用的是四位分段码（1001/2001…），迁移时映射到新规则，不保留双轨。

## 三、BusinessException

`assets/common/BusinessException.java`

- 只表达**可预期失败**：账号已存在、余额不足、状态不允许。
- 不许包系统级异常（NPE、SQL、IO）——那些走 `Exception` 兜底并打 error 日志。
- 抛出即中断当前事务（`@Transactional` 默认对 RuntimeException 回滚），所以事务里最后的校验失败要在写操作之前抛。

## 四、UserContext

`assets/common/UserContext.java`

```java
UserContext.getCurrentUserId()   // Long，解析失败返回 null（不抛）
UserContext.getCurrentTenant()   // Long，租户隔离查询的条件来源
UserContext.getUsername()
UserContext.getCurrentRole()
UserContext.isSysTenant()        // 平台管理员跨租户查询的开关
UserContext.remove()             // 必须 finally 调用
```

- 内部是 `ThreadLocal<Map<String,Object>>`，值统一按字符串存、按 `Long.valueOf` 解析；解析异常吞掉返回 null，避免脏 Header 打爆 500。
- **谁写入取决于拓扑**（单体 = AOP 解析 JWT；微服务 = 拦截器读网关注入的 Header），**谁清理也必须对称**：AOP 的 finally 或 `afterCompletion`。
- 定时任务、MQ 消费、启动初始化里取到的是 null——这是设计意图，不要在这里塞一个 "system" 用户兜底，否则审计字段全是假数据。业务上确实需要系统写库时，用显式的系统账号常量并在 DDL 注释里说明。

## 五、JWT

`assets/security/` 三个文件：`JwtUtils`（非 Bean，纯逻辑）+ `JwtProperties`（配置绑定）+ `JwtConfig`（装配 + fail-fast 校验）。

JJWT 0.12.x 新 API 写法（0.9.x 的 `setSubject`/`signWith(SignatureAlgorithm, str)` 已全部废弃）：

```java
Jwts.builder().claims(map).issuer(iss).issuedAt(now).expiration(exp)
    .signWith(secretKey, Jwts.SIG.HS256).compact();

Jwts.parser().requireIssuer(iss).verifyWith(secretKey).build()
    .parseSignedClaims(token).getPayload();
```

载荷约定字段：`userId`（字符串）、`username`、`tenant`（字符串）、`role`、`is_sys_tenant`（"0"/"1"）。
新增 claims 要同步契约的登录响应样例，前端解析逻辑才能对上。

- `parseToken` 失败返回 null，调用方翻译成 401xx；不要在这里抛异常。
- `extractTokenFromHeader` 兼容裸 token 与 `Bearer ` 前缀两种写法。
- 密钥只从环境变量/配置中心来；`JwtConfig` 启动即校验长度 ≥ 32 字节。

## 六、GlobalExceptionHandler

`assets/exception/GlobalExceptionHandler.java`

四类处理器，顺序即优先级：

1. `BusinessException` → 按 code 返回，warn 级日志（不打堆栈，避免刷屏）
2. `MethodArgumentNotValidException` → 聚合成 `字段: 提示; 字段: 提示` 返回 40001
3. 客户端中断类（`ClientAbortException` / `IOException`）→ 只记 warn，**不尝试写响应体**（写不了）
4. `Exception` 兜底 → 50001 + error 日志带 traceId 与堆栈；响应体不回显异常信息

**SSE 陷阱（必读）**：接口 `produces = text/event-stream` 时，响应头已发出，此时返回对象给消息转换器会抛
`HttpMessageNotWritableException` 并打断整条流。资产里的 `isSseRequest()` + `writeSseError()` 手工写一帧
`event: error` 再返回 null。做流式接口（LLM 输出、进度推送）时这是必踩坑，评审要专门看这条分支。

## 七、落位对照

| 资产 | 目标位置 |
| --- | --- |
| `common/*.java`（4 个） | `${base-package}.common` |
| `security/*.java`（3 个） | `${base-package}.security` |
| `exception/GlobalExceptionHandler.java` | `${base-package}.exception` |
| `config/MybatisPlusConfig.java`、`MybatisPlusFillHandler.java` | `${base-package}.config` |
| `persistence/BaseEntity.java` | `${base-package}.pojo` |
| `web/RequestTraceFilter.java` | `${base-package}.web` 并在配置里注册 |
