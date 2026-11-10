# 安全与日志审计落地（Java / Spring Boot）

要求本身以 [`docs/02-protocols/security-baseline.md`](../../../docs/02-protocols/security-baseline.md) 为唯一权威来源——本文件只回答「在 JDK 21 + Spring Boot 3 工程里怎么把它写出来」。**条款文字两边不重复**，冲突时以基线为准并回来修正本文件。

基线第九节列了 6 项待总架构师拍板的参数（口令复杂度、锁定阈值、Token 有效期、留存天数、双因素、落库还是落文件）。**开发不得自行假定取值**：`application.yml` 里对应键全部走 `${ENV}`，缺值按已定基线跑，未定项在提测报告里标「待裁定」。

## 一、资产落位

| 资产 | 复制到 | 说明 |
| --- | --- | --- |
| `assets/audit/AuditEventType.java` | `${base-package}.audit` | 12 类事件枚举，与基线 AU-1 覆盖面一一对应；新增事件类型必须先在基线里登记 |
| `assets/audit/AuditLog.java` | `${base-package}.audit` | 声明式审计注解 |
| `assets/audit/AuditRecorder.java` | `${base-package}.audit` | 唯一的审计写入口，产出八要素 JSON + HMAC |
| `assets/audit/AuditLogAspect.java` | `${base-package}.audit` | 把 `@AuditLog` 方法的成败转成审计记录 |
| `assets/audit/SensitiveMaskUtils.java` | `${base-package}.audit` | 唯一的脱敏入口，日志与 detail 都走它 |
| `assets/testing/AuditRecorderTest.java`、`AuditLogAspectTest.java` | `src/test/java/${base-package}/audit/` | 9 个用例，是审计能力的最低验收线，改名可以、断言不能删 |
| `assets/config/logback-spring.xml` | `src/main/resources/` | 已含 `AUDIT_FILE` appender（`maxHistory 180`）与 `logger AUDIT additivity=false` |
| `assets/config/application.yml` | `src/main/resources/` | 已含 `security.*` 与 `audit.*` 参数块 |

## 二、两条写入路径，各管一半场景

**声明式（优先）**——增删改导出这类「一次请求对应一次业务动作」的接口，在 Controller 方法上标注即可：

```java
@AuditLog(type = AuditEventType.DATA_DELETE, object = "User", desc = "删除用户")
@DeleteMapping("/user/{id}")
public Result<Void> remove(@PathVariable Long id) { ... }
```

切面对成功记 `outcome=success, code=200`，对 `BusinessException` 记 `code=e.getCode()`（与契约 `x-error-codes` 同源），对其它异常记 `code=null` 并在 detail 里留 `traceId` 线索——**异常原样抛出，审计不改变业务语义**。

**手工**——以下场景切面覆盖不到，必须在业务代码里显式调 `AuditRecorder.record(...)`：

- 登录成功 / 失败：失败发生在 Controller 之前（鉴权环节），且要带锁定计数
- 登出、Token 签发与刷新（`AUTH_ISSUE`）
- 网关或切面直接拦下的请求（`SECURITY_BLOCK`）：限流命中、内部令牌校验失败
- 越过权限边界的尝试（`PERMISSION_DENIED`）：不要只回 403，要留下"谁在什么时候想干什么"
- 配置变更、账号启停（`CONFIG_CHANGE`）

判断标准只有一条：**测评员想知道的动作，就必须有一条记录**。`@AuditLog` 标了但接口没有任何写操作，等于没标。

> 取值来源仍是契约：`type` 对应契约 `x-audit.event_type`、`object` 对应 `x-audit.object_type`（形态见 `docs/02-protocols/api-contract-spec.md` §8.3），
> 鉴权注解里的角色与权限点串对应 `x-permissions`（§8.1）。契约里找不到你要用的值，就是契约缺口——上报 PM 走变更流程，不在代码里自造事件名或权限点。

## 三、记录结构与签名

落盘是一条 JSON 行，键名用 camelCase（线上形态），与基线八要素的逻辑名一一对应：

