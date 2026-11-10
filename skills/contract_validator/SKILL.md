---
name: contract_validator
description: OpenAPI 3.1 契约的机器校验、冻结锁定、兼容性 Diff 与 Mock 报文生成。architect 交付契约前必须调用（Lint + 指纹），PM 核验凭证后登记冻结；契约变更时执行 Diff 分级（BREAKING_CHANGE 须总架构师拍板）。
---

# 契约校验工具集（contract_validator）

## Overview

`docs/02-protocols/api-contract-spec.md` 的机器执行端：把契约标准（E001~E009/E100 + W001~W003 检查项、变更分级表）落为确定性脚本，杜绝"人眼过契约"。

> 边界：契约标准第八节的安全与审计声明（`security` / `x-roles` / `x-permissions` / `x-sensitive` / `x-audit`）**不在本工具集的校验范围内**，
> 由 architect 自检与 PM 登记前人工对账；是否补成 lint 项属基线变更，需总架构师拍板。

## 依赖

Python ≥ 3.10，首次使用前安装：

```bash
python -m pip install -r skills/contract_validator/requirements.txt
```

## 四个工具（均在 `skills/contract_validator/` 下执行）

| 工具 | 用途 | 调用方与时机 | 退出码 |
| --- | --- | --- | --- |
| `lint.py <contract> [--report r.json]` | 按契约标准逐项校验 | architect 交付前必跑 | 0 通过 / 1 有 ERROR |
| `freeze.py <contract> [--report r.json]` | 内部先跑 lint，通过后计算 sha256、写 `<contract>.lock.json` 锁文件，并打印 PM 登记块 | architect 校验通过后 | 0 冻结 / 1 拒绝 |
| `diff.py <old> <new> [--report r.json]` | 变更分级审计 | 契约变更任务，与上一冻结版比对 | 0 无变更/纯增量 / 2 BREAKING_CHANGE |
| `mock_gen.py <contract> [--out m.json] [--operation-id id]` | 从样例/Schema 生成 Mock 报文集 | architect 交付附件；前端 mock 初始化参考 | 0 成功 / 1 失败 |

```bash
python lint.py   workspace/contracts/auth-api-v1.yaml --report reports/auth-v1-lint.json
python freeze.py workspace/contracts/auth-api-v1.yaml
python diff.py   workspace/contracts/auth-api-v1.yaml workspace/contracts/auth-api-v2.yaml
python mock_gen.py workspace/contracts/auth-api-v1.yaml --out mocks/auth-api-v1.mocks.json
```

## 输出约定（LLM 友好）

- 所有工具在 stdout 打印逐条 `[检查项] 级别 @ 位置: 说明` 与一行终判（`LINT PASSED/FAILED`、`FREEZE OK/REFUSED`、`DIFF VERDICT`、`MOCK GEN OK`）。
- `--report` 输出结构化 JSON，作为交付报告中的物理凭证路径。
- WARN 不阻断冻结，但 architect 必须在交付报告中逐条说明。

## 与协议的衔接

- 冻结生效点：freeze.py 只产锁文件与登记块，**契约冻结以 PM 在 `tasks.json` 项目 `contracts` 表登记为准**（见 `agents/pm/tools.md`）。
- freeze.py 打印的登记块（path/version/sha256/frozen_at）与 `contracts` 表字段一一对应，PM 核验 sha256 与锁文件一致后直接落账。
- diff 退出码 2 时，architect 必须携带 BREAKING_CHANGE 清单上报总架构师，决策结论写入交付报告后方可重新 freeze。

## 测试

`tests/fixtures/` 自带四份样例契约（v1 合法、v2 纯增量、v2 破坏性、invalid 多违规），回归方式见 `tests/run_tests.md`。
