"""看板汇总：按项目输出任务状态分布、待派发就绪队列、阻塞清单与打回红线预警。

用法: python board.py [--ledger tasks.json] [--project <project_id>] [--json]
退出码: 0 正常; 2 账本读取失败。只读工具，不写账本。
"""
import argparse
import json
import sys
from collections import Counter

from common import load_ledger


def same_reason_counts(task):
    c = Counter()
    for r in task.get("rejection_history", []) or []:
        if isinstance(r, dict) and r.get("reason"):
            c[str(r["reason"])] += 1
    return c


def readiness(project, ledger):
    """粗判 TODO 任务是否可能就绪：契约类 inputs 均已登记。精细检查交给 check_dispatch。"""
    paths = {str(c.get("path", "")).replace("\\", "/") for c in project.get("contracts", []) or []
             if isinstance(c, dict)}
    ready = []
    for t in project.get("tasks", []) or []:
        if t.get("status") != "TODO":
            continue
        inputs = [str(i) for i in t.get("inputs", []) or []]
        contract_inputs = [i for i in inputs if i.replace("\\", "/").startswith("contracts/")]
        if all(ci in paths for ci in contract_inputs):
            ready.append(t["task_id"])
    return ready


def main():
    ap = argparse.ArgumentParser(description="任务看板")
    ap.add_argument("--ledger", default="tasks.json")
    ap.add_argument("--project")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ledger = load_ledger(args.ledger)
    boards = []
    for p in ledger["projects"]:
        if args.project and p.get("project_id") != args.project:
            continue
        tasks = p.get("tasks", []) or []
        counts = Counter(str(t.get("status")) for t in tasks)
        blocked = [{"task_id": t.get("task_id"), "note": t.get("verification_log", "")}
                   for t in tasks if t.get("status") == "BLOCKED"]
        redline = [{"task_id": t.get("task_id"), "reason": reason, "times": n}
                   for t in tasks for reason, n in same_reason_counts(t).items() if n >= 2]
        boards.append({
            "project_id": p.get("project_id"),
            "project_name": p.get("project_name"),
            "root_dir": p.get("root_dir"),
            "counts": {s: counts.get(s, 0) for s in
                       ("TODO", "IN_PROGRESS", "IN_REVIEW", "ACCEPTED", "REJECTED", "BLOCKED")},
            "contracts": len(p.get("contracts", []) or []),
            "ready_to_dispatch": readiness(p, ledger),
            "blocked": blocked,
            "redline_warnings": redline,
        })

    if args.json:
        print(json.dumps(boards, ensure_ascii=False, indent=2))
        sys.exit(0)

    for b in boards:
        c = b["counts"]
        print(f"== {b['project_id']} ({b['project_name']}) root={b['root_dir']}")
        print("   TODO={} IN_PROGRESS={} IN_REVIEW={} ACCEPTED={} REJECTED={} BLOCKED={} contracts={}".format(
            c["TODO"], c["IN_PROGRESS"], c["IN_REVIEW"], c["ACCEPTED"], c["REJECTED"], c["BLOCKED"],
            b["contracts"]))
        if b["ready_to_dispatch"]:
            print(f"   就绪待派发(粗筛，派发前仍须 check_dispatch): {', '.join(b['ready_to_dispatch'])}")
        for x in b["blocked"]:
            print(f"   BLOCKED {x['task_id']}: {x['note'][:80]}")
        for w in b["redline_warnings"]:
            print(f"   红线预警 {w['task_id']}: 同一原因打回 {w['times']} 次 -> {w['reason'][:60]}")
    if not boards:
        print("账本中无项目（projects 为空或 --project 未命中）")
    sys.exit(0)


if __name__ == "__main__":
    main()