| 基线字段 | JSON 键 | 来源 |
| --- | --- | --- |
| audit_id | `auditId` | 雪花 `IdWorker.getIdStr()`，禁自增 |
| event_time | `eventTime` | `OffsetDateTime`，带时区；服务器必须 NTP 同步 |
| actor | `actor{userId,username,tenant,role,isSysTenant}` | `UserContext`，未登录记 `anonymous` |
| event_type | `eventType` | `AuditEventType` 枚举名 |
| object | `object` | `类型:资源ID`，取不到 ID 记 `-` |
| outcome + 错误码 | `outcome` / `code` | `success`\|`fail` + 契约码 |
| client | `client{ip,userAgent,traceId,uri}` | `RequestContextHolder` + MDC |
| detail | `detail` | 过 `SensitiveMaskUtils.maskText` 后落盘 |
| sign | `sign` | 见下 |

**签名口径**（校验方必须完全一致，否则验真全失败）：对**不含 `sign` 键**、按上表顺序排列的 map 做 JSON 序列化，用 `audit.sign-key` 走 HmacSHA256，输出十六进制。`AuditRecorder` 里 `event.put("sign", sign(event))` 正是先算后放，所以 `sign` 天然不参与自身计算。

`sign-key` 为空时记录写 `sign=unsigned` 并在启动时打 WARN。**`unsigned` 记录不满足 AU-3**，生产环境出现即视为门禁未过，不是"差不多可用"。

## 四、留存、保护与备份

审计与运行日志**物理分离**是本基线最容易做错的一处：把审计当普通 `log.info` 打进业务日志，测评直接判不符合，因为无法证明审计未被业务日志覆盖。

- **文件形态**（默认）：独立 appender + 独立文件名 `*-audit.*.log`；`additivity=false`；`maxHistory ≥ 180`；审计 appender **不套 AsyncAppender**——`neverBlock=true` 溢出即丢记录，审计宁可慢也不能丢。
- **落库形态**：表 `audit_log` 走 Flyway 建，列名用基线逻辑名（snake_case），`detail` 用 `jsonb`；应用账号**只授予 INSERT/SELECT**，DELETE/TRUNCATE 交给归档专用账号；分区或定期归档到新表，不直接删。
- 两种形态都要：纳入备份计划、可按 用户 / 时间区间 / 事件类型 / 资源 检索导出。检索能力缺失等同于"有审计但用不上"。
- 篡改自身也要记：清理归档、改留存配置这类动作产生 `AUDIT_TAMPER` 记录。

## 五、身份鉴别与访问控制的代码落点

| 基线 | 落点 |
| --- | --- |
| ID-1 口令复杂度与轮换 | `security.password.*` 读入，校验写在 Service 层（注册、改密、首次登录），**不依赖前端**；散列只用 `BCryptPasswordEncoder`，历史口令比对旧散列 |
| ID-2 失败锁定与超时退出 | Redis 计数：`login:fail:{username}` INCR + TTL=锁定时长，达阈值置 `login:lock:{username}`；解锁与登录成功都要 DEL。会话超时取 `security.session.idle-timeout-seconds`，Token 有效期在 `jwt.expiration` |
| ID-3 防窃听 | 口令只在请求体里出现，禁止进 URL 查询串；`GlobalExceptionHandler` 与各日志点都不得打印请求体 |
| AC-1/AC-4 角色 | 单体：`@ApiRegister(roles = "...")`；微服务：网关鉴权 + 服务侧 `UserContext.getCurrentRole()` 判定，契约里显式声明所需角色 |
| AC-5 越权 | **两道都要**：角色校验挡垂直越权，`tenant` + 属主条件挡水平越权。查询用 `QueryWrapper` 显式加 `tenant`，更新/删除先按 `id + tenant` 取归属再判，禁止"前端看不到就当没有" |
| AC-2/AC-3 账户 | 初始化脚本禁止 `admin/admin123`；账号状态校验放在鉴权环节（拦截器/网关），不放在业务分支里 |

