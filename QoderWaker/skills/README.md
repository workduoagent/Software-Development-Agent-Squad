# 技能装配说明

> 技能真源在 `agents/**/skills/<skill>/`，同名副本逐字节一致（`scripts/sync_skills.py --check` 校验）。技能包本身不复制进本目录，按下面流程取用。

## 生成扁平视图（上传前执行）

```bash
python scripts/sync_skills.py        # 生成仓库根 skills/<skill>/，9 个技能包
```

## 技能包与绑定关系

| 技能 | 内容 | 绑定到（实例级挂载） |
| --- | --- | --- |
| task_tracker | 账本校验 / 看板 / 派发检查 / 状态流转 / 契约登记 | pm-01 |
| artifact_inspector | 产出物 / 测试日志 / 摘录 / 副作用核验 | pm-01、qa-01 |
| contract_validator | Lint / Diff / 指纹冻结 / Mock 生成 | architect-01、qa-01 |
| database-ops | 数据侧规范与 D0xx 门禁 | architect-01、java-dev-01、py-backend-dev-01 |
| springboot-scaffold | JDK 21 + Spring Boot 3 工程基线 | java-dev-01 |
| python-backend-scaffold | Python 3.12 + FastAPI 工程基线（初版） | py-backend-dev-01 |
| react-scaffold | React 19 + Vite + antd 基线 | react-dev-01、tauri-dev-01 |
| tauri2-scaffold | Tauri 2 桌面基线 | tauri-dev-01 |
| python-scripting | Python 脚本工程基线（可复现/幂等/无机密） | py-script-dev-01 |

绑定方式按 `../wakers/instances.md`：**角色模板级不挂栈技能，全部在实例上挂载**（「技能直接绑给具体智能体」）。pm / architect / qa 模板级可挂各自技能，程序员模板级保持为空。

## 上传与依赖

- 「上传 Skill」接受目录还是 zip 需实测（pilot 第一项）。
- 带 `requirements.txt` 的技能（task_tracker、artifact_inspector、contract_validator、python-backend-scaffold）在本机预装 Python 依赖；bash 门禁脚本（check_secrets.sh / check_security.sh / check_db_ops.sh）要求本机 bash 可用；Python 版机检（check_secrets.py）随 python-backend-scaffold 分发。
- 脚本只留在技能包里、不复制进项目；运行时命令以 skill 名开头寻址（如 `task_tracker/validate.py`）。

## 纪律

- 技能目录不手改：改技能先改 `agents/**/skills/` 真源 → `sync_skills.py` 重生成 → 重新上传对应技能。
- 同名副本不一致时 `sync_skills.py` 会拒绝生成，此时禁止上传任何一方的版本。
