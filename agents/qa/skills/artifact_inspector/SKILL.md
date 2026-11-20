---
name: artifact_inspector
description: PM / QA 的物理验收工具集：任务 outputs 存在性与占位识别、测试日志通过率与退出码核验、报告摘录回溯比对、依赖与配置副作用扫描。验收时把"手工看文件"变成机器判据，配合 task_tracker 完成验物到记账的闭环。
---

# 物理制品质检工具集（artifact_inspector）

## Overview

软件团队知识库 物理验收判据.md 一节通用判定规则（文件存在性、证据真实性、副作用扫描、口头无效）与 `agents/pm/prompt.md` 三节"验物"步骤的机器执行端。纯 Python 标准库，无第三方依赖。

> 边界：本工具集核验的是"凭证与磁盘事实的一致性"。日志本身是不是真实执行的产物无法从文本证明（见下"能力边界"），
> 安全机检（S/F/D 门禁）不在本包职责内，仍按 review-criteria 走对应 scaffold 脚本。

## 四个工具（下列命令在本 skill 目录内执行；脚本路径相对 skill 目录）

| 工具 | 用途 | 调用方与时机 | 退出码 |
| --- | --- | --- | --- |
| `check_outputs.py --task ID` 或 `--root dir <rel>...` | outputs 逐一核验：存在、非空、非占位、不逃逸 root_dir | PM 验物第一步 | 0 通过 / 1 命中 / 2 定位失败 |
| `check_testlog.py <log>...` | 解析 pytest/vitest/jest/surefire 汇总行，判 100% 通过并核对退出码留存 | PM 核对提测日志 / QA 自检产出 | 0 全 PASS / 1 任一 FAIL |
| `check_excerpt.py <log> --excerpt ".." [--from-report 报告.md]` | 报告摘录必须在日志原文逐字回溯命中 | PM 怀疑摘录裁剪时 | 0 全命中 / 1 有缺失 |
| `scan_side_effects.py snapshot/compare` | 公共依赖与配置清单的基线快照与改动比对，未声明改动即命中 | snapshot 在派发时，compare 在验收时 | 0 干净 / 1 有未声明改动 |

```bash
python check_outputs.py --task AUTH-002 --report reports/AUTH-002-outputs.json
python check_testlog.py workspace/services/auth-service/qa/logs/auth-004-pytest-run.log
python check_excerpt.py <log> --from-report workspace/services/auth-service/qa/reports/auth-report.md
python scan_side_effects.py snapshot workspace/services/auth-service --out baseline-auth.json
python scan_side_effects.py compare workspace/services/auth-service --baseline baseline-auth.json \
    --declared src/controllers/auth.py --declared tests/test_auth.py
```

## 检查码

| 码 | 级别 | 含义 |
| --- | --- | --- |
| A001-A004 | ERROR | `check_outputs.py`：路径逃逸 root_dir、文件不存在、空/仅空白、全文占位 TODO |
| A020-A025 | ERROR/WARN | `check_testlog.py`：汇总行不可识别、failed/errors>0、passed=0、退出码未留存、退出码非 0、存在 skipped |
| A030-A031 | ERROR/WARN | `check_excerpt.py`：摘录无法回溯、仅空白归一化后命中（排版漂移） |
| A040-A041 | ERROR/INFO | `scan_side_effects.py`：未声明的依赖/配置改动（增删改）、已声明改动待核对 CR |

## 与协议的衔接

- `check_outputs.py --task` 直接读 `tasks.json` 任务卡的 outputs 字段并按项目 `root_dir` 解析，判据即 review-criteria 一节 1"0 字节、仅占位 TODO 视为不存在"。
- `check_testlog.py` 落实一节 2"含完整执行输出结尾与退出码"：退出码格式认 `exit code: N` / `退出码: N` / maven 尾行等常见形态，取最后一次出现为终判。
- `scan_side_effects.py compare` 的 declared 清单 = 任务卡 outputs + 已获批 Change Request 文件；命中未声明改动按一节 3 直接不通过，不接受事后补声明。
- 与 `task_tracker` 的分工：本包出"验物"凭证（`--report` JSON 落盘），`transition.py ACCEPTED --log <凭证路径>` 负责把凭证登记进账本。

> 账本相关用法（`--task` / `--ledger` / `transition.py`）只属 PM。QA 等成员自检用 `check_outputs.py --root <目录> <相对路径>...`，只核自己的产物，不读账本、不碰状态流转。

## 能力边界（脚本查不出的绕过类别）

1. 日志文本可全真伪造（框架汇总行、退出码行都能手打）：本包只能核一致性，真实性的最终兜底是 PM 在 root_dir 重跑命令，重跑与报告矛盾即打回。
2. 摘录若在报告里被改写过措辞（非复制粘贴），精确与归一化匹配都会误报 MISSING，需人工比对语义。
3. xfail / flaky 重试成功 / 覆盖率阈值被调低等"没绕测试但动了标准"的形态不在日志解析范围，按 developers README 五节红线走 code review。
4. 快照之后的改动才可比对；基线被同步伪造（改了 pom.xml 又重打快照）超出静态工具能力，靠派发时刻快照留档的纪律保证。

## 测试

`tests/fixtures/` 含四框架 good/bad 日志、占位与空文件产出、依赖改动场景，回归方式与实测结果见 `tests/run_tests.md`。
