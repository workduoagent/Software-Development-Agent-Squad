# QoderWaker 装配手册（RUNBOOK）

**唯一权威装配文档**：装机与更新的顺序、验证、纪律都在这里；其他文档只描述结构，不重复装配步骤。
配合 `scripts/package_waker.py` 使用：脚本产出 `dist/qoderwaker-upload/`（上传工作台目录 + `00-OPERATION.md` 本次操作单），本手册定义操作顺序与验收标准。

## 标准迭代流程（长期更新只走这一条）

1. **改仓库真源**：roles 三件套 / 技能（`agents/**/skills/` 后重跑 sync_skills）/ 知识库（`软件团队知识库/` + 检索包装）/ instances.md 文案 / WakerFlow 底稿。
2. **跑打包**：`python scripts/package_waker.py`。
3. **看增量**：打开 `dist/qoderwaker-upload/00-OPERATION.md` 顶部「增量重传清单」——真源无变化则为空，有变化则逐文件列出。
4. **照单重传**：只重传清单里列出的文件到平台对应位置（技能 / 知识库 / 模板三件套 / WakerFlow 粘贴），其余不动。
5. **重验**：按改动面选对应核验条目（见阶段 5）。

纪律：

- **平台侧不就地编辑**——所有变更从真源走一遍流程；平台上的文件视为生成产物。
- **保留 `dist/qoderwaker-upload/` 目录**（含隐藏 `.state.json`）以维持增量比对；删掉 dist 等于重置基线（下次全量）。
- 真源有字段级文案改动时改 `wakers/instances.md`（表单文案的真源），不要只改平台。

## 阶段 0：本机准备（一次性）

- [ ] 0.1 仓库克隆到固定路径（即 `{squad_root}`；换设备 = 换环境，全部本地依赖要重配）。
- [ ] 0.2 Python 依赖：`task_tracker` / `artifact_inspector` / `contract_validator` / `python-backend-scaffold` 的 requirements.txt 装好（建议 conda env 隔离）。
- [ ] 0.3 bash 可用（`check_secrets.sh` / `check_security.sh` / `check_db_ops.sh` 依赖）。
- [ ] 0.4 把 `wakers/device-env.template.md` 复制到仓库根改名 `device-env.md` 按实况填写（含 squad_root 绝对路径；口令只记环境变量名；已进 `.gitignore`）。

## 阶段 1：平台资源（技能 → 知识库，先于一切模板）

- [ ] 1.1 跑 `python scripts/package_waker.py`（每个技能自动生成目录 + 同名 `.zip`）。
- [ ] 1.2 **技能上传（平台仅支持 ZIP，2026-11-21 实测确认）**：逐个上传 `01-skills/<skill>.zip`（9 个）。上传后在平台上抽查 SKILL.md 描述与 `scripts/` 子目录是否完整；若平台报找不到 SKILL.md，改用 `python scripts/package_waker.py --flat-zip` 重打包再传（zip 内布局：顶层文件夹为默认，扁平为备用——这也是实测项）。
- [ ] 1.3 **知识库上传**：`02-knowledge-base/` 全部文件，命名「软件团队知识库」。上传后抽查：能检索《任务状态机》《接口契约标准》条目。

## 阶段 2：角色模板（7 个，试点纪律）

按 `00-OPERATION.md` 第三节表逐个创建：表单「角色名称」「它主要负责什么」照抄 + 上传三件套 + 挂模板级技能（pm / architect / qa 挂；程序员四类模板不挂，栈技能在实例挂）。

- [ ] 2.1 **先建 architect-01 模板**并用阶段 5 核验条目验证（技能可跑、知识库命中、三件套长度未超限）。
- [ ] 2.2 验证通过后批量建其余 6 个模板。

## 阶段 3：Waker 实例

按 `00-OPERATION.md` 第四节表创建；每个实例：名称 / 「我负责什么」照抄 / 运行环境**本机** / 技能按表 / **绑定知识库**。

- [ ] 3.1 建实例并核对：pm-01 严格单例（永建第二个 PM）；py-script-dev-01 散活为主；数量 0 的未来实例不建。
- [ ] 3.2 设备环境收尾：确认 `device-env.md` 已在仓库根；pm-01 首次对话告知仓库根绝对路径。

## 阶段 4：WakerFlow

- [ ] 4.1 新建 WakerFlow → 粘贴 `04-wakerflow/main-flow-prompt.md` 全文。
- [ ] 4.2 按 `wakerflow/acceptance-checklist.md` 对账：9 阶段 / 7 人工闸门 / 12 机检 + 6 人工对账门禁 / 融合约束，缺项重新生成或手工补节点。

## 阶段 5：核验与实测记录

按 `wakers/instances.md`「装机后核验」逐条过（点名 / 改派 / 散活 / 评估 / PM 单例 / 成员不知账本 / 知识库命中 / 环境档案）。实测结果填入下表（这是仓库的装机事实记录，随迭代维护）：

| 实测项 | 结果 | 备注 |
| --- | --- | --- |
| 技能上传形态 | **仅支持 ZIP**（2026-11-21 实测） | zip 内布局待验证：默认顶层文件夹，报缺 SKILL.md 则 `--flat-zip` 扁平重打 |
| 知识库对 JSON/长度上限 | 待填 | 本方案已按纯 md 适配 |
| 人工闸门形态（审批节点 or 暂停等回复） | 待填 | |
| pm-01 能否直接呼叫成员 | 待填 | 不行则用技术栈条件路由兜底 |
| WakerFlow 步骤传路径 or 内容 | 待填 | |
| 散活模式可用性 | 待填 | |

## 常见故障与处置

- **打包报「副本不一致」**：同名技能真源被改得不一致——回 `agents/**/skills/` 修齐再跑。
- **平台上传被拒 / 内容截断**：先查文件是否被平台格式化（代码块、表格），再查长度上限；超限则对 bible 做减法（细节本就指回技能，bible 不该长）。
- **技能 zip 传后报缺 SKILL.md**：平台期望扁平 zip（SKILL.md 在压缩包根）——`python scripts/package_waker.py --flat-zip` 重打包重传。
- **增量清单里出现意外文件**：检查是否误改了生成物（01/02/03 目录内容都来自真源，手工改了 dist 会被当作真源变更）——删掉 dist 重跑可重置。
