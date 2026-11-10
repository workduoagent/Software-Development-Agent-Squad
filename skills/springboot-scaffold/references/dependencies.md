# 依赖与版本基线

## 一、锁定版本

JDK 版本由公司统一确定，**任何模块不得下调**。

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| JDK | **21**（LTS，公司既定） | `maven.compiler.release` 与 `java.version` 都写 21 |
| Spring Boot | 3.3.4 | 父 pom 继承 `spring-boot-starter-parent` |
| Spring Cloud | 2023.0.3 | 仅微服务拓扑 |
| Spring Cloud Alibaba | 2023.0.3.2 | Nacos 注册与配置 |
| MyBatis-Plus | 3.5.6 | 必须用 `mybatis-plus-spring-boot3-starter`（不是 boot2 版本） |
| PostgreSQL driver | 42.7.3 | |
| Flyway | 10.17.3 | 需要 `flyway-core` + `flyway-database-postgresql` 两个坐标 |
| JJWT | 0.12.6 | API 与 0.9.x 完全不兼容，只用新 API |
| Redisson | 3.31.0 | 分布式限流/锁 |
| commons-lang3 / commons-io | 3.18.0 / 2.16.1 | |
| Lombok | 继承 Boot 版本 | `optional=true` |

## 二、依赖纪律

1. **版本只能出现在父 pom 的 `<properties>` / `<dependencyManagement>`**。业务模块写依赖不写 `<version>`。
2. **不引 Spring Security 全家桶**：密码散列只要 `spring-security-crypto`（BCrypt），鉴权走 JWT + 拦截器/切面（见 `topology.md`）。引了 Security 而不做配置会导致全部接口被默认登录页拦下。
3. **JSON 序列化统一 Jackson**（Boot 默认）。参考项目里大量使用 fastjson，本基线不再默认引入：
   - 需要兼容旧代码时才显式加，并且只允许出现在 `common` 层，禁止在 Controller/Service 里手工 `JSON.toJSONString` 拼响应。
   - 网关写响应体时用字符串模板或 Jackson，别把 fastjson 带进 WebFlux 链路。
4. **校验用 `spring-boot-starter-validation`**，DTO 上必须有 `@NotBlank/@Size/@Pattern` 等注解——契约里 `required` 与 `maxLength` 的落地就是它。
5. **AOP**：单体拓扑必须引 `spring-boot-starter-aop`，鉴权/限流/慢日志全靠它。
6. **测试依赖常备**：`spring-boot-starter-test`、`mockito-junit-jupiter`；`scope=test` 不影响包体积。

## 三、JDK 21 相关

- **虚拟线程**：`spring.threads.virtual.enabled=true` 已在基线里打开。收益是 IO 密集接口吞吐；代价是每个请求换线程，`ThreadLocal` 复用假设失效——`UserContext.remove()` 必须在 finally 里执行，否则跨请求串号。
- **Record** 适合做 VO 与不可变 DTO；MyBatis-Plus 实体不用 Record（需要可变字段与填充）。
- **`@Serial`** 标注 `serialVersionUID`，避免编译告警。
- 文本块用于 SQL 片段与 SSE 帧拼接，别再用字符串加号堆。

## 四、复制资产

| 场景 | 复制 |
| --- | --- |
| 新建单体工程 | `assets/config/pom-single.xml` → `pom.xml` |
| 新建微服务父工程 | `assets/config/pom-parent.xml` → 根 `pom.xml` |
| 新增公共 jar 模块 | `assets/config/pom-jar-module.xml`（改 artifactId） |
| 主配置 | `assets/config/application.yml`（单体）/ `bootstrap-nacos.yml`（微服务） |
| 日志 | `assets/config/logback-spring.xml` |
| 结构变更 | 模板与规范见 [`skills/database-ops/`](../../database-ops/SKILL.md)，产出落到 `src/main/resources/db/migration/postgresql/` |

## 五、配置安全（交付门禁项）

所有 yml / properties / Java 提交前必须过 `bash scripts/check_secrets.sh src`（命中即打回）：

- 配置文件里机密键（password / secret / access-key / api-key / token）的值只能是 `${ENV}` 占位或空串。
- Java 里禁止给机密占位符配默认值：`@Value("${jwt.secret:anything}")` 这种写法等价于把口令写进仓库。
- 不得出现内网 IP:port、Nacos namespace UUID、第三方平台 AppSecret。

`JwtProperties` / `JwtConfig` 不允许有默认密钥——缺失时启动直接失败（fail-fast），比带病上线安全。
