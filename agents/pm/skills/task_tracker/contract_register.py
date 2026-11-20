"""契约冻结登记：核验 freeze.py 锁文件与物理契约 sha256 三方一致后，写入项目 contracts 登记表。

用法: python contract_register.py --project <project_id> --lock <contract.yaml.lock.json>
        [--ledger tasks.json] [--write]
      默认只核验并打印登记块（建议模式）；--write 才落账（覆盖旧版同路径条目，版本须递增）。
退出码: 0 核验通过; 1 核验失败（拒绝登记）; 2 参数/文件缺失。
检查码 P2xx 定义见 SKILL.md。
"""
import argparse
import json
import os
import re
import sys

from common import (SEMVER_RE, SHA256_RE, load_ledger, print_check,
                    project_root_abs, safe_join, sha256_file, utc_now_iso,
                    usage, write_ledger)


def semver_tuple(v):
    core = str(v).split("-")[0].split("+")[0]
    return tuple(int(x) for x in (core.split(".") + ["0", "0", "0"])[:3])


def resolve_contract(lock, ledger_path, project, ledger_rel):
    """依次尝试：账本内登记形态路径(root_dir 相对)、锁文件记录的冻结时路径。返回绝对路径或 None。"""
    root = project_root_abs(ledger_path, project)
    candidates = []
    if ledger_rel:
        candidates.append(safe_join(root, ledger_rel))
    lock_path = lock.get("contract", "")
    root_prefix = os.path.normpath(project.get("root_dir", ".")) + os.sep
    if str(lock_path).replace("\\", "/").startswith(root_prefix.replace("\\", "/")):
        candidates.append(safe_join(root, lock_path[len(root_prefix):]))
    else:
        candidates.append(os.path.normpath(lock_path))
    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand
    return None


def main():
    ap = argparse.ArgumentParser(description="契约冻结登记核验与落账")
    ap.add_argument("--project", required=True)
    ap.add_argument("--lock", required=True, help="freeze.py 产出的锁文件")
    ap.add_argument("--path", help="登记进 contracts 表的项目相对路径（缺省从锁文件推断）")
    ap.add_argument("--ledger", default="tasks.json")
    ap.add_argument("--write", action="store_true", help="核验通过后写入 contracts 登记表")
    args = ap.parse_args()

    if not os.path.isfile(args.lock):
        usage(f"锁文件不存在: {args.lock}")
    try:
        with open(args.lock, encoding="utf-8") as f:
            lock = json.load(f)
    except json.JSONDecodeError as e:
        print_check("P201", "ERROR", args.lock, f"锁文件不是合法 JSON: {e}")
        sys.exit(1)

    for field in ("contract", "version", "sha256", "frozen_at"):
        if not lock.get(field):
            print_check("P201", "ERROR", args.lock, f"锁缺字段 {field}，须由 freeze.py 重新产出")
            sys.exit(1)
    if not SHA256_RE.match(str(lock["sha256"])):
        print_check("P201", "ERROR", args.lock, "sha256 非 64 位十六进制")
        sys.exit(1)
    lint_summary = (lock.get("lint") or {})
    if int(lint_summary.get("errors", -1)) != 0:
        print_check("P202", "ERROR", args.lock, f"锁内 lint errors={lint_summary.get('errors')}，未过 lint 禁冻结")
        sys.exit(1)

    ledger = load_ledger(args.ledger)
    from common import find_project
    project = find_project(ledger, args.project)

    ledger_rel = args.path
    if ledger_rel is None:
        root_prefix = os.path.normpath(project.get("root_dir", ".")) + os.sep
        c = str(lock["contract"]).replace("\\", "/")
        r = root_prefix.replace("\\", "/")
        ledger_rel = c[len(r):] if c.startswith(r) else c

    abs_path = resolve_contract(lock, args.ledger, project, ledger_rel)
    if abs_path is None:
        print_check("P203", "ERROR", args.project, f"在 root_dir 与锁记录路径下都找不到契约物理文件: {lock['contract']}")
        sys.exit(1)

    actual = sha256_file(abs_path)
    if actual.lower() != str(lock["sha256"]).lower():
        print_check("P204", "ERROR", abs_path,
                    f"指纹不一致: 锁={str(lock['sha256'])[:12]}… 实际={actual[:12]}…，冻结后契约被改动，退回 architect 重新校验")
        sys.exit(1)
    print_check("P204", "INFO", abs_path, "锁文件与物理契约 sha256 一致")

    contracts = project.setdefault("contracts", [])
    rel_norm = str(ledger_rel).replace("\\", "/")
    existing = next((c for c in contracts if isinstance(c, dict)
                     and str(c.get("path", "")).replace("\\", "/") == rel_norm), None)
    new_version = str(lock["version"])
    if not SEMVER_RE.match(new_version):
        print_check("P205", "ERROR", rel_norm, f"契约版本非语义化: {new_version!r}")
        sys.exit(1)
    if existing is not None:
        old = str(existing.get("version", "0.0.0"))
        if semver_tuple(new_version) <= semver_tuple(old):
            print_check("P205", "ERROR", rel_norm,
                        f"版本未递增: 登记为 {old}，本次 {new_version}；变更须新大版本文件且版本递增")
            sys.exit(1)
        print_check("P205", "INFO", rel_norm, f"重新登记: {old} -> {new_version}（旧条目将被覆盖）")

    entry = {"path": rel_norm, "version": new_version,
             "sha256": str(lock["sha256"]).lower(), "frozen_at": str(lock["frozen_at"])}
    print("登记块（contracts 表条目）:")
    print(json.dumps(entry, ensure_ascii=False, indent=2))

    if not args.write:
        print("REGISTER VERIFIED: 未落账（加 --write 写入 contracts 登记表）")
        sys.exit(0)

    if existing is not None:
        contracts[contracts.index(existing)] = entry
    else:
        contracts.append(entry)
    ledger["updated_at"] = utc_now_iso()
    write_ledger(ledger, args.ledger)
    print(f"REGISTER OK: {args.project} contracts 已落账 {rel_norm}@{new_version}")
    sys.exit(0)


if __name__ == "__main__":
    main()
