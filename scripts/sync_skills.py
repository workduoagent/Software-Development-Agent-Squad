#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把各角色目录下的 skills 扁平化成运行时 skills/ 视图。

真源：agents/**/skills/<skill>/，同一 skill 可被多个角色各持一份副本。
产物：skills/<skill>/（生成目录，不手改），供插件打包与本机命令共用 skills/<skill>/ 寻址。

副本一致性：同名 skill 的多份副本必须逐字节一致；不一致时直接报错退出，
避免"以某角色为准"的隐式选择。退出码 0 成功 / 1 副本冲突 / 2 路径错误。
"""

import argparse
import hashlib
import os
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"__pycache__", ".scratch", ".git", "node_modules"}
SKIP_FILES = {".pyc"}


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(src):
    items = {}
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if os.path.splitext(name)[1] in SKIP_FILES:
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, src).replace(os.sep, "/")
            items[rel] = file_digest(full)
    return items


def collect_sources():
    found = {}
    agents_dir = os.path.join(REPO_ROOT, "agents")
    for root, dirs, files in os.walk(agents_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        if "SKILL.md" not in files:
            continue
        rel = os.path.relpath(root, REPO_ROOT).replace(os.sep, "/")
        parts = rel.split("/")
        if "skills" not in parts:
            continue
        idx = parts.index("skills")
        if idx + 1 >= len(parts):
            continue
        name = parts[idx + 1]
        found.setdefault(name, []).append(root)
    return {name: sorted(paths) for name, paths in sorted(found.items())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", default=os.path.join(REPO_ROOT, "skills"),
                        help="扁平化产物目录，默认 <repo>/skills")
    parser.add_argument("--check", action="store_true", help="只校验副本一致性，不写文件")
    args = parser.parse_args(argv)

    sources = collect_sources()
    if not sources:
        print("FAIL: agents/**/skills/ 下没有找到任何 SKILL.md", file=sys.stderr)
        return 2

    dest = os.path.abspath(args.dest)
    conflicts = []
    chosen = {}
    for name, paths in sources.items():
        base = manifest(paths[0])
        for other in paths[1:]:
            if manifest(other) != base:
                conflicts.append((name, paths[0], other))
        chosen[name] = paths[0]

    if conflicts:
        print("FAIL: 同名 skill 副本不一致，未生成任何产物", file=sys.stderr)
        for name, a, b in conflicts:
            print("  %s: %s != %s" % (name, os.path.relpath(a, REPO_ROOT), os.path.relpath(b, REPO_ROOT)),
                  file=sys.stderr)
        return 1

    if args.check:
        for name, paths in sources.items():
            print("OK %-22s 副本 %d 份一致  %s" % (
                name, len(paths), ", ".join(os.path.relpath(p, REPO_ROOT).replace(os.sep, "/") for p in paths)))
        print("CHECK OK: %d 个 skill，无冲突" % len(sources))
        return 0

    os.makedirs(dest, exist_ok=True)
    for stale in os.listdir(dest):
        stale_path = os.path.join(dest, stale)
        if stale not in chosen and os.path.isdir(stale_path):
            shutil.rmtree(stale_path)
    for name, src in chosen.items():
        target = os.path.join(dest, name)
        if os.path.isdir(target):
            shutil.rmtree(target)
        shutil.copytree(src, target)
        print("SYNC %-22s <- %s" % (name, os.path.relpath(src, REPO_ROOT).replace(os.sep, "/")))
    print("SUMMARY: 已生成 %d 个 skill 到 %s" % (len(chosen), os.path.relpath(dest, REPO_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
