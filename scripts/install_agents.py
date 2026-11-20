# -*- coding: utf-8 -*-
"""把本仓库的角色 prompt 安装为 Qoder 用户级自定义 Agent。

用法：python scripts/install_agents.py [--dest <dir>] [--dry-run]

真源只有一个：本仓库 agents/**/prompt.md。运行时目录里的 .md 只是装机产物，
不要在客户端目录里就地编辑——改完重跑本脚本即可覆盖。
只有带 YAML frontmatter 的 prompt.md 才会被安装；缺 frontmatter 的占位稿跳过。
角色技能真源在 agents/**/skills/，与本脚本无关；运行时技能由插件包提供
（scripts/package_plugin.py 从各角色目录扁平化进插件 skills/）。
"""
import argparse
import os
import shutil
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DEST = os.path.join(os.path.expanduser("~"), ".qoder-cn", "agents")
REQUIRED_KEYS = ("name", "description")


def parse_frontmatter(text):
    """返回 (字段字典, 是否合法)。仅支持本仓库用到的扁平 key: value 形式。"""
    if not text.startswith("---"):
        return {}, False
    lines = text.split("\r\n" if "\r\n" in text[:200] else "\n")
    if not lines or lines[0].strip() != "---":
        return {}, False
    fields, idx = {}, None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            idx = i
            break
        if ":" in lines[i] and not lines[i].startswith((" ", "\t")):
            key, _, value = lines[i].partition(":")
            fields[key.strip()] = value.strip()
    if idx is None:
        return {}, False
    for key in REQUIRED_KEYS:
        if not fields.get(key):
            return {}, False
    return fields, True


def collect_sources():
    sources = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(REPO_ROOT, "agents")):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        if "prompt.md" in filenames:
            sources.append(os.path.join(dirpath, "prompt.md"))
    return sorted(sources)


def main(argv):
    parser = argparse.ArgumentParser(description="Install squad role prompts as Qoder user Agents.")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="Agent 目录，默认 ~/.qoder-cn/agents")
    parser.add_argument("--backup-dir", default=None, help="覆盖前把旧文件备份到此目录，默认 %TEMP%")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = parser.parse_args(argv)

    dest = os.path.abspath(os.path.expanduser(args.dest))
    if not os.path.isdir(dest):
        print("USAGE ERROR: Agent 目录不存在: %s" % dest)
        return 2
    backup_dir = args.backup_dir or os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp",
                                                 "agent-install-backup")

    rows, changed = [], 0
    for src in collect_sources():
        rel = os.path.relpath(src, REPO_ROOT).replace(os.sep, "/")
        with open(src, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
        fields, ok = parse_frontmatter(text)
        if not ok:
            rows.append(("SKIP", rel, "-", "缺 YAML frontmatter（占位稿，不是可安装 Agent）"))
            continue
        target = os.path.join(dest, "%s.md" % fields["name"])
        if os.path.exists(target):
            with open(target, "rb") as f:
                same = f.read() == raw
            if same:
                rows.append(("UNCHANGED", rel, fields["name"], "与运行时一致"))
                continue
            if not args.dry_run:
                if not os.path.isdir(backup_dir):
                    os.makedirs(backup_dir)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                kept = os.path.join(backup_dir, "%s.%s.md" % (stamp, fields["name"]))
                shutil.copyfile(target, kept)
                rows.append(("UPDATED", rel, fields["name"], "旧文件备份 -> %s" % kept))
            else:
                rows.append(("UPDATED", rel, fields["name"], "将覆盖并备份旧文件"))
        else:
            rows.append(("ADDED", rel, fields["name"], "新建"))
        changed += 1
        if not args.dry_run:
            with open(target, "wb") as f:
                f.write(raw)

    print("AGENT INSTALL %s -> %s" % ("(dry-run)" if args.dry_run else "", dest))
    for verdict, rel, name, note in rows:
        print("  %-9s %-42s %-16s %s" % (verdict, rel, name, note))
    written = sum(1 for r in rows if r[0] in ("ADDED", "UPDATED"))
    skipped = sum(1 for r in rows if r[0] == "SKIP")
    same = sum(1 for r in rows if r[0] == "UNCHANGED")
    print("SUMMARY: 扫描 %d 个 prompt.md，写入 %d，已一致 %d，跳过 %d%s" % (
        len(rows), written, same, skipped, "（dry-run 未落盘）" if args.dry_run else ""))
    if written and not args.dry_run:
        print("NEXT: 新建会话后在 设置 -> 智能体 核对；运行时注册状态须单独核验。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
