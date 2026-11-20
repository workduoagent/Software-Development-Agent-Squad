---
name: task_tracker
description: PM 的任务账本工具集：tasks.json 结构校验、看板汇总、派发前置检查、状态机流转记账与契约冻结登记。PM 每次查账、派发、验收落笔前必须调用对应脚本，杜绝手工改账的状态机违规。
---

# 任务账本工具集（task_tracker）

## Overview

软件团队知识库 任务状态机.md 与任务字段标准.json 的机器执行端：把 PM 的"查账→记账"从手工编辑 `tasks.json` 变成确定性脚本，保证单写者落盘原子、状态流转只走合法边、打回必带证据、派发必经前置检查。

> 边界：本工具集只管理账本与登记，不做物理验收。`outputs` 存在性、日志真实性、副作用扫描由 `artifact_inspector/` 负责；两串凭证齐备才可 ACCEPTED。

## 依赖

Python ≥ 3.10，首次使用前安装：

```bash
python -m pip install -r requirements.txt
```

`--ledger` 的默认值 `tasks.json` 与 `--schema` 的默认值 `软件团队知识库 任务字段标准.json` 都是**相对当前工作目录**的字面量（见 validate.py:160-161、board.py:39 等）。跨目录执行一律显式传 `--ledger "{root_dir}/tasks.json"`，禁止依赖默认值——默认值会命中当前目录下同名账本，而不是权威账本。

## 五个工具（下列命令在本 skill 目录内执行；脚本路径相对 skill 目录）

| 工具 | 用途 | 调用方与时机 | 退出码 |
| --- | --- | --- | --- |
| `validate.py [tasks.json] [--report r.json]` | schema 校验 + 账本不变量（前缀唯一、round 递增、accepted_at 一致性等） | PM 每次改账后与发现账本可疑时 | 0 通过 / 1 有 ERROR |
| `board.py [--project ID] [--json]` | 状态分布、就绪队列、阻塞与打回红线预警 | PM 每轮汇报前 | 0 / 2 定位失败 |
| `check_dispatch.py <TASK-ID> [--report r.json]` | 派发前置：TODO 状态、上游全 ACCEPTED、契约已冻结且 sha256 无漂移 | PM 置 `TODO → IN_PROGRESS` 前必跑 | 0 可派发 / 1 拒绝 |
| `transition.py <TASK-ID> <TO_STATUS> [--reason --evidence.. --log]` | 按合法边流转并原子写账；REJECTED 强制证据落账 | PM 记账的唯一入口，禁止手改 status | 0 成功 / 1 拒绝流转 / 3 报警红线 |
| `contract_register.py --project ID --lock <.lock.json> [--write]` | 核验 freeze 锁文件与契约物理文件三方一致（锁/文件/登记块）后落 `contracts` 表 | architect 交付契约凭证后，PM 登记冻结时 | 0 通过 / 1 拒绝登记 |

**账本结构示例**：`assets/tasks.example.json` 是一份完整的 Few-Shot 账本（含契约登记、五种任务状态、打回记录），新建账本或核对字段形态时参照；它是示例，不是运行时账本，运行时账本始终是仓库根 `tasks.json`。

```bash
python validate.py                                     # 改账后全量校验
python board.py --project proj-auth-service
python check_dispatch.py AUTH-003 --report reports/AUTH-003-dispatch.json
python transition.py AUTH-002 IN_REVIEW --log "提测报告与日志路径已登记"
python transition.py AUTH-004 REJECTED --reason "单元测试通过率不足 100%" \
    --evidence "qa/logs/auth-004-pytest-run.log: 2 failed, 17 passed"
python contract_register.py --project proj-auth-service \
    --lock workspace/services/auth-service/contracts/auth-api-v1.yaml.lock.json --write
```

## 检查码

| 码 | 级别 | 含义 |
| --- | --- | --- |
| P001-P010 | ERROR/WARN | `validate.py`：账本顶层、项目结构、id 唯一、前缀冲突、accepted_at 一致性、round 递增、契约登记条目、schema 违规 |
| P101-P107 | ERROR | `check_dispatch.py`：非 TODO 派发、inputs 缺失、路径逃逸、契约未冻结、契约漂移、上游未 ACCEPTED |
| P201-P205 | ERROR | `contract_register.py`：锁文件缺损、lint 未过、契约物理缺失、指纹不一致、版本未递增 |
| P301-P305 | ERROR/WARN/ALARM | `transition.py`：非法流转、打回缺证据、同原因 ≥2 预警 / ≥3 报警红线、落账摘要缺失 |

## 与协议的衔接

- 流转边与软件团队知识库 任务状态机.md 一一对应；`BLOCKED → 原状态`由 PM 按挂起前实际状态显式指定目标（TODO 或 IN_PROGRESS）。
- 报警红线：同一 `reason` 第 2 次打回出 WARN（第三轮返工前先对齐判据），第 3 次起落账后仍以退出码 3 强制 PM 中断上报，与软件团队知识库 任务状态机.md 物理验收判据.md 一致。
- 契约冻结生效点不变：`contract_register.py --write` 落账即 tools.md 所述"PM 登记"动作本身；安全与审计声明（`软件团队知识库 接口契约标准.md` §八）仍是登记前 PM 的人工对账义务，本工具不代判。
- `validate.py` 用 jsonschema 直接执行 `软件团队知识库 任务字段标准.json`，协议改字段标准后无需改工具。

## 测试

`tests/fixtures/clean|dirty/` 自带合法账本、违规账本与最小项目工作区（含契约与锁文件），回归方式与实测结果见 `tests/run_tests.md`。
