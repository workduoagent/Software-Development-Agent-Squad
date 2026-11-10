# 迁移、灰度与回滚

## 一、版本与命名（Flyway 10.17）

| 规则 | 内容 |
| --- | --- |
| 目录 | `src/main/resources/db/migration/`，两条方言线各自独立目录：`db/migration/postgresql/` 或 `db/migration/mysql/`，靠 `flyway.locations` 按 profile 选择，禁止同一目录混放两种方言（D009 判定） |
| 命名 | `V{n}__{snake_case_描述}.sql`，`n` 严格递增且**项目内唯一**（D010） |
| 不可改写 | 已提交（已进过任何环境）的脚本一个字符都不改。要改就开新版本，改了会导致其他环境 `validate-on-migrate` 校验和失败，且失败信息只提示 checksum，很难联想到"有人偷偷改了老脚本" |
| 可重复脚本 | `R__{描述}.sql` 只用于视图、字典初始化等**自身幂等**的对象，禁止用它跑一次性修数 |
| 单文件粒度 | 一个脚本一件事：加列、回填、加约束各自成版本，便于定位失败点与选择性回滚 |
| 配套 | 迁移脚本与实体字段变更必须在同一任务提交，PR 描述互链；表结构变更同时更新契约的 DDL 章节 |
| 校验 | `validate-on-migrate: true`、`out-of-order: false`（乱序版本说明有人绕过流程） |

## 二、大表在线变更

千万行以上，DDL 的目标是**不长时间阻塞写入**。两条线的可行路径：

| 变更 | PostgreSQL 16 | MySQL 8 |
| --- | --- | --- |
| 加列（带默认值） | 直接 `ADD COLUMN ... NOT NULL DEFAULT const`，11+ 不重写整表，只改元数据 | `ALTER TABLE ... ADD COLUMN ..., ALGORITHM=INSTANT, LOCK=NONE`；8.0 的 INSTANT 有列位置与次数限制，超限自动降级为 COPY，必须显式写算法让降级暴露成报错而不是悄悄锁表 |
| 加索引 | `CREATE INDEX CONCURRENTLY`（**不能在事务里**，见第四节） | `ALTER TABLE ... ADD INDEX ..., ALGORITHM=INPLACE, LOCK=NONE`；不支持 `CONCURRENTLY` 语义，但 INPLACE 期间 DML 可继续 |
| 改列类型 | 必须重写整表并持 `ACCESS EXCLUSIVE` 锁 → 新建列 + 双写 + 回填 + 改名切换 | 大部分类型变更只能 `COPY`（全表重建，等同锁写）→ 同样走影子表/新列方案，或使用 `gh-ost`/`pt-online-schema-change`（需 DBA 确认工具在位） |
| 加 `NOT NULL` | 先加 `CHECK` 并 `NOT VALID`，回填后 `VALIDATE CONSTRAINT`，最后保留约束 | 先回填再 `MODIFY`，无法分步，必须选窗口 |
| 重命名 | `ALTER TABLE ... RENAME` 是元数据操作，代价极低 | 同左，但注意会隐式提交 |

通用形态：**扩展（加新）→ 双写 → 回填 → 切换 → 收敛（删旧）**，每一步独立成版本、独立可回滚。任何"一条脚本改完"的大表变更直接打回。

## 三、约束与索引的安全补建

存量脏数据会让 `ADD CONSTRAINT` 失败并锁表。安全顺序：

```sql
-- dialect: postgresql
ALTER TABLE biz_project ADD CONSTRAINT ck_biz_project_kind
    CHECK (kind IN ('external', 'internal')) NOT VALID;

-- 先查脏数据，结果为 0 才继续（这条 SELECT 也留在脚本注释里作为校验依据）
SELECT count(*) FROM biz_project WHERE kind NOT IN ('external', 'internal');

ALTER TABLE biz_project VALIDATE CONSTRAINT ck_biz_project_kind;
```

