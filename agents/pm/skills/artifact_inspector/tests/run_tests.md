# artifact_inspector 回归表（实测记录）

实测环境：Windows 10.0.26300 / Python 3.12.10（纯标准库），2026-11-10 于仓库根目录运行。
夹具位于 `tests/fixtures/`（含 `ledger.json`、`workspace/demo`、九份框架日志、`report.md`、`deps/` 依赖树），目录级夹具已用 `.gitattributes` 关闭换行符转换。
表内"实测"为当轮真实退出码与关键判据行，非预期值。

## 用例

| # | 命令（省略 `python artifact_inspector/` 前缀，`F=tests/fixtures`） | 判据 | 实测 |
| --- | --- | --- | --- |
| F1 | `check_outputs.py --task DEMO-001 --ledger $F/ledger.json` | 混合样例逐项命中 | exit=1，5/7 失败：A003 仅空白、A004 占位、A002 缺失、A003 空目录、A001 `../evil.ts` 逃逸；`src/ok.ts` 与 `outdir/` 通过 |
| F2 | `check_outputs.py --task DEMO-002 --ledger $F/ledger.json` | 全合格 | exit=0 `OUTPUTS PASSED: 2 项` |
| F3 | `check_outputs.py --root $F/workspace/demo src/ok.ts docs/placeholder.md` | 显式清单模式 | exit=1，A004 |
| F4 | `check_outputs.py --task NOPE-001` | 任务定位失败 | exit=2 USAGE ERROR |
| G1 | `check_testlog.py $F/logs/pytest-pass.log vitest-pass.log surefire-pass.log` | 三框架 good 全绿 | exit=0，识别 pytest/vitest/maven-surefire 且 exit_code=0 |
| G2 | `check_testlog.py $F/logs/vitest-skip.log` | skipped 预警不拦门 | exit=0 + A025 WARN |
| G3 | `check_testlog.py pytest-fail.log jest-fail.log surefire-fail.log` | 失败样例 | exit=1，每份命中 A021+A024（surefire 计 failed=3 即 Failures1+Errors2） |
| G4 | `check_testlog.py $F/logs/no-exitcode.log` | 退出码未留存 | exit=1 A023 |
| G5 | `check_testlog.py $F/logs/nonsense.log` | 非测试输出 | exit=1 A020 |
| H1 | `check_excerpt.py $F/logs/pytest-pass.log --from-report $F/report.md` | 报告 1 真 1 伪 | exit=1：excerpt0 精确命中，excerpt1 A030 |
| H2 | `--excerpt "============ 19 passed in 12.34s ============="` | 原文精确 | exit=0 |
| H3 | `--excerpt "19 passed  in 12.34s"`（双空格） | 归一化命中 | exit=0 + A031 WARN |
| H4 | 在 fail 日志中回溯 pass 摘录 | 伪造 | exit=1 A030 |
| I1 | `scan_side_effects.py snapshot <scratch>/deps --out baseline.json` | 基线快照 | exit=0，3 个清单文件入快照（源码文件不入账） |
| I2 | 改 `package.json` + 加 `Cargo.toml` 后 compare | 未声明改动 | exit=1，A040 ADDED + A040 MODIFIED |
| I3 | 同改动 compare `--declared package.json --declared Cargo.toml` | 已声明放行 | exit=0，两条 A041 INFO |
| I4 | 删除 `.github/workflows/ci.yml` 后 compare | 删除扫描 | exit=1，A040 DELETED |
| I5 | 全新拷贝对原基线 compare | 无改动 | exit=0 `SIDE EFFECTS CLEAN` |

## 已知盲区（脚本查不出的绕过类别，验收时仍需人工）

1. 全真伪造日志：手工拼出一帧合规的框架汇总行 + 退出码行可骗过文本判据。本工具核的是"凭证间一致性"，真实性的最终兜底仍是 PM 在 root_dir 重跑命令（review-criteria 一节 2）。
2. 摘录被改写成另一种排版（补省略号、改换行位置、大小写调整）时，精确与空白归一化都判 MISSING，语义级比对不属静态工具职责。
3. 框架覆盖面为 pytest / vitest / jest / maven-surefire；go test、dotnet、gradle 原生输出、cypress 等按 A020 拒绝，宁可误拦也不放行不可识别日志。
4. xfail/flaky 重试后成功、覆盖率阈值调低、`@Disabled` 源码级绕门：这些动作在测试代码里，不在日志里，归 scaffold 门禁与 code review。
5. 副作用扫描依赖快照时点纪律：必须在派发（TODO→IN_PROGRESS）时打快照；先改依赖后打快照、或基线文件被同步伪造，超出本工具能力。
6. 占位识别按"全注释行 + 占位词"启发式；混入 1 行真实代码的"占位"文件会放行，由功能判据兜底。
7. 0 字节与仅空白等价处理，但仅含空对象 `{}`、空标签等"结构上为空"的文件不在此判，需人工或类型化检查。
