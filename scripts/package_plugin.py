"""把本仓库装配成可安装的 Qoder Plugin 目录与 zip。

用法: python scripts/package_plugin.py [--out dist]
产物: <out>/<plugin-name>/  与  <out>/<plugin-name>-<version>.zip
排除: .idea/、dist/、agents/（Qoder 按约定加载其为 Agent 定义，见下方注释）、
中央账本 tasks.json（账本不随插件分发，依据见 软件团队知识库/任务状态机.md R4）、仓库根 skills/（生成视图，下面单独装配）。

技能真源在各角色目录 agents/**/skills/，打包时由 sync_skills.py 扁平化进插件根 skills/；
同名副本不一致直接失败，避免插件悄悄选用某一角色的版本。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_skills

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# agents/ 必须排除：Qoder 安装器按约定递归加载 agents/ 下每个 .md 为 Agent 定义，
# 缺 YAML frontmatter 即报 plugin.agent.invalid，整包安装失败（实测 14/14 命中）。
# skills/ 也排除：它是生成视图，改由 sync_skills.py 从角色目录装配，避免重复入包。
EXCLUDED_PREFIXES = (".idea/", "dist/", ".git/", "agents/", "skills/")
EXCLUDED_FILES = {"tasks.json"}


def git_file_list():
    """仓库内被版本控制的文件 + 未被 .gitignore 忽略的新文件。"""
    args = ["git", "-c", "core.quotePath=false", "ls-files"]
    found = set()
    for extra in ([], ["--others", "--exclude-standard"]):
        proc = subprocess.run(args + extra, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            return None
        for line in proc.stdout.splitlines():
            name = line.strip().strip('"')
            if name:
                found.add(name.replace("\\", "/"))
    return sorted(found)


def selected_files():
    names = git_file_list()
    if names is None:
        print("FAIL: git 不可用，无法确定分发清单", file=sys.stderr)
        sys.exit(2)
    keep = []
    for name in names:
        if name in EXCLUDED_FILES or name.startswith(EXCLUDED_PREFIXES):
            continue
        if os.path.exists(os.path.join(REPO_ROOT, name)):
            keep.append(name)
    return keep


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="dist", help="产物目录，默认 dist")
    args = parser.parse_args(argv)

    manifest_path = os.path.join(REPO_ROOT, ".qoder-plugin", "plugin.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    plugin_name, version = manifest["name"], manifest["version"]

    out_dir = os.path.join(REPO_ROOT, args.out.replace("/", os.sep))
    stage_dir = os.path.join(out_dir, plugin_name)
    if os.path.exists(stage_dir):
        shutil.rmtree(stage_dir)

    files = selected_files()
    for rel in files:
        dest = os.path.join(stage_dir, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(os.path.join(REPO_ROOT, rel), dest)

    skill_dest = os.path.join(stage_dir, "skills")
    if sync_skills.main(["--dest", skill_dest]) != 0:
        print("FAIL: 技能副本校验或装配失败", file=sys.stderr)
        sys.exit(1)
    files.extend(os.path.relpath(os.path.join(root, name), stage_dir).replace(os.sep, "/")
                 for root, _, names in os.walk(skill_dest) for name in names)

    zip_path = os.path.join(out_dir, f"{plugin_name}-{version}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in files:
            archive.write(os.path.join(stage_dir, rel.replace("/", os.sep)), rel)

    print(f"STAGED  {stage_dir}")
    print(f"ZIP     {zip_path}")
    print(f"FILES   {len(files)}  BYTES {os.path.getsize(zip_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
