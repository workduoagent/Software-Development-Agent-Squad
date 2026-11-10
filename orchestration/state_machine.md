# 任务流转状态机（State Machine）

全团队（PM / Architect / developers 各技术栈开发 / QA 智能体，与担任总架构师的用户）统一遵循的权威定义。PM 侧的账本操作细则见 `agents/pm/tools.md`，任务字段标准见 `docs/02-protocols/task-schema.json`。

## 状态枚举

| 状态 | 含义 |
| --- | --- |
| `TODO` | 已拆解，未派发/未开工 |
| `IN_PROGRESS` | 已派发，成员执行中 |
| `IN_REVIEW` | 成员汇报完成，PM 验收中 |
| `ACCEPTED` | 物理验收通过（终态） |
| `REJECTED` | 验收未通过，附原因与证据打回 |
| `BLOCKED` | 等待用户澄清或外部输入，挂起 |

## 流转定义

```
TODO → IN_PROGRESS → IN_REVIEW → ACCEPTED
IN_REVIEW → REJECTED（验收失败，附原因与打回证据）
REJECTED → IN_PROGRESS（原作者返工）
TODO / IN_PROGRESS → BLOCKED（等待用户澄清或外部输入），阻塞解除后恢复挂起前状态
```

| 流转 | 触发与责任 |
| --- | --- |
| `TODO → IN_PROGRESS` | PM 完成派发前置检查后派发，成员开工 |
| `IN_PROGRESS → IN_REVIEW` | 成员汇报完成，PM 置位并启动物理验收 |
| `IN_REVIEW → ACCEPTED` | PM 物理验收全部通过 |
| `IN_REVIEW → REJECTED` | 任一验收项未达标，附具体证据打回 |
| `REJECTED → IN_PROGRESS` | 原作者认领返工 |
| `→ BLOCKED → 原状态` | 等待用户决策/外部输入时挂起，解除后恢复 |

**派发前置检查**：任务 `inputs` 依赖的上游任务必须全部 `ACCEPTED`，契约类输入必须已在项目 `contracts` 登记表冻结，否则禁止派发。

## 单写者原则

`tasks.json` 仅由 PM 统一写入。成员只汇报进度与产出，严禁自行修改账本；所有状态流转由 PM 对账后落笔。

## 打回记录与报警红线

每次打回必须在任务的 `rejection_history` 中追加一条记录：

```json
{
  "round": 1,
  "rejected_at": "2026-11-09T21:00:00Z",
  "reason": "单元测试通过率不足 100%",
  "evidence": ["tests/test_auth.py::test_login 失败日志的物理路径或摘录"]
}
```

同一问题同一原因打回超过 2 次（按 `reason` 计数），PM 立即中断执行并向用户报警求助。