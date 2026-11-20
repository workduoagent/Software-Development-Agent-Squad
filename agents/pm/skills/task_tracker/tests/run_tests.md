# task_tracker 回归表（实测记录）

实测环境：Windows 10.0.26300 / Python 3.12.10 / jsonschema 4.26.0，2026-11-10 于仓库根目录运行。
所有 scratch 场景由 `cp -r tests/fixtures/clean tests/.scratch/<case>` 复制后进行，夹具本体未被改动。
表内"实测"为当轮真实退出码与关键判据行，非预期值。

## 用例

| # | 命令（在本 skill 目录内执行，省略 `python ` 前缀） | 判据 | 实测 |
| --- | --- | --- | --- |
| A1 | `validate.py tasks.json` | 空账本 PASSED | exit=0 `LEDGER PASSED (0 errors, 0 warnings)` |
| A2 | `validate.py tests/fixtures/clean/tasks.json` | 夹具合法 PASSED | exit=0 `LEDGER PASSED (0 errors, 0 warnings)` |
| A3 | `validate.py tests/fixtures/dirty/tasks.json` | 命中 P002/P004/P005/P006/P007/P008/P009/P010 | exit=1，17 errors / 4 warnings：缺 sha256、version 'v1'、4 条 required 缺失、complexity L、bad-id-1 pattern、task_id 重复、IN_PROGRESS 带 accepted_at、round [2,1]、project_id 重复、root_dir 冲突、跨项目前缀冲突 |
| B1 | `check_dispatch.py AUTH-003 --ledger <clean>/tasks.json` | 契约已冻结可派发 | exit=0 `DISPATCH OK` |
| B2 | `check_dispatch.py AUTH-005` | 上游 AUTH-004 REJECTED | exit=1，2 项 P106 |
| B3 | `check_dispatch.py ADM-001` | contracts/ui-kit-v1.yaml 未登记 | exit=1，P104 |
| B4 | `check_dispatch.py AUTH-002` | 非 TODO | exit=1，P101 |
| B5 | 复制后向契约 yaml 追加一行再 `check_dispatch.py AUTH-003` | 指纹漂移 | exit=1，P105（登记 64ccde… 实际 4190f5…） |
| B6 | 账本注入 `../escape.yaml` inputs 与 `../out.java` outputs 后 `check_dispatch.py AUTH-006` | 路径逃逸 | exit=1，inputs/outputs 各命中 P103 |
| C1 | `transition.py AUTH-002 IN_REVIEW --ledger <trans> --log ...` | 合法边落账 | exit=0，verification_log 带时间戳写入 |
| C2 | `transition.py AUTH-003 ACCEPTED` | TODO→ACCEPTED 非法，不写账 | exit=1 P301，账本中 AUTH-003 仍 TODO |
| C3 | `transition.py AUTH-004 IN_PROGRESS` | 返工认领 | exit=0 |
| C4a | `transition.py AUTH-004 REJECTED --reason R --evidence E`（IN_PROGRESS 态） | IN_PROGRESS→REJECTED 非法边 | exit=1 P301（打回只发生在 IN_REVIEW，与设计一致） |
| C4b | `transition.py AUTH-004 REJECTED`（IN_REVIEW 态，缺证据） | 证据强制 | exit=1 P302 |
| C5 | 同原因第 2 次打回 | 预警 | exit=0，P303 WARN "返工第三轮前先与用户对齐判据" |
| C6 | 返工后第 3 次同原因打回 | 报警红线 | exit=3，P303 ALARM，落账 rounds=[1,2,3] |
| C7/C8 | `transition.py AUTH-003 BLOCKED` → `transition.py AUTH-003 TODO --log ...` | 挂起与恢复 | exit=0（C7 无 --log 出 P305 WARN） |
| C11/C12 | `transition.py AUTH-002 ACCEPTED --log ...` → 再尝试 `IN_PROGRESS` | ACCEPTED 写 accepted_at；终态不可逆 | exit=0 / exit=1 P301，validate PASSED |
| C14 | `board.py --ledger <trans> --project proj-auth-service` | 红线预警 | 输出 `红线预警 AUTH-004: 同一原因打回 3 次` |
| D1 | `contract_register.py --project proj-auth-service --lock <v1.lock> --ledger tasks-noreg.json`（无 --write） | 建议模式 | exit=0 `REGISTER VERIFIED`，打印登记块 |
| D2 | 同上 `--write` | 落账 | exit=0 `REGISTER OK @1.0.0`；随后 B1 场景 `DISPATCH OK` |
| D3 | 同版本再次 `--write` | 版本未递增 | exit=1 P205 |
| D4 | 用 `auth-api-v1.badlint.lock.json` 登记 | lint 未过禁冻结 | exit=1 P202 |
| D5 | 篡改契约后登记 | 锁/文件指纹不一致 | exit=1 P204（锁 64ccde… 实际 f5afec…） |
| D6 | 锁升 2.0.0 并重算 sha 后 `--write` | 同 path 覆盖旧条目 | exit=0，contracts 表仅 1 条且 version=2.0.0 |
| D7 | v2 登记后再篡改契约 `check_dispatch.py` | 漂移复验 | exit=1 P105 |
| J1-J6 | 与 artifact_inspector 联动：`check_outputs.py --task AUTH-002 --report ..` + `check_testlog.py --report ..` 双绿后 `transition.py AUTH-002 ACCEPTED --log 凭证路径` | 验物到记账闭环 | exit=0 链路全绿，终账 validate PASSED |

## 已知盲区（脚本查不出的绕过类别，验收时仍需人工）

1. 账本外的口头状态约定：工具只认 `tasks.json` 落笔，成员私改账本由单写者纪律与 git diff 兜底，本工具不做写入方审计。
2. inputs 上游推断依赖"路径出现在某任务 outputs"这一事实；若上游任务卡漏声明产出文件，P106 会漏报，需 PM 对照 Tech Spec 抽查。
3. 契约漂移检测以登记 sha 为锚；登记块本身被手工改写（同机器伪造 tasks.json 里的 sha256）超出静态工具能力，靠 freeze 锁文件与 `contract_register.py` 三方对账压缩窗口。
4. `board.py` 的就绪队列是粗筛（只核契约登记），不可直接作为派发依据，仍须逐卡 `check_dispatch.py`。
5. 时钟来源为本机 UTC，账本时间戳不做权威时间审计。
