# 设备环境档案（device-env）

> **用途**：Waker 在本机执行门禁、联调与脚本时的环境事实取值真源。各角色 bible 的「权威输入」引用本档案；散活与联调同样从这里取环境信息。
> **装配**：把本模板复制到本机仓库根并重命名为 `device-env.md`，按实况填写（该文件已加入 `.gitignore`，不进 git）。
> **红线**：口令、Token、密钥一律不写入本文件——只记环境变量名与取值来源（系统环境变量 / 凭据管理器）。本档案记录的是**事实**不是规范；改动后知会相关实例即可。

## 仓库与路径（PM 寻址依据；散活对话时直接告知实例或让它读本节）

| 项 | 值 |
| --- | --- |
| squad_root（本机仓库根） | <填写绝对路径，如 E:\Codes\ABC\Software-Development-Agent-Squad> |
| ledger（中央账本） | `{squad_root}\tasks.json` |
| root_dir（项目根） | 随项目在触发时给定，可指向仓库外工程 |

## 工具链（java-dev / react-dev / tauri-dev / py-* 的门禁与构建依赖）

| 工具 | 版本 | 路径 / 命令 | 备注 |
| --- | --- | --- | --- |
| JDK | 21 | `JAVA_HOME=<填写>` | 发行版：<填写> |
| Maven | 3.9.x | `mvn` | settings.xml 路径：<填写>；镜像源：<填写> |
| Node | 20.x | `node` / `npm` / `pnpm` | pnpm <填写> |
| Rust | stable | `cargo` | Tauri 构建依赖 |
| Python | 3.12.x | conda env：`squad-py` | conda 安装路径：<填写>；后端与脚本共用或分 env 注明 |
| Git | 2.x | `git` | — |
| bash | Git Bash | `bash` | check_secrets.sh / check_security.sh / check_db_ops.sh 依赖 |

## 数据源（backend / qa 使用；连接串由技能 assets 模板按环境变量组装）

| 实例标识 | 引擎 | host:port | 库名 | 用户 | 口令来源 |
| --- | --- | --- | --- | --- | --- |
| dev-pg | PostgreSQL 16 | <填写> | <填写> | <填写> | 环境变量 `SQUAD_PG_PASSWORD` |
| dev-mysql | MySQL 8 | <填写> | <填写> | <填写> | 环境变量 `SQUAD_MYSQL_PASSWORD` |

## 联调服务地址（react-dev ↔ java-dev / py-backend / tauri-dev）

| 服务 | 地址 | 启动方式 |
| --- | --- | --- |
| 后端本地（Java） | http://<填写> | `mvn spring-boot:run` |
| 后端本地（Python） | http://<填写> | `uvicorn app.main:app --reload` |
| 前端本地 | http://<填写> | `npm run dev` |

## 环境变量清单

| 变量名 | 用途 | 取值来源 |
| --- | --- | --- |
| SQUAD_PG_PASSWORD | PostgreSQL 口令 | 系统环境变量（用户级） |
| SQUAD_MYSQL_PASSWORD | MySQL 口令 | 系统环境变量（用户级） |
| SQUAD_JWT_SECRET | 服务 JWT 签名密钥 | 系统环境变量（用户级） |

> 待拍板参数（Token 有效期、锁定阈值、审计留存等）不在本档案记录取值——它们属于 Tech Spec §七，本档案只记环境事实。
