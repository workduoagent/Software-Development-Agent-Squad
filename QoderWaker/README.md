# QoderWaker 装配包

把本仓库的多智能体开发小分队部署为 QoderWake 数字员工团队的装配底稿。

## 模型

```
角色模板（roles/，岗位） → Waker 实例（wakers/instances.md，具体的人） → WakerFlow（wakerflow/，控制流调度）
```

融合原则一句话：**控制流归 WakerFlow，状态流归 PM**。WakerFlow 只决定「何时调用谁、在哪暂停等人、打回回到谁」；账本 `tasks.json` 只经 pm-01 的 task_tracker 脚本写入，ACCEPTED / REJECTED 只由 pm-01 宣布。

每个 Waker 同时支持**两种使用模式**（各角色 bible 有「独立使用（散活）模式」节）：

- **流水线模式**：经 WakerFlow / 任务卡派发，执行门禁与账本纪律（成员不碰账本）。
- **散活模式**：用户直接对话处理非项目事务——PM 拆需求 / 规划排期 / 评估；成员可行性评估与实现方案；脚本工具；前后端联调。不碰账本、产物按用户指定位置交付、安全红线不放宽；散活产出升级为正式项目时走 PM 立项进 S0。

## 目录

```
QoderWaker/
├── roles/                  7 个角色模板 × identity / persona / bible 三件套
│   ├── pm/                 项目经理（对应 agents/pm/prompt.md + orchestration/workflow.yaml）
│   ├── architect/          系统架构师（对应 agents/architect/prompt.md）
│   ├── frontend/           前端程序员（React 18+ 现役，Vue 2/3 待技能；对应 agents/developers/frontend-react/prompt.md）
│   ├── backend/            后端程序员（Java 与 Python 现役，Rust 待技能；对应 backend-java / backend-python/prompt.md）
│   ├── desktop/            桌面程序员（Tauri 2；对应 desktop-tauri/prompt.md；「其他类型开发」家族首个成员）
│   ├── scripting/          脚本程序员（Python 现役；对应 script-python/prompt.md；「其他类型开发」家族第二个成员）
│   └── qa/                 质检工程师（对应 agents/qa/prompt.md）
├── wakers/instances.md     实例划分表：模板卡片文案、实例划分、装配步骤与核验
├── wakers/device-env.template.md  设备环境档案模板（复制到仓库根填 device-env.md，已进 .gitignore）
├── knowledge-base/         知识库上传底稿：总索引 + 10 份文档（8 份原样 + 2 份 json→md 检索包装）
├── wakerflow/              main-flow-prompt.md（新建 WakerFlow 的自然语言底稿）+ acceptance-checklist.md（生成后对账）
└── skills/README.md        技能上传来源、绑定方式与纪律
```

## 真源关系

- **Qoder IDE 插件形态**真源不变：`agents/**/prompt.md` + `agents/**/skills/` + `软件团队知识库/`。
- **QoderWake 形态**真源：本目录。三件套（identity/persona/bible）由对应 prompt.md 拆解适配而来，persona 为净新增；每个文件头部注明真源出处。
- 纪律改动规则：先改对应形态的真源，再同步另一形态；后续可加一致性检查脚本。
- 知识库文档真源仍是仓库 `软件团队知识库/`；`knowledge-base/` 只做检索适配，不做内容改写。

## 装配顺序（pilot）

1. **architect 试点**（依赖最少的可产出角色）：建角色模板（上传 `roles/architect/` 三件套）→ 挂 contract_validator、database-ops → 建 architect-01 实例（运行环境：本机）→ 绑知识库。实测四件事：技能上传包格式、知识库检索命中、门禁脚本本机可跑、三件套长度是否超限。
2. **PM 账本链**：建 pm 模板与 pm-01 单例 → 跑 S0→S1，验证 `{ledger}` 绝对路径解析与知识库模版引用。
3. **最小 WakerFlow 闭环**：把 `wakerflow/main-flow-prompt.md` 粘进「新建 WakerFlow」，先只验 S0→S1→S2→S3（含 H-SCOPE / H-PARAM 两个人工闸门）；按 `acceptance-checklist.md` 对账。
4. **全量**：补前端 / 后端（Java + Python）/ 桌面 / 脚本程序员与 qa-01 实例 → 完整 S0-S8 流程 → S5 打回循环单独测。

## 运行层依赖（本机一次性准备）

- 仓库克隆到本机固定路径（即 `{squad_root}`），`tasks.json` 在仓库根；技能脚本与知识库物理文件都从这里寻址。
- 设备环境档案：把 `wakers/device-env.template.md` 复制到仓库根改名 `device-env.md` 按实况填写（JDK/Maven/Node/Conda 路径、数据源、联调地址；口令只记环境变量名，文件已进 `.gitignore`）。
- Python 依赖：`task_tracker` / `artifact_inspector` / `contract_validator` / `python-backend-scaffold` 的 requirements.txt。
- bash 可用（`check_secrets.sh` / `check_security.sh` / `check_db_ops.sh`）。
- 界面已提示「切换设备后凭证、Token 和本地依赖需重新配置」——全套绑定在一台常开设备上。

## 已知边界（实测前不要假设）

- 人工闸门是否原生支持审批节点未知；不支持则以「流程暂停、等用户回复」形态实现。
- pm-01 能否直接呼叫成员 Waker 未验证；兜底方案是 WakerFlow 按任务卡技术栈字段条件路由。
- WakerFlow 步骤间传文件路径还是传内容未验证；影响任务卡传递方式。
- 知识库单文档长度上限未知；三件套按最小必要写，bible 不复制技能内容（细节指回技能）。
