"""账本校验：软件团队知识库 任务字段标准.json 的 jsonschema 校验加账本级不变量（跨任务唯一性、状态字段一致性）。

用法: python validate.py [tasks.json] [--schema 软件团队知识库/任务字段标准.json] [--report r.json]
退出码: 0 无 ERROR; 1 有 ERROR; 2 账本或 schema 读不到。
检查码 P0xx 定义见 SKILL.md。
"""
import argparse
import json
import os
import sys

from common import (SEMVER_RE, SHA256_RE, TASK_ID_RE, UTC_ISO_RE, print_check,
                    write_report)

try:
    from jsonschema import Draft202012Validator
except ImportError:
    req = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    print(f"FAIL: 缺少依赖 jsonschema，请先 python -m pip install -r {req}")
    sys.exit(2)


def check_ledger_top(data, errs, warns, loc):
    if data.get("version") != "1.0.0":
        warns.append((f"{loc}:version", f"账本 version={data.get('version')!r}，当前协议为 1.0.0"))
        print_check("P001", "WARN", f"{loc}:version", f"version={data.get('version')!r}")
    if not UTC_ISO_RE.match(str(data.get("updated_at", ""))):
        errs.append(f"{loc}:updated_at 缺失或非 UTC(Z) 时间")
        print_check("P001", "ERROR", f"{loc}:updated_at", "缺失或非 UTC(Z) 时间")


def check_contracts(project, idx, errs, warns):
    pid = project.get("project_id", f"projects[{idx}]")
    for i, c in enumerate(project.get("contracts", []) or []):
        loc = f"{pid}.contracts[{i}]"
        if not isinstance(c, dict):
            errs.append(f"{loc}: 契约登记条目必须是对象")
            print_check("P002", "ERROR", loc, "条目不是对象")
            continue
        for field in ("path", "version", "sha256", "frozen_at"):
            if not c.get(field):
                errs.append(f"{loc}.{field}: 缺登记字段")
                print_check("P002", "ERROR", f"{loc}.{field}", "缺登记字段")
        if c.get("version") and not SEMVER_RE.match(str(c["version"])):
            errs.append(f"{loc}.version: 非语义化版本 {c['version']!r}")
            print_check("P002", "ERROR", f"{loc}.version", f"非语义化版本 {c['version']!r}")
        if c.get("sha256") and not SHA256_RE.match(str(c["sha256"])):
            errs.append(f"{loc}.sha256: 非 64 位十六进制")
            print_check("P002", "ERROR", f"{loc}.sha256", "非 64 位十六进制指纹")


def check_project_shape(project, idx, seen_pid, seen_root, errs, warns):
    loc = f"projects[{idx}]"
    if not isinstance(project, dict):
        errs.append(f"{loc}: 项目必须是对象")
        print_check("P003", "ERROR", loc, "项目不是对象")
        return
    for field in ("project_id", "project_name", "root_dir"):
        if not project.get(field):
            errs.append(f"{loc}.{field}: 缺必填字段")
            print_check("P003", "ERROR", f"{loc}.{field}", "缺必填字段")
    if not isinstance(project.get("tasks"), list):
        errs.append(f"{loc}.tasks: 必须是数组")
        print_check("P003", "ERROR", f"{loc}.tasks", "必须是数组")
    if not isinstance(project.get("contracts"), list):
        warns.append((f"{loc}.contracts", "缺 contracts 数组，按无冻结契约处理"))
        print_check("P003", "WARN", f"{loc}.contracts", "缺 contracts 数组")
        return
    pid = project.get("project_id")
    if pid in seen_pid:
        errs.append(f"{loc}: project_id 重复 {pid!r}")
        print_check("P004", "ERROR", f"{loc}:project_id", f"重复 {pid!r}")
    seen_pid.add(pid)
    root = os.path.normpath(str(project.get("root_dir", "")))
    if root in seen_root:
        errs.append(f"{loc}: root_dir 指向同一物理目录 {root!r}，破坏多项目隔离")
        print_check("P005", "ERROR", f"{loc}:root_dir", f"与其他项目指向同一目录 {root!r}")
    seen_root.add(root)


def schema_errors_of(task, validator, tid):
    for e in sorted(validator.iter_errors(task), key=lambda x: list(x.path)):
        path = ".".join(str(x) for x in e.absolute_path)
        yield (f"{tid}.{path}" if path else str(tid)), e.message


