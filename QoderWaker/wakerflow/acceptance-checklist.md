# WakerFlow 生成后对账清单

用 `main-flow-prompt.md` 生成流程后逐项核对，一个都不能少；有缺失就带着对应条目重新生成或手工补节点。

## 阶段（9）

- [ ] S0 需求受理与定界（pm-01）
- [ ] S1 任务拆解与建账（pm-01，G-LEDGER）
- [ ] S2 设计与契约产出（architect-01，G-LINT / G-DIFF / G-FREEZE + mock_gen）
- [ ] S3 登记冻结（pm-01，G-REGISTER，唯一生效点；「登记完成前下游不得开工」硬规则在）
- [ ] S4 并行实现（pm-01 派发 + 前端/后端/桌面程序员实例，G-DISPATCH / G-SIDE-EFFECT snapshot）
- [ ] S5 物理验收与记账（pm-01，G-OUTPUTS / G-TESTLOG / G-EXCERPT / G-SIDE-EFFECT compare）
- [ ] S6 集成与安全验证（qa-01 执行 + pm-01 核验）
- [ ] S7 上线与数据变更（H-RELEASE + G-DBOPS）
- [ ] S8 复盘与漂移检查（pm-01）

## 人工闸门（7）

- [ ] H-SCOPE（S0）需求歧义答复、范围与不做清单、PRD 版本确认
- [ ] H-TECH（S0/S2）技术选型、拓扑、数据库与中间件
- [ ] H-PARAM（S2）基线第九节参数：口令策略、锁定阈值、Token 有效期、审计留存
- [ ] H-BREAKING（S2/S3）破坏性变更与权限/审计声明的任何变化
- [ ] H-EXEMPT（S4/S5）门禁豁免理由、覆盖率门槛调整、留存期偏离
- [ ] H-ESCALATE（S5）同因第 3 次打回报警
- [ ] H-RELEASE（S7）不可逆数据变更批准、上线窗口与回滚点确认

## 机检门禁（12）

- [ ] G-LEDGER `task_tracker/validate.py`
- [ ] G-DISPATCH `task_tracker/check_dispatch.py`
- [ ] G-LINT `contract_validator/lint.py`
- [ ] G-DIFF `contract_validator/diff.py`（退出码 2 = BREAKING_CHANGE 分支在）
- [ ] G-FREEZE `contract_validator/freeze.py`
- [ ] G-REGISTER `task_tracker/contract_register.py --write`
- [ ] G-OUTPUTS `artifact_inspector/check_outputs.py`
- [ ] G-TESTLOG `artifact_inspector/check_testlog.py`
- [ ] G-EXCERPT `artifact_inspector/check_excerpt.py`
- [ ] G-SIDE-EFFECT `artifact_inspector/scan_side_effects.py`（snapshot + compare 两步都在）
- [ ] G-SEC-GATE `check_secrets.sh` / `check_security.sh`（成员步骤内执行，pm-01 重跑复核）
- [ ] G-DBOPS `check_db_ops.sh`（含变更单要求 + 批次抽查规则）

## 人工对账门禁（6，无脚本，不得写成机检）

- [ ] G-SEC-DECL（§八 声明逐 operation 核对）
- [ ] G-QA-COVERAGE（错误码逐 code 覆盖 100%）
- [ ] G-QA-SECURITY（四族安全用例执行记录与原文摘录）
- [ ] G-PRD-DOD（PRD §十二 十条 + §三.2 无待答）
- [ ] G-SPEC-INTAKE（architect 接收前输入充分性）
- [ ] G-SPEC-PENDING（Tech Spec §七 逐项拍板依据）

## 融合约束（状态流归 PM）

- [ ] 流程自身不执行任何账本命令；账本命令只出现在 pm-01 步骤内
- [ ] 成员 Waker 只接收任务卡内容，不接收账本
- [ ] ACCEPTED / REJECTED 只由 pm-01 宣布
- [ ] S5 打回回到 S4 对应成员，重提测全量重验；同因 2 次封顶 → H-ESCALATE
- [ ] 三段式汇报出现在每阶段完成与 H-ESCALATE 时
- [ ] S2 门禁依序不跳步；S3 硬规则「未登记不派下游」在

## 需实测项（生成流程后立即验证）

- [ ] 人工闸门的暂停/审批形态：原生审批节点 or 流程暂停等用户回复
- [ ] WakerFlow 步骤间传文件路径还是传内容（决定任务卡怎么传给成员实例）
- [ ] pm-01 能否直接呼叫成员 Waker；不能则启用按任务卡技术栈条件路由的兜底
- [ ] 多张互不依赖任务卡能否并行推进（S4 并行语义）
- [ ] S5 打回循环能否真实回到 S4 对应实例并重新计数
- [ ] 成员实例散活可用：绕过流程直接对话可评估 / 写脚本 / 联调，全程不碰账本
