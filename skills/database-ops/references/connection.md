# 数据连接与连接池

## 一、参数落位原则

连接配置分三层，**只有第三层允许离开仓库**：

| 层 | 内容 | 位置 | 理由 |
| --- | --- | --- | --- |
| 结构层 | 池大小、超时、keepalive、URL 参数 | 仓库 `src/main/resources/application.yml` | 这些是性能与稳定性的契约，必须进代码评审 |
| 环境层 | 库名、schema、非敏感开关 | profile 文件 / 启动参数 | 按环境变化但不涉密 |
| 机密层 | host、端口、账号、口令 | 环境变量或配置中心，`${ENV}` 占位 | 不得进仓库，`check_secrets.sh` 拦截 |

现网反面教材：we-agent-cloud 把整份数据源放进 Nacos（`app-server-sys/src/main/resources/bootstrap.yml:16-19`），仓库里 `hikari` 零命中、`jdbc:` 零命中，等于**连接契约无人评审**。基线不接受这种外置方式。

凭据缺失必须 fail-fast：`password: ${DB_PASSWORD}` 不给默认值。给默认值会把"配置没注入"变成"用错误身份连上了"或"启动成功但功能全废"，排查成本更高。

## 二、HikariCP 基线（Boot 3 默认池，无 Druid）

| 参数 | 基线值 | 依据 |
| --- | --- | --- |
| `maximum-pool-size` | 10（起步）| 池大小不是越大越好。经验式 `cores × 2 + 有效磁盘数`；超过数据库承载后吞吐不升反降，排队从池子移到锁上更难查 |
| `minimum-idle` | 与 max 相同 | 稳态服务不做弹性伸缩，避免流量突增时集中建连（一次 TLS + 认证约 10-30ms） |
| `connection-timeout` | 10000 | 拿不到连接要在 10s 内失败并触发熔断/降级。Boot 默认 30s 会让上游线程堆积 |
| `max-lifetime` | 1740000（29min） | 必须**小于**数据库或中间件的空闲回收时间，且提前 30-60s。MySQL `wait_timeout` 默认 28800s；RDS Proxy / PgBouncer 常设 5-15min，此时以更小者为准 |
| `idle-timeout` | 600000 | 仅当 `minimum-idle < maximum-pool-size` 时生效 |
| `keepalive-time` | 30000 | 防 NAT / LB 静默掐连接；0 表示关闭，云上部署建议开启 |
| `leak-detection-threshold` | 60000（dev/staging 必开） | 打印未归还连接的堆栈，是抓 `Connection`/`SqlSession` 泄漏的唯一手段。生产可关，开销在采样 |
| `pool-name` | 显式命名 | 多数据源与 JMX/Micrometer 指标的唯一区分方式，缺省 `HikariPool-1` 无法排障 |
| `initialization-fail-timeout` | 1 | 启动即验证连通性，坏配置直接拒绝启动，交给编排系统重启而不是半死不活地服务 |

不要用 `connection-test-query`：JDBC4 的 `isValid()` 更准且无 SQL 解析开销，配了反而绕开驱动的空闲检测。

监控接入：Micrometer 的 `hikaricp.connections.*`（active / idle / pending / creation / usage），`pending` 持续非零即池子不够或慢查询占位。

## 三、JDBC URL 参数

### PostgreSQL 16

```
jdbc:postgresql://${DB_HOST}:${DB_PORT:5432}/${DB_NAME}?currentSchema=${DB_SCHEMA:public}&ApplicationName=${spring.application.name}&connectTimeout=10&socketTimeout=120&tcpKeepAlive=true&reWriteBatchedInserts=true&prepareThreshold=5&sslmode=${DB_SSLMODE:disable}
```

| 参数 | 作用 | 注意 |
| --- | --- | --- |
| `ApplicationName` | 在 `pg_stat_activity` 里定位是哪个服务打满连接 | 多服务共用实例时是唯一的排障抓手，必填 |
| `connectTimeout` | 建连超时（秒） | 默认 10，保持 |
| `socketTimeout` | 单条 SQL 网络读超时（秒），**默认 0 即永不超时** | 必须设。不设时一条挂死的查询会永久占住连接，池子被缓慢耗尽 |
| `tcpKeepAlive` | 打开 TCP 保活 | 与 `keepalive-time` 配合 |
| `reWriteBatchedInserts` | 把 JDBC batch 的重写合并成多值 `INSERT` | 只对单表批量插入有效；配合 MyBatis-Plus `saveBatch` 才看得出收益 |
| `prepareThreshold` | 第 N 次起转服务端预编译 | 默认 5。连接数紧张时调大或设 1 |
| `stringtype=unspecified` | 让字符串参数按目标列类型隐式转换 | **禁用**：它会掩盖真实类型错配，enum/数字列写字符串能在单测通过、在生产报错 |
| `sslmode` | 生产用 `verify-full` + `sslrootcert` | `disable` 只允许本机/内网专线且 Tech Spec 明确记录 |

