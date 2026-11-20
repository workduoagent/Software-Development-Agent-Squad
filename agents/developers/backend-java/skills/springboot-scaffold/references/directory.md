# 工程拓扑与分层

两种拓扑共用同一套分层纪律，只是模块切分不同。新建工程先选拓扑，再按对应结构建目录。

## 一、分层职责（两种拓扑都一样）

```
controller   只做「契约 ↔ 内部对象」转换 + 参数校验，禁止写业务分支
service      业务编排、事务边界、跨表/跨服务调用
mapper(repo) 只与单表打交道，复杂查询才下沉 XML
pojo         entity（表映射）/ dto（入参）/ vo（出参）三类，禁止 entity 直接进出接口
```

硬性约束：

1. **Controller 返回 `Result<XxxVO>`**，入参用 `@Valid XxxDTO`；`entity` 出现在 Controller 签名上即打回。
2. **事务只在 service 层**，`@Transactional(rollbackFor = Exception.class)` 必须带 `rollbackFor`——默认只回滚 RuntimeException，受检异常会静默提交。
3. **禁止 Controller 互相调用**、禁止 service 依赖 `HttpServletRequest`（要当前用户就取 `UserContext`）。
4. **DTO/VO 与契约字段逐字一致**：`msg` 不是 `message`；ID 是 `String`（`@JsonSerialize(ToStringSerializer)`）。

包结构（单体为例，`${base-package}` 由总架构师在项目初始化时定）：

```
${base-package}
├── controller        REST 入口，一个契约资源一个类
├── service           接口 + impl 子包
├── mapper            MyBatis-Plus Mapper
├── pojo
│   ├── entity        与表一一对应，继承 BaseEntity
│   ├── dto           请求入参（带校验注解）
│   └── vo            响应出参
├── common            Result / ErrorCodeEnum / BusinessException / UserContext
├── audit             审计事件枚举/注解/写入器/切面 + 脱敏工具（见 references/security-audit.md）
├── config            MP / JWT / MVC / 线程池
├── aspect|interceptor 鉴权与限流（拓扑相关）
├── exception         GlobalExceptionHandler
└── util              无状态工具，禁止放业务逻辑
resources/
├── db/migration      Flyway 脚本，按方言分子目录（规范见 skills/database-ops）
├── mapper            复杂查询 XML
├── application.yml / bootstrap.yml
└── logback-spring.xml
```

## 二、单体拓扑（默认）

一个 Maven 模块，一个可执行 jar。适合：单业务域、日活量级可控、没有多团队并行部署需求。

```
example-server/
├── pom.xml                  assets/config/pom-single.xml
└── src/main/java/...        上面那套包结构
```

- 鉴权：`@ApiRegister` + AOP 切面（见 `topology.md`）
- 配置：本地 `application.yml` + profile 文件，无配置中心
- 部署：单进程，Redis 用于限流与缓存

## 三、微服务拓扑

三层 Maven 结构，父 pom 只管版本，不引入实际依赖。

```
example-cloud/
├── pom.xml                  assets/config/pom-parent.xml   packaging=pom
├── app-core/                packaging=pom
│   ├── app-core-common      Result / ErrorCodeEnum / UserContext / utils（jar，须 skip repackage）
│   ├── app-core-config      MP / JWT / Redis 配置类（jar，须 skip repackage）
│   └── app-core-web         拦截器、GlobalExceptionHandler（jar，须 skip repackage）
└── app-server/              packaging=pom
    ├── app-server-gateway   WebFlux + Spring Cloud Gateway，唯一对外入口
    ├── app-server-sys       业务服务（可执行 jar）
    └── app-server-xxx       每加一个服务复制一份
```

硬性约束：

1. **公共 jar 模块必须 `<skip>true</skip>` spring-boot-maven-plugin**（见 `assets/config/pom-jar-module.xml`）。否则会被打成可执行 jar，下游依赖时报「没有主清单属性」。
2. **只有 app-server-* 里放主类**，app-core-* 一个 `@SpringBootApplication` 都不许有。
3. **gateway 是 WebFlux**：不得引 `spring-boot-starter-web`；其他业务服务是 MVC，不得混入 reactive web。
4. **服务间调用只走注册中心服务名 + OpenFeign**，禁止写死 IP/端口。

## 四、拓扑选择判定

| 信号 | 结论 |
| --- | --- |
| 只有一个业务域、一个团队、一份数据库 | 单体 |
| 需要独立发布节奏 / 多语言服务 / 需要 API-Key 开放平台 | 微服务 |
| 说不清 | 单体（微服务的运维成本要在契约冻结前由总架构师确认） |
