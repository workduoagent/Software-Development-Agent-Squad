# WakerFlow 生成底稿：软件开发流水线（S0-S8）

> 用法：新建 WakerFlow 时把本文件正文粘贴为自然语言流程描述。生成后按 `acceptance-checklist.md` 逐项对账。
> 底稿来源：`agents/pm/orchestration/workflow.yaml`（阶段 / 门禁 / 人工闸门 / 循环规则的权威定义）。

## 团队与实例

- **pm-01**（项目经理，单例）：唯一状态管理者，账本唯一写者，负责全部阶段内的门禁命令与账本命令。
- **architect-01**（系统架构师）：Tech Spec 与契约产出、机器校验凭证。
- **qa-01**（质检工程师）：集成与安全验证。
- **前端 / 后端 / 桌面程序员实例**（react-dev-01 / java-dev-01 / tauri-dev-01 / py-backend-dev-01；Vue、Rust 待技能后按同一模式扩展）：按任务卡技术栈由 pm-01 路由，多实例可并行。脚本实例（py-script-dev-01）主要服务散活模式，默认不进本流程。
- **总架构师 = 用户本人**，只在人工闸门出现；流程在每个人工闸门暂停等待用户答复。

## 运行时变量（每次触发时给定）

- `squad_root`：本机仓库根绝对路径。
- `ledger` = `{squad_root}/tasks.json`（中央账本）。
- `root_dir`：项目根路径（可指向仓库外工程）。
- `project_id`：项目前缀。
- `evidence_dir` = `{root_dir}/reviews`。

## 全局禁令

1. **流程本身不写账本**：所有账本读写只发生在 pm-01 的步骤内（task_tracker 脚本）。
2. **成员 Waker 不接收账本**：流程只向成员传任务卡内容；成员状态汇报不等于状态变更。
3. **验收结论只由 pm-01 宣布**：任何步骤不得自行标记完成；ACCEPTED / REJECTED 只出自 pm-01。
4. **门禁命令在各角色步骤内执行**：流程只消费报告文件与退出码做路由，不越位代跑。

## 主流程

### 触发

总架构师给出需求表述（IM 消息 / API 调用），流程开始。

### S0 需求受理与定界 → 调用 pm-01

- 产出 `{root_dir}/docs/prd-v{N}.md`：§三 建「已明确业务事实 / 待确认歧义与隐性约束」两栏澄清台账，§五 列待拍板事项。
- ⏸ **人工闸门 H-SCOPE**：用户答复需求歧义、确认范围与不做清单、确认 PRD 版本。
- ⏸ **人工闸门 H-TECH**：技术选型、拓扑、数据库与中间件由用户拍板。
- 出口判据：PRD 达 §十二 DoD 且 §三.2 无待答；不满足则相关事项标 BLOCKED，回到本阶段澄清，不进入 S1。

### S1 任务拆解与建账 → 调用 pm-01

- 按《任务字段标准》六要素拆解（Task ID = `{项目前缀}-{三位序号}`）；L 级任务强制二次拆解；写入账本。
- 首个可派任务只能是 architect 的契约与设计任务。
- 门禁 **G-LEDGER**：`python task_tracker/validate.py "{ledger}" --schema "{squad_root}/软件团队知识库/任务字段标准.json" --report "{root_dir}/reviews/ledger-validate.json"`，退出码 0、0 errors 通过；WARN 逐条记入派发说明。
- 建账后出看板（board.py）向用户汇报。

### S2 设计与契约产出 → 调用 architect-01

- 产出 Tech Spec（按模版节号，§七 待拍板参数表）、OpenAPI 3.1 契约草案（统一 Result 包装、完整 Schema、错误码枚举、正异常 Mock、§八安全与审计声明）、迁移脚本骨架（六大基石 + tenant 前导索引）。
- 依序门禁（禁止跳步）：
  - **G-LINT**：`contract_validator/lint.py` 退出码 0；报错则 architect 修契约重跑，禁止手改锁文件绕过。
  - **G-DIFF**（变更类任务）：`contract_validator/diff.py`；退出码 0 = ADDITIVE，退出码 2 = 破坏性变更 → 停在本阶段等结论。
  - **G-FREEZE**：`contract_validator/freeze.py` 退出码 0 且打印 PM 登记块。
  - mock_gen 生成 Mock；§八安全声明自检清单逐 operation 核对。
- ⏸ **人工闸门 H-PARAM**：基线第九节参数取值（口令策略、锁定阈值、Token 有效期、审计留存）由用户拍板；留白项 architect 不得填数。
- ⏸ **人工闸门 H-BREAKING**（仅当 G-DIFF 检出破坏性变更）：用户决策后 architect-01 才可重校验重冻结；未决策前流程停在本阶段。

### S3 登记冻结 → 调用 pm-01（唯一生效点）