## 六、脱敏（DP-3 / SEC-4）

`SensitiveMaskUtils` 是唯一入口，规则顺序有意义：身份证 → 手机号 → 银行卡 → 凭据键值 → Bearer。凭据键值先于 Bearer，否则同一行被两道规则各削一次，输出 `Authorization: *** ***`。

- 自由文本、JSON 摘要：`maskText`
- 明确的手机号 / 身份证列：`maskPhone` / `maskIdCard`
- 口令类：**`maskCredential` 恒返回 `***`**，不做"保留首尾"——口令没有任何合法的可展示形态
- 禁止在业务代码里手写 `substring` 拼星号：写法不统一等于没有脱敏

## 七、依赖漏洞（S009）

静态脚本查不出依赖 CVE，这一步只能在 CI 做，命令进流水线门禁：

```bash
mvn -B org.owasp:dependency-check-maven:check -DfailOnViolation=true   # 后端
npm audit --omit=dev --audit-level=high                                 # 前端
```

离线环境用 `dependency-check` 的本地 NVD 镜像；扫不了的高危依赖必须在提测报告里列出并说明缓解，不能默默跳过。

## 八、交付门禁（安全相关的三条命令，全部留存真实日志）

```bash
bash scripts/check_secrets.sh  src     # S001，期望 SECRETS OK，exit 0
bash scripts/check_security.sh src     # S002-S008、S010，期望 SECURITY CHECK PASSED，exit 0
mvn -B clean verify                    # 单测含审计基线用例，退出码 0
```

`check_security.sh` 的输出分三段，`[INFO]` 是通过项取证（S005 命中文件、S006 实际留存天数、S010 声明计数），提测报告要把这一段带上——只贴"PASSED"不算证据。

单行豁免写 `#nosec: 理由`（S002/S003/S004/S007/S008 支持）。豁免是给"确有白名单、确有非敏感用途"的场景，**理由必须在代码评审里被看到**，空理由的豁免按未处理打回。

## 九、跨拓扑注意

| 场景 | 单体 | 微服务 |
| --- | --- | --- |
| 审计身份来源 | `ApiRegisterAspect` 解析 JWT 后写 `UserContext`，切面直接读 | 网关鉴权并 `mutate` 覆盖身份 Header，服务侧 `UserContextInterceptor` 落 ThreadLocal，切面同样只读 `UserContext` |
| 登录事件产生点 | 本服务登录接口 | **认证服务**产生 `LOGIN_*`，网关产生 `SECURITY_BLOCK`；业务服务不重复记登录，否则一次登录出多条记录，时间线反而不可读 |
| traceId | 单机 MDC 即可 | 网关生成、`RequestTraceFilter` 透传，审计 `client.traceId` 才有跨服务串联能力 |
| 审计写入失败 | 默认只告警 | 同左；`audit.fail-fast=true` 会让审计写失败直接拒绝操作，是否启用由总架构师裁定 |

## 十、常见坑

1. **切面在 JDK 动态代理下取不到注解**：`joinPoint.getSignature().getMethod()` 返回接口方法，注解在实现类上 → `resolve()` 已回退到目标类方法。自己另写切面时最容易漏，表现是"接口正常但审计一条没有"。
2. **`additivity` 忘了设 false**：审计同时进业务日志文件，运行日志一滚动/一清理就把审计带走了，判不符合。
3. **审计走 AsyncAppender**：高并发下静默丢记录，且丢的那段恰好是被攻击时段。
4. **`detail` 塞整个实体快照**：既有明文手机号又爆体积。只记字段级 `old→new` 摘要并过脱敏。
5. **错误码写死字符串**：`code` 必须与 `ErrorCodeEnum` / 契约同源，否则审计里的码在契约里查不到，对账对不上。
6. **只在成功时记审计**：失败与越权尝试才是测评与应急响应的重点。
7. **把 `System.out` 当审计**：S004 直接命中，且没有任何留存与保护措施。
8. **`sign-key` 上线不配**：`sign=unsigned`，事后无法证明记录未被改。
