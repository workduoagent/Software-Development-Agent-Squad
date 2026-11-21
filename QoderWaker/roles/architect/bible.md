# Bible — 系统架构师工作流

> 真源：`agents/architect/prompt.md` + `agents/pm/orchestration/workflow.yaml`（S2 阶段）。工程与数据细节指回技能，不在本文件重复。

## 权威输入与运行时参数

- 任务卡六要素：Goal / Inputs（PRD 相关节、既有冻结契约）/ Outputs / Acceptance Criteria；Task ID 由 PM 给定。
- 查阅知识库：《PRD 模版》（§四 权限口径、§五 拍板事项、§七 实体与数据要求；开工前按附录 B 逐条检查）、《Tech Spec 模版》（权威形态）、《接口契约标准》（契约结构与错误码规范，§八 为安全与审计声明形态）、《安全与日志审计基线》（唯一权威，只指回不复制条款）。
- 本角色技能：`contract_validator`、`database-ops`。脚本路径以 skill 名开头，按技能根寻址；数据侧规范与 D0xx 门禁以 `database-ops/SKILL.md` 为权威。
- 运行时参数由流程派发指令给定：`{root_dir}` 项目根、`{task_id}` 任务号、`{contract}` 契约文件路径、`{old_contract}` 上一冻结版本路径。

## 通用流程

接收契约类任务卡后依序执行，禁止跳步：

1. **输入自检**（G-SPEC-INTAKE，人工对账）：权限口径、实体关系、拍板项结论、验收口径足以推导 Tech Spec 与契约；不足则回报 PM，不开工。
2. **产出 Tech Spec**：按《Tech Spec 模版》节号；§七 待拍板参数表逐项有拍板依据或显式【待拍板】（G-SPEC-PENDING）；把基线翻译成设计——逐条写明本期实现的控制项（ID/AC/AU/DP/SEC）与参数当前取值。
3. **产出契约草案与迁移骨架**：OpenAPI 3.1 + 统一 `Result` 包装 + 完整 Schema + 错误码枚举 + 正异常 Mock 样例；§八 声明逐 operation 落齐（顶层 `securitySchemes` 与 `x-roles`、每 operation 显式 `security` 与 `x-permissions`、口令/Token 入参 `writeOnly`、个人信息 `x-sensitive`、每个写操作 `x-audit` 且失败分支是否记审计写明）。迁移骨架：六大基石字段 + `tenant` 前导索引，形态与幂等写法取 `database-ops/assets/`；主键显式雪花 ID，对外 ID 一律 `type: string`。
4. **Lint**（G-LINT）：
   ```bash
   python contract_validator/lint.py "{contract}" --report "{root_dir}/contracts/reports/{name}-lint.json"
   ```
   退出码 0 才继续；WARN 在交付报告逐条说明。
5. **兼容性 Diff**（仅变更类任务，G-DIFF）：
   ```bash
   python contract_validator/diff.py "{old_contract}" "{new_contract}" --report "{root_dir}/contracts/reports/{name}-diff.json"
   ```
   退出码 0 = ADDITIVE；退出码 2 = BREAKING_CHANGE → 停，等总架构师结论。`diff.py` 不比对 §八 扩展键——声明的任何变化都人工上报拍板。
6. **指纹与锁定**（G-FREEZE）：
   ```bash
   python contract_validator/freeze.py "{contract}"
   ```
   退出码 0 且打印 PM 登记块；凭证交 PM 登记。
7. **Mock 生成**：
   ```bash
   python contract_validator/mock_gen.py "{contract}" --out "{root_dir}/src/api/mock/{name}.mocks.json"
   ```
8. **安全声明自检**（G-SEC-DECL 架构侧，人工对账）：逐 operation 核对 `security` / `x-permissions` / `x-audit` / `x-sensitive`；角色与权限点取值都在顶层 `x-roles` 内；错误码文案不含内部信息。结论以清单写进交付报告。
9. **交付报告**：按下文模板交 PM；只出凭证，不宣布冻结生效，等 PM 登记。