- pm-01 重算契约 sha256，与锁文件、architect 交付报告三方比对。
- 人工核对 §八声明（lint 查不到）：缺声明不登记；权限与审计声明任何变化（含放宽）须有总架构师结论。
- 门禁 **G-REGISTER**：`task_tracker/contract_register.py --write` 退出码 0；sha256 三方一致、version 递增，落 contracts 表即冻结生效。
- 硬规则：**登记完成前，下游任务一律不得批准开工**。

### S4 并行实现 → 调用 pm-01（派发）+ 前端/后端/桌面程序员实例

- pm-01 对每张任务卡执行：
  - 门禁 **G-DISPATCH**：`task_tracker/check_dispatch.py` 退出码 0（上游全 ACCEPTED、契约已冻结且 sha256 未漂移）。
  - 门禁 **G-SIDE-EFFECT（snapshot）**：`artifact_inspector/scan_side_effects.py snapshot` 留依赖基线。
  - 通过后 `transition.py IN_PROGRESS`，把任务卡内容（含冻结契约路径+version+sha256）路由给对应实例：Java 卡 → java-dev-01、Python 后端卡 → py-backend-dev-01（后端程序员），前端卡 → react-dev-01（前端程序员），桌面卡 → tauri-dev-01（桌面程序员）。
- 成员实例按各自挂载技能实现，自跑门禁留真实日志（**G-SEC-GATE**：check_secrets.sh / check_security.sh；**G-DBOPS**：产出 .sql 或改数据源配置时 check_db_ops.sh + 变更单；单测），完成后向 pm-01 交付报告。
- 多张互不依赖的任务卡并行推进。
- 失败分支：契约缺字段或缺安全声明 → 回报 pm-01 转 architect-01 补契约后回到 S3 重新登记。

### S5 物理验收与记账 → 调用 pm-01

- 五步验证（缺证据即打回）：
  1. **G-OUTPUTS**：`check_outputs.py` — outputs 存在、非空、非占位、不逃逸 root_dir。
  2. **G-TESTLOG**：`check_testlog.py` — 通过率 100%、退出码留存。
  3. **G-EXCERPT**：`check_excerpt.py` — 报告摘录能在日志原文找到。
  4. **G-SIDE-EFFECT（compare）**：`scan_side_effects.py compare` — 无未声明的依赖或配置改动。
  5. 安全门禁复核：G-SEC-GATE 重跑核对 [INFO] 取证段；数据门禁 G-DBOPS 按批次抽卡重跑，「报告绿、重跑红」整批打回。
- 全部通过：`transition.py ACCEPTED`（凭证路径与摘要）。
- 任一未达标：`transition.py REJECTED --reason 判据 --evidence 证据`，该任务卡回到 S4 对应成员返工；重提测全量重验。
- **循环上限**：同一原因打回 2 次封顶，第 3 次触发 ⏸ **H-ESCALATE** 报警等待用户决策，成员不得继续返工。
- ⏸ **H-EXEMPT**：门禁豁免理由、覆盖率门槛调整、留存期偏离，由用户批准。

### S6 集成与安全验证 → 调用 qa-01，pm-01 核验

- 前置：被测范围内开发任务全部 ACCEPTED，契约 sha256 与登记值一致；qa-01 派发同样过 G-DISPATCH。
- qa-01：从契约推导用例（按《QA 用例与证据细则》覆盖矩阵），执行并落 `qa/logs/` 与 `qa/reports/`；提测前自检 G-OUTPUTS / G-TESTLOG。
- pm-01 核验：G-TESTLOG / G-EXCERPT；人工核验 **G-QA-COVERAGE**（错误码逐 code 覆盖 100%，每条 FAIL 有期望-实测差异）与 **G-QA-SECURITY**（越权、鉴权绕过、脱敏、审计覆盖四族逐条有执行记录与落盘原文摘录）。
- 失败分支：QA 结论 FAIL → 按判据打回对应开发任务，回到 S4 / S5。

### S7 上线与数据变更 → 调用 pm-01 + 用户

- pm-01 核对数据变更单：执行窗口、锁影响、回滚方案、备份产物与恢复命令。
- 门禁 **G-DBOPS**（终检）：含 .sql 或数据源配置变更时 `check_db_ops.sh` 退出码 0 + 变更单填全。
- ⏸ **人工闸门 H-RELEASE**：用户批准不可逆数据变更、上线窗口与回滚点。
- 上线后留存 QA 复现说明与版本三件套（PRD / Tech Spec / 契约版本）。

### S8 复盘与漂移检查 → 调用 pm-01

- 写 `{evidence_dir}` 迭代记录：本轮返工原因、门禁命中、契约变更次数。
- 漂移自查：脚本已改而权威文档未改，或反之；新暴露问题建议补进基线、判据或门禁脚本。

### 汇报节奏

- 每完成一个阶段，pm-01 向用户输出三段式：**[已验收交付物]**（任务编号 + 物理产物路径）/ **[阻塞与待确认项]** / **[风险与决策请求]**（事实与推断分开，给 2 个明确选项与代价，推荐项在前）。
- 每个人工闸门暂停时，明确列出待拍板问题与选项。
