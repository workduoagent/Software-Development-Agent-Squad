"""副作用扫描：对公共依赖与配置清单文件做基线快照，验收时比对未声明的改动。对应 review-criteria 一节 3。

用法:
  python scan_side_effects.py snapshot <root_dir> [--out baseline.json]
  python scan_side_effects.py compare <root_dir> --baseline baseline.json [--declared <rel>]... [--report r.json]
工作流：PM 派发（TODO -> IN_PROGRESS）时对 root_dir 打快照，验收时 compare；
--declared 传入任务卡 outputs 与已获批变更请求的文件，命中清单内的改动只记 INFO。
退出码: 0 无未声明改动; 1 命中未声明改动; 2 目录/基线文件缺失。
检查码 A040-A041 定义见 SKILL.md。快照之后的改动才可对比，快照时刻之前的漂移不属本工具职责。
"""
import argparse
import fnmatch
import json
import os
import sys

from common import print_check, safe_join, sha256_file, usage, write_report

SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", "__pycache__",
             "venv", ".venv", "vendor", ".idea"}

# 公共依赖与配置基线：包管理清单、锁文件、构建与 CI 配置、工程级配置文件
DEP_BASENAMES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "gradle.properties",
    "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock",
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum",
    "composer.json", "composer.lock",
}
DEP_PATTERNS = [
    "requirements*.txt", "docker-compose*.yml", "docker-compose*.yaml",
    "vite.config.*", "vitest.config.*", "jest.config.*", "tsconfig*.json",
    ".eslintrc*", ".prettierrc*",
]
DEP_DIRS = {os.path.join(".github", "workflows")}


def is_dep(rel):
    parts = rel.split("/")
    for d in DEP_DIRS:
        if rel.startswith(d.replace(os.sep, "/") + "/"):
            return True
    name = parts[-1]
    if name in DEP_BASENAMES:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in DEP_PATTERNS)


def collect(root):
    entries = {}
    for dp, dn, fns in os.walk(root):
        dn[:] = [x for x in dn if x not in SKIP_DIRS]
        for fn in fns:
            abs_p = os.path.join(dp, fn)
            rel = os.path.relpath(abs_p, root).replace(os.sep, "/")
            if is_dep(rel):
                entries[rel] = {"sha256": sha256_file(abs_p), "bytes": os.path.getsize(abs_p)}
    return entries


def cmd_snapshot(args):
    if not os.path.isdir(args.root_dir):
        usage(f"目录不存在: {args.root_dir}")
    entries = collect(args.root_dir)
    out = args.out or os.path.join(args.root_dir, ".side_effect_baseline.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"root_dir": args.root_dir, "files": entries}, f, ensure_ascii=False, indent=2,
                  sort_keys=True)
    print(f"BASELINE OK: {len(entries)} 个依赖/配置文件已快照 -> {out}")
    sys.exit(0)


def cmd_compare(args):
    if not os.path.isdir(args.root_dir):
        usage(f"目录不存在: {args.root_dir}")
    if not os.path.isfile(args.baseline):
        usage(f"基线文件不存在: {args.baseline}（派发任务时应先 snapshot）")
    with open(args.baseline, encoding="utf-8") as f:
        base = json.load(f).get("files", {})
    current = collect(args.root_dir)
    declared = {str(d).replace(os.sep, "/") for d in args.declared}

    hits, infos = [], []
    for rel, meta in sorted(current.items()):
        old = base.get(rel)
        if old is None:
            status = "ADDED"
        elif old["sha256"] != meta["sha256"]:
            status = "MODIFIED"
        else:
            continue
        if rel in declared:
            print_check("A041", "INFO", rel, f"{status}（已声明，核对 CR 范围后放行）")
            infos.append({"path": rel, "change": status, "declared": True})
        else:
            print_check("A040", "ERROR", rel, f"{status} 且未在任务卡 outputs/CR 声明清单内")
            hits.append({"path": rel, "change": status, "declared": False})
    for rel in sorted(base):
        if rel not in current:
            if rel in declared:
                print_check("A041", "INFO", rel, "DELETED（已声明）")
                infos.append({"path": rel, "change": "DELETED", "declared": True})
            else:
                print_check("A040", "ERROR", rel, "DELETED 且未声明")
                hits.append({"path": rel, "change": "DELETED", "declared": False})

    report = {"root_dir": args.root_dir, "baseline": args.baseline,
              "tracked": len(current), "undeclared_hits": hits, "declared_changes": infos}
    if args.report:
        write_report(args.report, report)
    if hits:
        print(f"SIDE EFFECTS FOUND: {len(hits)} 处未声明的依赖/配置改动，按 review-criteria 一节 3 直接不通过")
        sys.exit(1)
    print(f"SIDE EFFECTS CLEAN: 比对 {len(current)} 个清单文件，无未声明改动"
          + (f"（{len(infos)} 处已声明变更见 INFO）" if infos else ""))
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description="副作用扫描")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("snapshot")
    p1.add_argument("root_dir")
    p1.add_argument("--out")
    p1.set_defaults(func=cmd_snapshot)
    p2 = sub.add_parser("compare")
    p2.add_argument("root_dir")
    p2.add_argument("--baseline", required=True)
    p2.add_argument("--declared", action="append", default=[])
    p2.add_argument("--report")
    p2.set_defaults(func=cmd_compare)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
