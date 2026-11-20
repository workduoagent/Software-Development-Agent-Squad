"""派发前置检查：任务须为 TODO，inputs 依赖的上游任务全部 ACCEPTED，契约类输入已冻结登记且物理文件与登记指纹一致。

用法: python check_dispatch.py <TASK-ID> [--ledger tasks.json] [--report r.json]
退出码: 0 可派发; 1 拒绝派发; 2 账本/任务定位失败。
检查码 P1xx 定义见 SKILL.md。
"""
import argparse
import os
import sys

from common import (TASK_ID_RE, fail, find_task, load_ledger, print_check,
                    project_root_abs, safe_join, sha256_file, write_report)

CONTRACT_PATH_HINT = "contracts/"


def contract_entry(project, rel):
    norm = rel.replace("\\", "/")
    for c in project.get("contracts", []) or []:
        if isinstance(c, dict) and str(c.get("path", "")).replace("\\", "/") == norm:
            return c
    return None


def producers_of(project, rel):
    """返回把该路径声明为 outputs 的同项目任务。"""
    return [t for t in project.get("tasks", []) or [] if rel in (t.get("outputs") or [])]


def run_dispatch_check(task_id, ledger_path):
    ledger = load_ledger(ledger_path)
    project, task = find_task(ledger, task_id)
    pid = project["project_id"]
    root = project_root_abs(ledger_path, project)
    errs = []

    def err(code, loc, msg):
        errs.append(msg)
        print_check(code, "ERROR", loc, msg)

    status = task.get("status")
    if status != "TODO":
        err("P101", f"{pid}.{task_id}", f"status={status}，仅 TODO 任务可派发")
        return {"task_id": task_id, "verdict": "REFUSED", "errors": errs}

    registered_contract_paths = {str(c.get("path", "")).replace("\\", "/")
                                 for c in project.get("contracts", []) or [] if isinstance(c, dict)}

    for rel in task.get("inputs", []) or []:
        loc = f"{pid}.{task_id}.inputs[{rel}]"
        if TASK_ID_RE.match(str(rel)):
            _, up = find_task(ledger, rel)
            if up.get("status") != "ACCEPTED":
                err("P107", loc, f"上游任务 {rel} status={up.get('status')}，未 ACCEPTED 禁止派发")
            continue

        abs_path = safe_join(root, rel)
        if abs_path is None:
            err("P103", loc, "inputs 路径逃逸出项目 root_dir 或为绝对路径")
            continue
        if not os.path.isfile(abs_path):
            err("P102", loc, f"上游物理产物不存在: {abs_path}")
            continue

        up_tasks = [t for t in producers_of(project, rel) if t.get("task_id") != task_id]
        for up in up_tasks:
            if up.get("status") != "ACCEPTED":
                err("P106", loc, f"产出该文件的上游任务 {up['task_id']} status={up.get('status')}，未 ACCEPTED")

        rel_norm = str(rel).replace("\\", "/")
        entry = contract_entry(project, rel_norm)
        if entry is None and (rel_norm.startswith(CONTRACT_PATH_HINT) or "/contracts/" in rel_norm):
            err("P104", loc, "契约类输入未在项目 contracts 登记表冻结，视为未冻结")
        if entry is not None:
            registered = str(entry.get("sha256", "")).lower()
            actual = sha256_file(abs_path).lower()
            if registered != actual:
                err("P105", loc, f"契约漂移: 登记 sha256={registered[:12]}… 实际={actual[:12]}…，须重新校验冻结后派发")

    for rel in task.get("outputs", []) or []:
        if safe_join(root, str(rel)) is None:
            err("P103", f"{pid}.{task_id}.outputs[{rel}]", "outputs 路径逃逸出项目 root_dir 或为绝对路径")

    return {"task_id": task_id, "project": pid, "verdict": "OK" if not errs else "REFUSED",
            "errors": errs, "registered_contracts": sorted(registered_contract_paths)}


def main():
    ap = argparse.ArgumentParser(description="派发前置检查")
    ap.add_argument("task_id")
    ap.add_argument("--ledger", default="tasks.json")
    ap.add_argument("--report")
    args = ap.parse_args()

    report = run_dispatch_check(args.task_id.upper(), args.ledger)
    if args.report:
        write_report(args.report, report)
    if report["verdict"] == "REFUSED":
        print(f"DISPATCH REFUSED: {report['task_id']} 共 {len(report['errors'])} 项未过前置检查")
        sys.exit(1)
    print(f"DISPATCH OK: {report['task_id']} 前置检查全部通过，可置 IN_PROGRESS")
    sys.exit(0)


if __name__ == "__main__":
    main()
