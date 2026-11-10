# 持久层规范

数据库统一 PostgreSQL，ORM 统一 MyBatis-Plus（不用 JPA）。表结构变更统一走 Flyway。

## 一、六大基石字段

每张业务表必须齐全，缺任一项 PM 强制否决（同 `docs/02-protocols/api-contract-spec.md`）。

| 列 | 类型 | 生成方式 | 说明 |
| --- | --- | --- | --- |
| `id` | BIGINT 主键 | 应用侧雪花（`IdType.ASSIGN_ID`） | **禁止** BIGSERIAL / IDENTITY；对外 JSON 序列化成字符串 |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | MP INSERT 填充 | |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | MP INSERT_UPDATE 填充 | |
| `created_by` | BIGINT | MP INSERT 填充，取 `UserContext` | |
| `updated_by` | BIGINT | MP INSERT_UPDATE 填充 | |
| `tenant` | BIGINT NOT NULL DEFAULT 0 | MP INSERT 填充 | **必须建单列索引**，租户隔离的唯一查询入口 |

- `is_deleted`（软删除）、`version`（乐观锁）**不是基石**：只有契约里有对应语义时才加，且加了之后所有查询必须显式带上条件。
- 字典/配置表如果确实无租户概念，可以不带 `tenant`，但要在 DDL 注释里写明理由，并在租户过滤处显式排除。
- 迁移旧库时字段名不同（参考项目用的是 `create_at`/`create_by`），用 `@TableField("create_at")` 显式映射，不改契约命名。

## 二、实体与序列化

`assets/persistence/BaseEntity.java` → `pojo/BaseEntity.java`，所有 entity 继承它。

Long 精度陷阱：雪花 ID 19 位，超过 JS `Number.MAX_SAFE_INTEGER`，直出必然精度丢失。
**逐字段** 加 `@JsonSerialize(using = ToStringSerializer.class)`，不要做全局 Long→String 配置——
那会把数量、时长等正常数值也变成字符串，前端 `+`/`toFixed` 全线出错。

时间统一 `LocalDateTime` + `@JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")`，
契约里对应 `type: string, format: date-time`。

## 三、MyBatis-Plus 配置

`assets/config/MybatisPlusConfig.java`

- `PaginationInnerInterceptor(DbType.POSTGRE_SQL)` —— **方言必须写死**。不写时按 JDBC URL 推断，测试库/内存库会拼出错误分页语句。
- `setOverflow(false)`：页码越界返回空列表，不回跳首页（回跳会让前端以为"还有数据"）。
- `setMaxLimit(500L)`：契约里 `pageSize` 的上限由后端强制，不依赖前端。
- `call-setters-on-nulls: true`：否则 `Map` 结果里 null 字段整个键消失，前端读到 undefined。
- `map-underscore-to-camel-case: true`：`created_at` ↔ `createdAt` 靠它。

## 四、自动填充

`assets/config/MybatisPlusFillHandler.java`

| 操作 | 方法 | 原因 |
| --- | --- | --- |
| insert | `strictInsertFill` | 调用方已显式赋值时不覆盖（导入历史数据要保留原创建时间） |
| update | `setFieldValByName` | 更新时间必须每次强制变；`strictUpdateFill` 在实体已有值时会跳过，留下脏时间 |

未登录上下文（定时任务/MQ）取到 null 时**跳过填充**，交给 DDL DEFAULT 兜底；禁止填 0 假装系统用户。

## 五、租户隔离

不用 `TenantLineInnerInterceptor` 自动改写 SQL——它对无 `tenant` 列的表（字典表、Flyway 历史表、
子查询里的临时表）会生成非法 SQL，且 count 语句与分页拦截器的顺序很容易出错，排查成本高于收益。

基线做法：

1. 所有业务查询在 `QueryWrapper` 里显式 `eq("tenant", UserContext.getCurrentTenant())`。
2. 跨租户访问只在 `UserContext.isSysTenant() == true` 时允许，并且必须走独立的 admin 接口，
   与业务接口分离，便于评审与鉴权配置。
3. 单测必须覆盖「A 租户查 B 租户数据」这条越权路径（返回 403xx 或空）。

## 六、Flyway 迁移

规范权威在 [`skills/database-ops/`](../../database-ops/SKILL.md)，本节只讲 Java 侧怎么接：

- 脚本放 `src/main/resources/db/migration/postgresql/`，模板是 `skills/database-ops/assets/postgresql/V1__example_baseline.sql`；
  命名、幂等、大表拆分、回滚与变更单一律按 `database-ops/references/migration.md`，机检走 `check_db_ops.sh`。
- `spring.flyway.locations` 用 `{vendor}` 占位，两条数据库线的目录物理分开，避免同一版本号在两个方言目录里重复。
- 迁移脚本与实体字段变更必须在同一个任务里提交，PR 描述里互链——这是 Java 侧的约束，脚本改了什么由变更单说。
- `ddl-auto` 在本项目里不存在（不用 JPA），任何"实体反向生成表结构"的做法一律打回。

## 七、SQL 与 XML

- 单表 CRUD 用 MP 条件构造器；超过两表 join 或需要窗口函数才写 `resources/mapper/*.xml`。
- 禁止 `select *`，查询侧红线见 `database-ops/references/dml.md` 第七节；mapper XML 里的 `${}` 拼接仍由本 skill 的 `check_security.sh` S002 拦，白名单标注写在命中行或其上两行。
- 分页列表接口必须返回 `{total, list}`（与契约一致），且 `total` 用 `COUNT(*) OVER()` 或独立 count 查询，不能靠内存分页。
