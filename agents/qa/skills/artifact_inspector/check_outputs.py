"""outputs 物理核验：存在性、非空、非占位、路径不逃逸 root_dir。对应 review-criteria 一节 1/5 两条通用判据。

用法:
  python check_outputs.py --task <TASK-ID> [--ledger tasks.json]   # 从账本任务卡取 outputs
  python check_outputs.py --root <dir> <rel_path> [<rel_path> ...] # 显式清单
退出码: 0 全部通过; 1 命中 ERROR; 2 参数或账本定位失败。
检查码 A001-A004 定义见 SKILL.md。
"""
import argparse
import json
import os
import sys

from common import (placeholder_only, print_check, read_text, safe_join,
                    usage, write_report)

SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", "__pycache__", "venv", ".venv"}


def check_one(root, rel, results):
    loc = rel
    abs_path = safe_join(root, rel)
    if abs_path is None:
        print_check("A001", "ERROR", loc, "路径逃逸 root_dir 或为绝对路径")
        results.append({"path": rel, "verdict": "ESCAPE"})
        return False

    ok = True
    if os.path.isdir(abs_path):
        files = [os.path.join(dp, fn) for dp, dn, fns in os.walk(abs_path)
                 for fn in fns if not SKIP_DIRS & set(dp.split(os.sep))]
        nonempty = [p for p in files if os.path.getsize(p) > 0] if files else []
        if not nonempty:
            print_check("A003", "ERROR", loc, "目录产出物不存在或无任何非空文件")
            ok = False
        results.append({"path": rel, "verdict": "DIR_OK" if ok else "DIR_EMPTY",
                        "files": len(nonempty)})
        return ok

    if not os.path.isfile(abs_path):
        print_check("A002", "ERROR", loc, "物理文件不存在")
        results.append({"path": rel, "verdict": "MISSING"})
        return False

    size = os.path.getsize(abs_path)
    if size == 0:
        print_check("A003", "ERROR", loc, "0 字节空文件")
        ok = False
    else:
        text = read_text(abs_path)
        if not text.strip():
            print_check("A003", "ERROR", loc, "仅空白字符，等同空文件")
            ok = False
        elif placeholder_only(text):
            print_check("A004", "ERROR", loc, "正文全部为占位 TODO 注释，按不存在处理")
            ok = False
    results.append({"path": rel, "verdict": "OK" if ok else "FAIL", "bytes": size})
    return ok


def resolve_from_ledger(task_id, ledger_path):
    if not os.path.isfile(ledger_path):
        usage(f"账本不存在: {ledger_path}")
    with open(ledger_path, encoding="utf-8") as f:
        ledger = json.load(f)
    for p in ledger.get("projects", []):
        for t in p.get("tasks", []):
            if t.get("task_id") == task_id:
                base = os.path.dirname(os.path.abspath(ledger_path)) or "."
                root = os.path.normpath(os.path.join(base, p.get("root_dir", ".")))
                outputs = t.get("outputs", [])
                if not outputs:
                    usage(f"{task_id} 的 outputs 为空，任务卡不合规")
                return root, outputs, p.get("project_id")
    usage(f"任务不存在: {task_id}")


def main():
    ap = argparse.ArgumentParser(description="outputs 物理核验")
    ap.add_argument("--task")
    ap.add_argument("--ledger", default="tasks.json")
    ap.add_argument("--root")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--report")
    args = ap.parse_args()

    if args.task:
        root, rels, pid = resolve_from_ledger(args.task.upper(), args.ledger)
        loc_prefix = f"{pid}.{args.task.upper()}"
    elif args.root:
        root, rels = args.root, args.files
        loc_prefix = args.root
        if not rels:
            usage("显式模式必须给出至少一个相对路径")
    else:
        usage("必须提供 --task 或 --root 其一")

    if not os.path.isdir(root):
        usage(f"项目 root_dir 不存在: {root}")

    results = []
    failed = 0
    print_check("A000", "INFO", loc_prefix, f"root={root} outputs={len(rels)}")
    for rel in rels:
        if not check_one(root, str(rel), results):
            failed += 1
    verdict = {"task": args.task, "root": root, "checked": len(rels), "failed": failed,
               "items": results}
    if args.report:
        write_report(args.report, verdict)
    if failed:
        print(f"OUTPUTS FAILED: {failed}/{len(rels)} 项未通过物理核验")
        sys.exit(1)
    print(f"OUTPUTS PASSED: {len(rels)} 项产出物全部存在、非空且非占位")
    sys.exit(0)


if __name__ == "__main__":
    main()