### MySQL 8 [MySQL 未经公司实测]

```
jdbc:mysql://${DB_HOST}:${DB_PORT:3306}/${DB_NAME}?useUnicode=true&characterEncoding=UTF-8&connectionTimeZone=%2B08:00&forceConnectionTimeZoneToSession=true&rewriteBatchedStatements=true&cachePrepStmts=true&prepStmtCacheSize=250&prepStmtCacheSqlLimit=2048&useServerPrepStmts=true&tinyInt1isBit=false&connectTimeout=10000&socketTimeout=120000&autoReconnect=false&sslMode=${DB_SSLMODE:DISABLED}&allowPublicKeyRetrieval=true
```

| 参数 | 作用 | 注意 |
| --- | --- | --- |
| `rewriteBatchedStatements` | 让 `addBatch` 真正合并 | 不设时 MySQL 驱动逐条发送，批量插入慢一个数量级，这是"MySQL 批量比 PG 慢"的头号原因 |
| `useServerPrepStmts` + `cachePrepStmts` | 服务端预编译与语句缓存 | 与 `rewriteBatchedStatements` 同时开启才有效果 |
| `connectionTimeZone` / `forceConnectionTimeZoneToSession` | 固定会话时区 | `DATETIME` 不带时区，服务端与 JVM 时区不一致就整体偏移。必须显式钉死并在 Tech Spec 记录 |
| `tinyInt1isBit=false` | `TINYINT(1)` 映射为整数 | 默认映射成 `Boolean`，会破坏"0/1 状态 + 2/3 扩展值"的列设计 |
| `autoReconnect=false` | 禁止驱动自动重连 | 开启后重连会丢会话变量、临时表与事务上下文，故障时表现诡异。交给连接池重建 |
| `allowPublicKeyRetrieval` | `caching_sha2_password` 首次认证取公钥 | 只在 `sslMode=DISABLED` 的内网成立；生产走 TLS 时应关掉，否则中间人可注入公钥拿口令 |
| `zeroDateTimeBehavior` | `0000-00-00` 处理 | 保持默认 `EXCEPTION`，配 `sql_mode` 含 `NO_ZERO_DATE`。改成 `CONVERT_TO_NULL` 等于默许脏数据入库 |

## 四、超时链路必须分层收敛

数据库侧超时只是整条链路的一环，**由内向外递增**，否则内层刚超时外层已经放弃，故障归因会指向错误的组件：

| 层 | 参数 | 建议 |
| --- | --- | --- |
| 服务端单条语句 | PG `statement_timeout` / MySQL `MAX_EXECUTION_TIME` | 30s（按业务最长合法查询设，见 `operations.md` 第三节可按账号覆盖） |
| 服务端锁等待 | PG `lock_timeout`、`idle_in_transaction_session_timeout` / MySQL `innodb_lock_wait_timeout` | 5s / 10s。空闲事务必须回收，长挂的 `idle in transaction` 会挡住 vacuum 与 DDL |
| 驱动读超时 | `socketTimeout` | 120s，必须大于上面两项，小于池超时 |
| 池获取超时 | `connection-timeout` | 10s |
| 上游调用超时 | HTTP / Feign / 网关 | 大于池超时，避免上游超时后连接仍被占用形成堆积 |

## 五、多数据源

现网 nexus 用 business + vector 两套 DS（`BusinessDataSourceConfig.java:32-35`、`VectorDataSourceConfig.java:25-28`），教训可直接复用：

1. 每个 DS 独立 `pool-name` 与独立 `PlatformTransactionManager`；`@Transactional` 跨 DS **不会**传播，必须显式写 `transactionManager = "xxx"`，否则你以为的原子性根本不存在。
2. 没有 Seata/XA 就不要假装有分布式事务。跨 DS 写用"本地事务 + 状态表 + 补偿任务"的最终一致设计，并在 Tech Spec 里写明可接受的不一致窗口。
3. 总连接预算 = 单池 max × 实例数 × DS 数，必须小于服务端 `max_connections × 0.8`。多服务共用一个库时，这条最容易先炸。
4. 读写分离若真要上，优先用只读账号 + 显式路由，不要用拦截器透明改写：复制延迟会让"写完立刻查"读到旧数据，这是用户可感知的错误，必须在设计阶段声明。
