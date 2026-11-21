# -*- coding: utf-8 -*-
"""把 QoderWaker 装配底稿打包成「上传就绪目录 + 本次操作单」。

用法：python scripts/package_waker.py [--out dist/qoderwaker-upload] [--flat-zip]

产物（<out>/）：
  00-OPERATION.md                    本次装机/更新操作单（含增量重传清单与全部表单文案）
  01-skills/<skill>/ 与 <skill>.zip  技能扁平视图 + 上传用 ZIP（平台仅支持 ZIP 上传）
  02-knowledge-base/                 知识库上传文件（不含装配 README）
  03-roles/<template>/               identity.md / persona.md / bible.md
  04-wakerflow/main-flow-prompt.md   WakerFlow 生成底稿
  05-device-env/                     设备环境档案模板

增量检测：<out>/.state.json 记录上次打包的每文件 sha256；重跑本脚本自动比对，
在 00-OPERATION.md 顶部输出「增量重传清单」——标准迭代流程：
改仓库真源 -> 重跑本脚本 -> 照清单重传变更文件 -> 重验受影响能力。
保留 <out>/ 目录（含 .state.json）以维持增量比对；删除 dist 即重置基线。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_skills

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QW = os.path.join(REPO_ROOT, "QoderWaker")

# 装配顺序：试点角色在前。目录名 -> 平台表单「角色名称」
TEMPLATES = [
    ("architect", "系统架构师"),
    ("pm", "项目经理"),
    ("frontend", "前端程序员"),
    ("backend", "后端程序员"),
    ("desktop", "桌面程序员"),
    ("scripting", "脚本程序员"),
    ("qa", "质检工程师"),
]
TEMPLATE_SKILLS = {
    "architect": "contract_validator、database-ops",
    "pm": "task_tracker、artifact_inspector",
    "qa": "artifact_inspector、contract_validator",
    "frontend": "不挂（栈技能在实例）",
    "backend": "不挂（栈技能在实例）",
    "desktop": "不挂（栈技能在实例）",
    "scripting": "不挂（栈技能在实例）",
}
PIECE_FILES = ("identity.md", "persona.md", "bible.md")
SEP = re.compile(r"^:?-{3,}:?$")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def cells_of(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(cells):
    return bool(cells) and all(SEP.match(c) for c in cells)


def parse_instances(path):
    """从 wakers/instances.md 解析模板卡片文案与实例表。解析失败即中止（真源损坏时不猜）。"""
    card, rows = {}, []
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = cells_of(line)
        if not cells or is_separator(cells):
            continue
        if len(cells) == 2 and cells[0] in {zh for _, zh in TEMPLATES}:
            card[cells[0]] = cells[1]
        elif len(cells) == 6 and cells[0] not in ("角色模板",):
            rows.append(cells)
    missing = [zh for _, zh in TEMPLATES if zh not in card or not card[zh]]
    if missing:
        print("FAIL: instances.md 模板卡片文案缺失或不完整：%s" % "、".join(missing), file=sys.stderr)
        sys.exit(2)
    if not rows:
        print("FAIL: instances.md 实例表解析为空", file=sys.stderr)
        sys.exit(2)
    return card, rows


def copy_tree(src, dst):
    shutil.copytree(src, dst)


def zip_dir(dir_path, zip_path, flat=False):
    """打包技能目录为 ZIP。默认 zip 内含同名顶层文件夹；flat=True 时文件置于压缩包根（SKILL.md 在根）。"""
    base = os.path.basename(dir_path.rstrip("/\\"))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, names in os.walk(dir_path):
            for name in sorted(names):
                full = os.path.join(root, name)
                rel = os.path.relpath(full, dir_path)
                arc = rel if flat else os.path.join(base, rel)
                archive.write(full, arc)


def collect_files(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            found[rel] = sha256_of(full)
    return found


def build_operation(out_dir, card, instance_rows, skill_dirs, kb_files, diff):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    L = []
    L.append("# QoderWaker 装机 / 更新操作单")
    L.append("")
    L.append("> 生成时间：%s。本单由 `scripts/package_waker.py` 生成，阶段编号对应 `QoderWaker/RUNBOOK.md`。" % now)
    L.append("> 表单文案的真源是 `QoderWaker/wakers/instances.md`；改文案请改真源后重跑本脚本。")
    L.append("")

    L.append("## 一、增量重传清单（与上次打包比对）")
    L.append("")
    if diff["first"]:
        L.append("**首次打包：无增量基线，本单即全量装机清单。**")
    elif not diff["added"] and not diff["changed"] and not diff["removed"]:
        L.append("**真源无变化：无需重传任何文件。**")
    else:
        if diff["added"]:
            L.append("**新增 %d 个（新上传）**：" % len(diff["added"]))
            for rel in diff["added"]:
                L.append("- `%s`" % rel)
        if diff["changed"]:
            L.append("")
            L.append("**内容变更 %d 个（到平台对应位置重新上传/重粘）**：" % len(diff["changed"]))
            for rel in diff["changed"]:
                L.append("- `%s`" % rel)
        if diff["removed"]:
            L.append("")
            L.append("**已从真源移除 %d 个（平台侧自行核对下架）**：" % len(diff["removed"]))
            for rel in diff["removed"]:
                L.append("- `%s`" % rel)
    L.append("")
    L.append("映射提示：`01-skills/` -> 平台技能；`02-knowledge-base/` -> 知识库；`03-roles/<模板>/` -> 角色模板三件套；`04-wakerflow/` -> 新建 WakerFlow 粘贴内容。")
    L.append("")

    L.append("## 二、阶段 1：平台资源")
    L.append("")
    L.append("### 1.1 技能上传（01-skills/，平台**仅支持 ZIP**：逐个上传 `<skill>.zip`）")
    L.append("")
    L.append("| 技能包 | 文件数 | 挂载到 |")
    L.append("| --- | --- | --- |")
    bind = {}
    for row in instance_rows:
        inst, skills = row[1], row[3]
        if "暂无" in skills or skills in ("—", ""):
            continue
        for s in re.split("[、,，]", skills):
            s = s.strip()
            if s:
                bind.setdefault(s, []).append(inst)
    for name in skill_dirs:
        L.append("| `%s` | %d | %s |" % (name, skill_dirs[name], "、".join(bind.get(name, ["-"])) or "-"))
    L.append("")
    L.append("### 1.2 知识库上传（02-knowledge-base/，建议命名：软件团队知识库）")
    L.append("")
    L.append("共 %d 个文件（装配 README 已排除）：" % len(kb_files))
    for rel in kb_files:
        L.append("- `%s`" % rel)
    L.append("")

    L.append("## 三、阶段 2：角色模板（03-roles/）")
    L.append("")
    L.append("试点纪律：先建并用核验条目验证 **architect**，通过后再批量建其余。")
    L.append("")
    L.append("| 模板目录 | 表单「角色名称」 | 表单「它主要负责什么」（照抄） | 三件套 | 模板级技能 |")
    L.append("| --- | --- | --- | --- | --- |")
    for dirname, zh in TEMPLATES:
        L.append("| `03-roles/%s/` | %s | %s | identity.md / persona.md / bible.md | %s |" % (
            dirname, zh, card[zh], TEMPLATE_SKILLS[dirname]))
    L.append("")

    L.append("## 四、阶段 3：Waker 实例（全部绑定「软件团队知识库」，运行环境一律本机）")
    L.append("")
    L.append("| 模板 | 实例名 | 数量 | 实例技能 | 「我负责什么」（照抄） | 约束 |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for row in instance_rows:
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    L.append("铁律：**pm-01 严格单例**（账本并发无锁）；py-script-dev-01 散活为主。")
    L.append("")

    L.append("## 五、阶段 4 WakerFlow 与阶段 5 核验")
    L.append("")
    L.append("- 新建 WakerFlow -> 粘贴 `04-wakerflow/main-flow-prompt.md` 全文 -> 按 `QoderWaker/wakerflow/acceptance-checklist.md` 对账（9 阶段 / 7 人工闸门 / 12 机检 + 6 人工对账门禁）。")
    L.append("- 核验：按 `QoderWaker/wakers/instances.md`「装机后核验」逐条过；实测结果记入 RUNBOOK 阶段 5 的记录表。")
    L.append("- 设备环境：`05-device-env/device-env.template.md` 复制到仓库根改名 `device-env.md` 填写（已进 `.gitignore`），并在 pm-01 首次对话里告知仓库根绝对路径。")
    L.append("")
    return "\n".join(L) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="dist/qoderwaker-upload", help="产物目录，默认 dist/qoderwaker-upload")
    parser.add_argument("--flat-zip", action="store_true",
                        help="ZIP 内文件置于压缩包根（SKILL.md 在根）；默认含同名顶层文件夹")
    args = parser.parse_args(argv)

    out = os.path.join(REPO_ROOT, args.out.replace("/", os.sep))
    state_path = os.path.join(out, ".state.json")
    old_state = None
    if os.path.isfile(state_path):
        with open(state_path, encoding="utf-8") as fh:
            old_state = json.load(fh)

    card, instance_rows = parse_instances(os.path.join(QW, "wakers", "instances.md"))

    # 清空产物目录（保留 .state.json）
    os.makedirs(out, exist_ok=True)
    for entry in os.listdir(out):
        if entry == ".state.json":
            continue
        full = os.path.join(out, entry)
        if os.path.isdir(full):
            shutil.rmtree(full)
        else:
            os.remove(full)

    # 01-skills：复用 sync_skills 的扁平化与副本校验
    skills_dest = os.path.join(out, "01-skills")
    if sync_skills.main(["--dest", skills_dest]) != 0:
        print("FAIL: 技能副本校验或装配失败", file=sys.stderr)
        return 1
    skill_dirs = {}
    for name in sorted(os.listdir(skills_dest)):
        full = os.path.join(skills_dest, name)
        if os.path.isdir(full):
            skill_dirs[name] = sum(len(files) for _, _, files in os.walk(full))
            zip_dir(full, os.path.join(skills_dest, "%s.zip" % name), flat=args.flat_zip)

    # 02-knowledge-base：排除装配 README
    kb_src = os.path.join(QW, "knowledge-base")
    kb_dest = os.path.join(out, "02-knowledge-base")
    os.makedirs(kb_dest, exist_ok=True)
    kb_files = []
    for root, _, names in os.walk(kb_src):
        for name in sorted(names):
            if name == "README.md":
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, kb_src)
            dest = os.path.join(kb_dest, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(full, dest)
            kb_files.append(rel.replace(os.sep, "/"))
    kb_files.sort()

    # 03-roles / 04-wakerflow / 05-device-env
    for dirname, _ in TEMPLATES:
        src = os.path.join(QW, "roles", dirname)
        dest = os.path.join(out, "03-roles", dirname)
        os.makedirs(dest, exist_ok=True)
        for piece in PIECE_FILES:
            piece_path = os.path.join(src, piece)
            if not os.path.isfile(piece_path):
                print("FAIL: 缺少 %s" % piece_path, file=sys.stderr)
                return 2
            shutil.copy2(piece_path, os.path.join(dest, piece))
    wf_dest = os.path.join(out, "04-wakerflow")
    os.makedirs(wf_dest, exist_ok=True)
    shutil.copy2(os.path.join(QW, "wakerflow", "main-flow-prompt.md"),
                 os.path.join(wf_dest, "main-flow-prompt.md"))
    de_dest = os.path.join(out, "05-device-env")
    os.makedirs(de_dest, exist_ok=True)
    shutil.copy2(os.path.join(QW, "wakers", "device-env.template.md"),
                 os.path.join(de_dest, "device-env.template.md"))

    # 增量比对 + 操作单
    new_state = collect_files(out)
    diff = {"first": old_state is None, "added": [], "changed": [], "removed": []}
    if old_state is not None:
        for rel in sorted(new_state):
            if rel not in old_state:
                diff["added"].append(rel)
            elif old_state[rel] != new_state[rel]:
                diff["changed"].append(rel)
        for rel in sorted(old_state):
            if rel not in new_state:
                diff["removed"].append(rel)
    diff["added"] = [r for r in diff["added"] if r != "00-OPERATION.md" and r != ".state.json"]
    diff["changed"] = [r for r in diff["changed"] if r != "00-OPERATION.md" and r != ".state.json"]

    operation = build_operation(out, card, instance_rows, skill_dirs, kb_files, diff)
    with open(os.path.join(out, "00-OPERATION.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(operation)

    with open(state_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(new_state, fh, ensure_ascii=False, indent=1, sort_keys=True)

    print("PACKAGE %s" % os.path.relpath(out, REPO_ROOT))
    print("  skills=%d  kb=%d  roles=%d" % (len(skill_dirs), len(kb_files), len(TEMPLATES)))
    if diff["first"]:
        print("  diff: 首次打包（全量清单见 00-OPERATION.md）")
    else:
        print("  diff: 新增 %d / 变更 %d / 移除 %d / 无变化 %d" % (
            len(diff["added"]), len(diff["changed"]), len(diff["removed"]),
            len(new_state) - len(diff["added"]) - len(diff["changed"])))
    print("  operation: %s" % os.path.join(os.path.relpath(out, REPO_ROOT), "00-OPERATION.md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