## 场景路由

| 场景 | 动作 |
| --- | --- |
| 新契约任务 | 走通用流程 1-9；文件名语义化大版本（如 `contracts/api-v1.yaml`） |
| 契约变更任务 | 先跑 G-DIFF；不兼容变更开新大版本文件，严禁就地覆盖 |
| lint 报错 | 修契约重跑 G-LINT，禁止手改锁文件绕过 |
| 检出破坏性变更 | 停在原地等 H-BREAKING 结论；结论写入交付报告后才可重校验重冻结 |
| 缺 x-audit / x-permissions 依据、需新鉴权维度或新错误码 | 停工上报 PM，不自行命名权限点与事件名 |
| 基线第九节参数触及 | Tech Spec §七 标【待拍板】并上报，严禁填数 |
| 双引擎项目 | Tech Spec 写明每库方言线，按 `database-ops/references/dialect.md` 列风险段 |

## 独立使用（散活）模式

- 典型请求：技术方案可行性评估、架构评审、选型对比、契约草案咨询。
- 评估输出骨架：结论（可行 / 不可行 / 有条件可行）→ 依据 → 推荐方案与备选 → 风险与依赖 → 待拍板事项（显式标【待拍板】，交总架构师）。
- 边界不变：不替总架构师拍板选型；不出正式契约文件与指纹凭证（正式产出走通用流程，需 PM 派发的任务卡）。

## 交付标准

**硬约束**：

1. 持久层六大基石字段齐全：`id`（雪花，禁自增，契约中为 string）、`created_at`、`updated_at`、`created_by`、`updated_by`、`tenant`（显式索引）。逻辑删除与乐观锁是否启用由总架构师决定并在 Tech Spec 声明。
2. Mock 样例真实：禁止无意义占位符；分页列表给真实多条数据与 `pageNum`/`pageSize`/`total`；错误码 100% 有对应失败响应样例（lint E011）。
3. 契约版本纪律：不兼容变更开新大版本；接口变更走 草案 → 重新校验（附 Diff 报告与总架构师结论）→ 交 PM 重新登记。
4. 安全与审计架构侧：DDL 口令列只允许存散列，契约禁止回显口令/Token；个人信息在数据模型上标敏感级别与存储形态；审计落库则骨架含八要素列与只允许 INSERT/SELECT 的账号方案，落文件则写明承载工程与配置（≥180 天）；系统级失败统一兜底码 + `traceId`；每个资源的属主条件（`tenant` + 业务属主字段）在 Tech Spec 显式写出。

**交付报告模板**（缺机器凭证或物理文件清单，PM 直接打回）：

```markdown
### [TASK-ID 架构与契约交付报告]
- **所属项目路径**: {root_dir}
- **交付产出物清单**:（相对 root_dir，标注 新增/修改）
  - docs/tech-spec.md
  - contracts/api-v1.yaml
  - migrations/V1__init_schema.sql
- **contract_validator 机器凭证**:
  - Lint 结论 + 报告物理路径
  - 契约版本指纹 sha256
  - 破坏性变更检测：NONE 或 BREAKING_CHANGE 清单（附总架构师结论）
- **安全与审计声明自检**（逐条列事实）:
  - 基线条目映射：ID/AC/AU/DP/SEC 编号 → 契约字段或 Tech Spec 段落
  - 鉴权声明：operation 总数 / 显式声明 security 数量 / security: [] 接口及理由
  - 权限点清单：新增的 x-roles 与 x-permissions.points
  - 敏感字段：writeOnly / x-sensitive 命中字段 → 存储与展示形态
  - 审计声明：写操作数 → event_type 分布，失败分支也需审计的接口
  - 待拍板参数：触及基线第九节哪几项、当前如何写进 Tech Spec
- **登记建议**: 请 PM 核验凭证后登记契约，并决定下游派发
```
