# 拓扑变体：鉴权、配置与调用链

同一套 `common` 基线，两种拓扑在**鉴权位置**、**配置来源**、**服务间调用**上分叉。开发前先确认拓扑，混用是返工主因。

## 一、单体拓扑

鉴权完全在应用内，靠注解声明。

```
请求 → Tomcat → ApiRegisterAspect（限流 → 验签 → 写 UserContext）→ Controller → ...
                                                              finally: UserContext.remove()
```

资产：`assets/aspect/ApiRegister.java` + `assets/aspect/ApiRegisterAspect.java`

注解语义：

```java
@ApiRegister(name = "创建示例", requireLogin = true, limitCount = 10, limitWindow = 1)
```

| 字段 | 作用 |
| --- | --- |
| `requireLogin` | true 才解析 JWT 并写上下文 |
| `limitCount` / `limitWindow` | Redis INCR + EXPIRE 固定窗口限流，0 表示不限 |
| `isLog` | 访问日志 |
| `name` / `desc` | 与契约 `summary` / `description` 对齐 |

三条纪律：

1. **默认放行、注解才鉴权**意味着「忘记打注解」= 接口裸奔。因此每个 mapping 方法必须有 `@ApiRegister`；
   公开接口显式写 `requireLogin = false`，让评审看出这是决策而不是遗漏。
   自查：`grep -c "@\(Get\|Post\|Put\|Delete\)Mapping" **/controller/*.java` 与 `@ApiRegister` 数量对齐。
2. 切面用 `@Around` 并在 finally 里 `UserContext.remove()` —— 虚拟线程下线程不复用，但异常路径仍会残留 Map 对象。
3. 限流 key 带 `spring.application.name` 前缀，避免多应用共用一套 Redis 时互相干扰。

配置：本地 `assets/config/application.yml` + `application-{profile}.yml`，profile 文件只放非机密差异。

## 二、微服务拓扑

鉴权集中在网关，服务只信 Header。

```
请求 → gateway AuthGlobalFilter（验签 → mutate 注入 X-User-Id / X-Username / X-Tenant /
                              X-User-Role / X-Sys-Tenant）
     → lb://app-server-xxx → UserContextInterceptor（读 Header 写 ThreadLocal）→ Controller
```

资产：`assets/gateway/AuthGlobalFilter.java`（网关）+ `assets/web/UserContextInterceptor.java` +
`assets/config/WebMvcConfig.java`（服务侧）+ `assets/web/InternalTokenInterceptor.java`（内部调用）

### 网关侧

- **必须 `request.mutate().header(...)` 覆盖**同名 Header，绝不能直接透传客户端请求——否则伪造
  `X-User-Id: 1` 就是任意用户。这是这套拓扑的第一安全前提。
- 白名单用 `AntPathMatcher`，只放健康检查与登录入口。
- 网关无状态：不写 `UserContext`（那是 servlet ThreadLocal，WebFlux 里没有对应概念），只注入 Header。
- 需要 Redis/DB 的阻塞调用一律 `Mono.fromCompletionStage(...)` 包装，别在 event-loop 线程上同步等。
- **`Mono<Void>` + `switchIfEmpty` 陷阱**：子分支返回的空 `Mono<Void>` 会被 `switchIfEmpty` 判定为
  "无值"继续走 fallback，导致已经写出的 401 响应再叠加一次处理。正确写法是校验失败时
  `Mono.error(new RuntimeException("XXX_NOT_FOUND"))`，末端统一 `onErrorResume` 分流。
- 网关模块不得引 `spring-boot-starter-web`；引了会同时存在两种 Web 容器，
  启动报 `WebApplicationContext required` 或直接退化。需要排除时用
  `spring-boot-starter-web` 的 `<exclusions>` 或在 `@SpringBootApplication` 上排除
  `WebMvcAutoConfiguration`、`DataSourceAutoConfiguration`（网关不该有数据源）。

### 服务侧

- `UserContextInterceptor` 只读 Header，**不再解析 JWT**（密钥不下发到业务服务，减少泄漏面）。
- 网关的缺省值（`unknown` / `anonymous` / `0` / `USER`）表示未登录，拦截器必须过滤掉，
  否则会把这些假值当真实身份写进 `created_by` / `tenant` 审计字段。
- 拦截器在 `WebMvcConfig` 注册，`excludePathPatterns("/actuator/**", "/error")`。
- `afterCompletion` 里 `UserContext.remove()`。

### 服务间调用

- 走 OpenFeign + Nacos 服务名，禁止写死地址。
- Feign 请求拦截器补 `X-Internal-Token`（值来自配置中心），被调方 `InternalTokenInterceptor` 校验 `/internal/**`。
- 密钥缺失时**拒绝而不是放行**（fail-closed）。
- 内部接口统一 `/internal/**` 前缀，网关路由表里不暴露该前缀——外部永远打不到。
- 透传身份：Feign 拦截器同时复制 `X-User-Id` 等 Header，让下游拿到最终用户而不是服务账号。

### 配置分层（Nacos）

`assets/config/bootstrap-nacos.yml`

```yaml
spring.config.import:
  - optional:nacos:common-config.yaml?group=DEFAULT_GROUP&refreshEnabled=true
  - optional:nacos:${spring.application.name}-${spring.profiles.active}.yaml?...
```

- `bootstrap.yml` 里**只留** Nacos 坐标与应用名，其余全部下沉到 Nacos。
- `optional:` 前缀必带：没有它，本地开发或 Nacos 抖动时应用直接起不来。
- 三份 data-id 的取舍：全局共用 → `common-config.yaml`；体量大的独立词库/规则 → 单独 data-id；
  服务私有 → `{name}-{profile}.yaml`。
- Nacos 地址、账号、namespace UUID 全部走环境变量，仓库里不得出现真实值。

## 三、跨拓扑陷阱清单

| 现象 | 根因 | 处置 |
| --- | --- | --- |
| 依赖公共 jar 报「没有主清单属性」 | 公共模块被 repackage 成可执行 jar | `spring-boot-maven-plugin` `<skip>true</skip>` |
| 网关启动报找不到 `WebMvcConfigurer` | WebFlux 里混进 MVC 依赖 | 排除 `spring-boot-starter-web` |
| 401 之后连接 reset / 日志刷屏 | `Mono<Void>` 走 `switchIfEmpty` 二次处理 | 改 `Mono.error` + `onErrorResume` |
| SSE 接口异常时整条流断 | Advice 返回对象触发消息转换 | `isSseRequest` 分支手工写 error 帧 |
| 审计字段出现 `tenant=0`、`created_by=1` 等假值 | 网关缺省 Header 被当真实身份 | 拦截器过滤 fallback 值 |
| 用户 A 的请求读到用户 B 的上下文 | 虚拟线程/线程池下 ThreadLocal 未清 | 清理放 finally / `afterCompletion` |
| 分页在测试库报语法错 | 未显式指定 `DbType.POSTGRE_SQL` | 写死方言 |
| 更新后 `updated_at` 没变 | `strictUpdateFill` 遇已有值跳过 | update 用 `setFieldValByName` |
| 前端拿到大整数尾数变 0 | Long 直出 JSON | ID 字段 `ToStringSerializer` |
