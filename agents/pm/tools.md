# PM 工具依赖与物理对账规范 (Local Filesystem Mode)

本项目经理智能体（PM）**不依赖任何外部项目管理 SaaS 平台（如 Jira、GitHub Issues）**，完全基于本地文件系统的物理文件与 JSON 账本驱动多项目流转。

---

## 一、 PM 所需的工具权限

### 1. 基础文件系统工具 (Filesystem Tools)
* `read_file(path)`：读取本地任务账本、契约规范、交付代码及测试日志。
* `write_file(path, content)`：创建/覆盖/更新本地任务账本 `tasks.json`。
* `list_directory(path)`：扫描目标项目的物理目录，核验文件落盘状态。

### 2. 本地技能脚本 (Skills)
* `contract_validator`（`skills/contract_validator/`）：契约 Lint、兼容性 Diff 与指纹计算。调用主体为 architect（交付契约前必须调用并出具校验凭证）；PM 核验其 Lint 报告与 sha256 指纹后方可登记冻结并批准下游开工，无凭证严禁放行。
* `artifact_inspector`（`skills/artifact_inspector/`）：物理文件与测试日志质检，辅助物理验收（存在性、非空、测试通过率核验）。

> 看板与任务持久化直接通过文件系统工具读写 `tasks.json` 完成，后续可由 `skills/task_tracker/` 封装。

---

## 二、 核心任务账本约定 (`tasks.json`)

**唯一权威账本**：仓库根目录下的 `tasks.json`。`agents/pm/examples/tasks.json` 仅为 Few-Shot 示例，严禁当作运行时账本读写。

### 账本设计原则
1. **多项目隔离**：以 `projects` 数组划分不同项目，每个项目声明其物理根路径 (`root_dir`，相对仓库根目录)。
2. **物理文件校验**：子任务中声明的 `inputs` 与 `outputs`，均相对于该项目的 `root_dir`，PM 必须通过物理存在性检查核验产出物。
3. **单写者原则**：`tasks.json` 仅由 PM 统一写入。成员只汇报进度与产出，严禁自行修改账本；所有状态流转由 PM 对账后落笔。

### 状态机与打回记录

状态枚举、流转责任、`rejection_history` 条目结构与报警红线的权威定义见 `orchestration/state_machine.md`；任务字段标准见 `docs/02-protocols/task-schema.json`。

### 契约冻结登记 (`contracts`)

每个项目维护 `contracts` 登记表，契约经 `contract_validator` 校验（architect 执行）、PM 核验凭证后登记冻结，作为下游开工的唯一凭证：

```json
{
  "path": "contracts/auth-api-v1.yaml",
  "version": "1.0.0",
  "sha256": "<契约文件内容的 SHA-256>",
  "frozen_at": "2026-11-09T20:15:00Z"
}
```

契约变更必须由 architect 重新校验（含兼容性 Diff，破坏性变更附总架构师决策结论），PM 核验后重新登记（version 递增，sha256 与 frozen_at 刷新）；未登记的契约视为未冻结。
登记（含重新登记）前，PM 额外人工核对契约的安全与审计声明齐备（`api-contract-spec.md` §八：`securitySchemes` / `x-roles` / 逐 operation 的 `security` 与 `x-permissions` / 写操作 `x-audit` / 敏感字段 `x-sensitive` 与 `writeOnly`）——`lint.py` 不查这些，缺项即不登记；权限或审计声明发生任何变化（含放宽）须附总架构师决策结论。

---

## 三、 PM 执行物理验收的操作规程

当成员汇报任务已完成时，PM 不听口头汇报，必须按以下三步通过工具对账（验物与记账对应 prompt 的五步验证流程）；分角色验收判据细则以 `docs/02-protocols/review-criteria.md` 为准：

1. **查账**：调用 `read_file("tasks.json")`，确认该任务处于 `IN_PROGRESS` 或 `IN_REVIEW`；同时核验其 `inputs` 依赖的上游任务均已 `ACCEPTED`、契约类输入已在项目 `contracts` 登记表冻结。
2. **验物**：
   - **文件存在性检查**：获取该项目的 `root_dir`，对任务声明的所有 `outputs` 路径，调用 `list_directory` / `read_file(root_dir + "/" + output_path)` 核验物理存在且非空。若文件不存在或为空，**严禁通过**。
   - **测试日志校验**：优先采信 QA 产出的测试报告制品（`qa/reports/`、`qa/logs/`）及成员提供的单测运行日志，核验 `Pass: 100%`。
   - **安全门禁校验**：核验提测报告中的 `check_secrets.sh` / `check_security.sh` 输出段——必须是真实落盘日志（含退出码与 `[INFO]` 取证行），摘录能在日志文件里原文找到；PM 可在 `root_dir` 重跑脚本复核。出现 ERROR 命中、留存天数等取证值与报告不符、或存在无理由的 `#nosec:` / `// nosec-fe:` 豁免，按未达标打回，**不得代为判定"这个风险可以接受"**（安全参数与豁免一律是总架构师的决策）。
   - **数据门禁抽查（非每卡必做）**：`check_db_ops.sh`（D001-D015）默认由开发自跑留凭证，PM 对含 `.sql` 或数据源配置变更的交付按批次抽卡，在 `root_dir` 重跑 `bash skills/database-ops/scripts/check_db_ops.sh <报告所列目录>`，比对退出码与 `[INFO]` 覆盖范围行；抽中"报告说绿、重跑说红"即整批打回，后续同类任务提到每卡必查。变更单的备份恢复段与执行窗口段属人工判据，核的是证据不是脚本。
   - **副作用扫描**：核对公共依赖与配置文件（包管理清单、锁文件、共享配置等）是否存在任务声明之外的改动；发现未声明改动即视为未达标。
3. **记账**：
   - 验收通过：将该任务在 `tasks.json` 中的 `status` 修改为 `ACCEPTED`，写入完成时间字段 `accepted_at`。
   - 验收失败：修改为 `REJECTED`，并在 `rejection_history` 中按权威结构追加本轮打回记录与具体未达标证据。
   - 调用 `write_file("tasks.json", updated_content)` 写回磁盘。