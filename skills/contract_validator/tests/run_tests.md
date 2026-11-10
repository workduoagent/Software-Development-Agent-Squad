# contract_validator 回归测试

依赖安装（一次性）：`python -m pip install -r requirements.txt`（Python ≥ 3.10）。
在 `skills/contract_validator/` 目录下依次执行，比对预期：

| # | 命令 | 预期 |
| --- | --- | --- |
| 1 | `python lint.py tests/fixtures/auth-api-v1.yaml` | `LINT PASSED: 0 errors, 0 warnings`，exit 0 |
| 2 | `python lint.py tests/fixtures/auth-api-v2-additive.yaml` | `LINT PASSED`，exit 0 |
| 3 | `python lint.py tests/fixtures/auth-api-invalid.yaml` | `LINT FAILED`，exit 1，命中 E001/E002/E003/E004/E005/E006/E007/E008/E009/E011/E100 共 15 errors |
| 4 | `python diff.py tests/fixtures/auth-api-v1.yaml tests/fixtures/auth-api-v2-additive.yaml` | `纯增量 ADDITIVE x2`，exit 0 |
| 5 | `python diff.py tests/fixtures/auth-api-v1.yaml tests/fixtures/auth-api-v2-breaking.yaml` | `BREAKING_CHANGE x3`（新增必填 captcha、data.userId 类型变更、data.expiresIn 删除），exit 2 |
| 6 | `python freeze.py tests/fixtures/auth-api-invalid.yaml` | `FREEZE REFUSED`，exit 1 |
| 7 | `python freeze.py tests/fixtures/auth-api-v1.yaml` | `FREEZE OK`，exit 0，生成 `.lock.json` 与 PM 登记块（sha256 一致）；测试后删除锁文件 |
| 8 | `python mock_gen.py tests/fixtures/auth-api-v1.yaml` | stdout 输出 6 条报文，全部 `source: example` |

夹具说明：v1 = 合法基线（注册/登录，allOf 组合 Result 与业务 data）；v2-additive = 新接口 + 可选字段 + 新错误码；v2-breaking = 三处破坏性变更；invalid = 多违规集合。