def check_task_semantics(task, pid, prefix_map, seen_ids, errs, warns):
    tid = task.get("task_id", "?")
    loc = f"{pid}.{tid}"
    if TASK_ID_RE.match(str(tid)):
        prefix = tid.rsplit("-", 1)[0]
        owner = prefix_map.setdefault(prefix, pid)
        if owner != pid:
            errs.append(f"{loc}: 项目前缀 {prefix} 已被项目 {owner} 占用，全账本前缀须唯一")
            print_check("P006", "ERROR", loc, f"前缀 {prefix} 与项目 {owner} 冲突")
        elif prefix.lower() not in str(pid).lower():
            warns.append((f"{loc}:task_id", f"前缀 {prefix} 与 project_id {pid} 无语义关联，确认是否串项目"))
            print_check("P006", "WARN", loc, f"前缀 {prefix} 与 project_id 无语义关联")
    if tid in seen_ids:
        errs.append(f"{loc}: task_id 全账本重复")
        print_check("P007", "ERROR", loc, "task_id 重复")
    seen_ids.add(tid)

    status = task.get("status")
    if "accepted_at" in task:
        if status != "ACCEPTED":
            errs.append(f"{loc}.accepted_at: status={status} 不允许存在 accepted_at")
            print_check("P008", "ERROR", f"{loc}.accepted_at", f"status={status} 不应携带")
        elif not UTC_ISO_RE.match(str(task["accepted_at"])):
            errs.append(f"{loc}.accepted_at: 非 UTC(Z) 时间")
            print_check("P008", "ERROR", f"{loc}.accepted_at", "非 UTC(Z) 时间")
    elif status == "ACCEPTED":
        warns.append((f"{loc}.accepted_at", "ACCEPTED 缺 accepted_at，落账要求 UTC 完成时间"))
        print_check("P008", "WARN", loc, "ACCEPTED 缺 accepted_at")

    rounds = []
    for i, r in enumerate(task.get("rejection_history", []) or []):
        if isinstance(r, dict):
            rounds.append(r.get("round"))
    numeric = [x for x in rounds if isinstance(x, int)]
    if numeric != sorted(numeric) or len(set(numeric)) != len(numeric):
        errs.append(f"{loc}.rejection_history: round 非严格递增 {rounds}")
        print_check("P009", "ERROR", f"{loc}.rejection_history", f"round 非严格递增 {rounds}")


def run_validate(ledger_path, schema_path):
    from common import load_ledger
    data = load_ledger(ledger_path)
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    validator = Draft202012Validator(schema)

    errs, warns = [], []
    print_check("P000", "INFO", ledger_path, f"projects={len(data['projects'])}")
    check_ledger_top(data, errs, warns, "(root)")

    seen_pid, seen_root, seen_ids, prefix_map = set(), set(), set(), {}
    for idx, project in enumerate(data["projects"]):
        check_project_shape(project, idx, seen_pid, seen_root, errs, warns)
        if not isinstance(project, dict):
            continue
        pid = project.get("project_id", f"projects[{idx}]")
        check_contracts(project, idx, errs, warns)
        for task in project.get("tasks", []) or []:
            if not isinstance(task, dict):
                errs.append(f"{pid}.tasks[]: 任务必须是对象")
                print_check("P010", "ERROR", pid, "任务条目不是对象")
                continue
            tid = str(task.get("task_id", f"tasks[{len(project['tasks']) - 1}]"))
            for path_, msg in schema_errors_of(task, validator, tid):
                errs.append(f"{pid}.{path_}: {msg}")
                print_check("P010", "ERROR", f"{pid}.{path_}", msg)
            check_task_semantics(task, pid, prefix_map, seen_ids, errs, warns)

    return {"ledger": ledger_path, "summary": {"errors": len(errs), "warnings": len(warns)},
            "errors": errs, "warnings": warns}


def main():
    ap = argparse.ArgumentParser(description="任务账本校验")
    ap.add_argument("ledger", nargs="?", default="tasks.json")
    ap.add_argument("--schema", default=os.path.join("软件团队知识库", "任务字段标准.json"))
    ap.add_argument("--report", help="校验报告 JSON 输出路径")
    args = ap.parse_args()

    if not os.path.isfile(args.schema):
        usage(f"schema 不存在: {args.schema}（请在仓库根目录运行或显式 --schema）")
    report = run_validate(args.ledger, args.schema)
    if args.report:
        write_report(args.report, report)
    s = report["summary"]
    if s["errors"]:
        print(f"LEDGER FAILED ({s['errors']} errors, {s['warnings']} warnings)")
        sys.exit(1)
    print(f"LEDGER PASSED (0 errors, {s['warnings']} warnings)")
    sys.exit(0)


if __name__ == "__main__":
    from common import usage
    main()
