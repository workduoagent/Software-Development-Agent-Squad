# 可观测性、测试与交付门禁

参考项目里没有测试基线也没有 traceId，这一节是本 skill 新立的规矩，不是照搬。

## 一、日志与链路追踪

- `assets/config/logback-spring.xml` → `resources/logback-spring.xml`，pattern 必带 `[trace=%X{traceId:-}]`。
- `assets/web/RequestTraceFilter.java` 注册为最高优先级过滤器：请求进来先生成/接收 `X-Trace-Id`，
  写 MDC + request attribute + 响应头，finally 清理。
  微服务拓扑里网关先生成 traceId，Feign 拦截器负责往下透传。
- 日志分级：业务异常 warn（不打堆栈）、系统异常 error（带堆栈与 traceId）、客户端中断 warn（只记 URI）。
- 禁止 `log.info` 打印完整请求体（可能含手机号、身份证、Token）。要调试入参就打脱敏后的 DTO。
- `LOG_HOME` 走环境变量，不给 `/app/logs` 这类绝对路径写死进仓库。

## 二、单测基线

依赖见 `dependencies.md`（`spring-boot-starter-test` + `mockito-junit-jupiter`）。

两层，都不起完整容器：

| 层 | 手段 | 测什么 |
| --- | --- | --- |
| Service | `@ExtendWith(MockitoExtension.class)`，纯 mock | 业务分支、每条契约错误码、边界 |
| Controller | `@WebMvcTest` + `@Import(GlobalExceptionHandler.class)` | 契约字段名、`Result` 包裹、校验返回码 |

资产：`assets/testing/ExampleServiceTest.java`、`assets/testing/ExampleControllerTest.java`

必测清单：

1. 正常路径（返回结构与契约样例一致）
2. 契约里该 operation 登记的**每一条**错误码路径 —— 登记 40001/40101/40901 就要有三个用例
3. 边界：空值、越界页码、重复提交、超长字符串
4. 租户越权：A 租户取 B 租户数据必须被拒
5. 上下文缺失：未登录/定时任务场景不得抛 NPE 或写假审计

纪律：

- **禁止连真实数据库、真实 Redis、真实外部 HTTP**（那是集成测试，另设 profile，不进交付门禁）。
- 需要 DB 的 DAO 行为用 Flyway + Testcontainers 单独立项；本门禁不依赖它。
- 断言只断「对外可见的结果」：返回值、异常码、落库参数。禁止断 private 方法或日志内容。
- 测试数据不写在 `src/main`，`UserContext` 在 `@AfterEach` 必须 `remove()`。

## 三、交付门禁（五条全过才能提测）

```bash
mvn -q -DskipTests=false clean verify            # 编译 + 单测 + 打包，退出码 0
mvn -q test 2>&1 | tee build/test.log            # 留存真实测试日志
bash scripts/check_secrets.sh src                # S001 机密自查，必须输出 SECRETS OK（退出码 0）
bash scripts/check_security.sh src               # S002-S008、S010 安全基线，必须 SECURITY CHECK PASSED
mvn -q test -Dtest='*ControllerTest' 2>&1 | tee build/contract-test.log   # 契约镜像测试全绿
```

`scripts/check_secrets.sh` 查三类：配置文件里写死的机密值（`${ENV}` 占位与 `""` 除外）、
Java 里 `${jwt.secret:默认值}` 形态的默认口令、内网 IP:port 与 namespace UUID。
命中即打回，不做人工放行；token 计数类配置（`max-tokens` 等）与纯数字值已在白名单里。

`scripts/check_security.sh` 的逐条含义、豁免写法与输出取证口径见 `references/security-audit.md`，
要求本身见 `docs/02-protocols/security-baseline.md`。

提测报告必须附上：

- `mvn verify` 退出码与 `build/test.log` 片段（用例数、失败数、真实时间戳）
- 两条门禁脚本的完整输出（`check_security.sh` 的 `[INFO]` 取证段也要带上）
- 新增/变更的错误码 → 契约 `x-error-codes` 对应条目
- 新增 Flyway 脚本路径与版本号
- 契约字段映射说明（DTO/VO ↔ OpenAPI schema）

## 四、评审对账项（backend 专属，详见 docs/02-protocols/review-criteria.md）

| 判据 | 证据 |
| --- | --- |
| 分层未被穿透 | Controller 签名里无 entity、无 `HttpServletRequest` |
| 六大基石齐全 | DDL + BaseEntity + FillHandler 三处对得上 |
| ID 字符串出参 | VO/Entity 上 `ToStringSerializer`，且契约里 `type: string` |
| 错误码双向对齐 | 代码枚举 ↔ 契约登记表，无孤儿码 |
| 拓扑一致性 | 单体不混入网关 Header 逻辑；微服务不自行解析 JWT |
| 幂等与事务 | `@Transactional(rollbackFor = Exception.class)`；写接口有重复提交防护 |
| ThreadLocal 清理 | 切面 finally / `afterCompletion` 里有 `UserContext.remove()` |
| 无机密入库 | 第三条门禁命令输出 `SECRETS OK` |
| 安全与审计已落地 | 第四条门禁命令通过 + `references/security-audit.md` 的覆盖清单逐项有实现（人工判据见 review-criteria） |

## 五、不要做的事

- 不要为了"以后可能用"预留多数据源、消息队列、缓存抽象层。
- 不要在 service 里 `new` 工具类绕过 Spring（JWT 例外：`JwtUtils` 由 `JwtConfig` 装配，仍从容器取）。
- 不要把 `Result` 塞进 `data` 形成嵌套 `{code,msg,data:{code,msg}}`。
- 不要用 `e.printStackTrace()` 或 `System.out`。
- 不要在没有契约变更的情况下改接口字段名——那是 BREAKING，必须走 architect + 总架构师流程。