`NOT VALID` 只挡住新写入，`VALIDATE` 会全表扫描但不与常规读写冲突。MySQL 8 的 `CHECK` 没有等价的 `NOT VALID` 分步语义，必须先修数据再加约束 [MySQL 未经公司实测]。

## 四、事务性差异（最容易出事故的一条）

| | PostgreSQL | MySQL |
| --- | --- | --- |
| DDL 是否在事务内 | **是**：`BEGIN; ALTER...; ROLLBACK;` 可完整撤销，脚本里多条 DDL 要么全成要么全不动 | **否**：DDL 隐式提交，`ALTER` 执行到一半失败就是"半套 schema"落地，只能靠备份恢复 |
| 失败后的状态 | 干净（回到执行前） | 不一致：可能表已建、索引未建；或列加了一半（多列 `ALTER` 中途失败） |
| 迁移脚本写法 | 一个脚本可放心放多条 DDL | 一个脚本只放**一条** DDL，或按可独立重跑的方式组织 |
| Flyway 记录 | 失败版本自动回滚，重跑即重来 | 失败版本留在 `flyway_schema_history` 且 `success=0`，必须**手工清理该行**（并确认 schema 实际状态）后才能重跑 |

`CREATE INDEX CONCURRENTLY` 的两点代价：不能跑在事务里，Flyway 需对该脚本单独关闭事务（`spring.flyway.execute-in-transaction=false` 是全局项，局部做法是把它拆到 `R__` 之外的独立迁移并在文件名标注 `no-tx`，或改由变更窗口手工执行）；中途失败会留下 `indisvalid = false` 的 `INVALID` 索引，必须先 `DROP INDEX` 再重建，直接重跑 `IF NOT EXISTS` 会静默跳过这个坏索引。

## 五、上线与回滚清单（逐条签认）

1. 变更单已填全，影响行数列有预查证据。
2. 目标环境**已有可恢复备份**并记下方言相关的产物路径与恢复命令（`operations.md` 第四节）。生产结构变更前没有备份，等同于无回滚方案。
3. 回滚脚本存在且在演练环境跑过。`U{n}__*.sql` 是社区版 Flyway 的人工回滚约定，不会自动执行：要么随版本一起提交并在变更单里写"回滚=执行 U 脚本"，要么写清"回滚=恢复备份"并给出恢复时长。
4. 执行窗口与预估耗时：大表 `ALTER`/建索引要给出实测耗时（在接近生产数据量的副本上跑一次），不接受"应该很快"。
5. 应用与库的**发布顺序**：先加列后发代码（新代码依赖新列），删列要等旧代码全部下线之后。任何时刻线上运行的代码必须能同时兼容"变更前"与"变更后"两种 schema。
6. 从库/CDC/数仓下游已确认结构变更。
7. 失败处置人在线，回滚决策点事先约定（例如"回填超过 30 分钟即回滚"）。
8. 变更完成后跑校验 SQL 并留存输出，作为交付凭证（与 `review-criteria.md` 的证据要求一致）。

## 六、存量库接入

- 已有库首次纳入 Flyway：`baseline-on-migrate: true` + 明确 `baseline-version`，让工具从当前版本起步，而不是重跑历史。
- 接入前必须做一次 schema 对账：把线上实际结构与仓库里应有脚本序列的产物 diff，缺的补 `V{n}__align_*.sql`。现网 README 自述其他模块建表"（`ddl-auto` 或 flyway 视 Nacos 配置而定）"——**schema 归属不明确就是没有治理**，接入时第一个任务就是把每张表的来源钉死。
- 禁止 `ddl-auto=update/create`（JPA 场景）出现在任何 profile。它会按实体反向改生产库，绕过所有评审。
- 多环境一致性：dev / staging / prod 必须跑同一份脚本序列；环境间靠"手工改一下"造成的差异，会在下一次迁移以 checksum 冲突的形式爆掉。
