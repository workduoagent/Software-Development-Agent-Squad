"""契约冻结：lint 通过后取 SHA-256 指纹，生成锁文件与 PM 登记块。

用法: python freeze.py <contract.yaml> [--report <lint-report.json>]
退出码: 0 冻结成功; 1 lint 有 ERROR 拒绝冻结，或契约文件读不到。
锁文件固定为 <contract.yaml>.lock.json，重复执行即重新冻结并覆盖旧锁。
"""
import argparse
import json
import sys

from common import fail, load_contract, sha256_file, utc_now_iso
from lint import print_report, run_lint


def main():
    ap = argparse.ArgumentParser(description="契约冻结与指纹锁定")
    ap.add_argument("contract")
    ap.add_argument("--report", help="lint 报告 JSON 输出路径")
    args = ap.parse_args()

    try:
        doc = load_contract(args.contract)
    except FileNotFoundError:
        fail(f"契约文件不存在: {args.contract}")

    report = run_lint(args.contract)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"lint 报告已写入: {args.report}")
    print_report(report)

    if report["summary"]["errors"] > 0:
        print("FREEZE REFUSED: lint 存在 ERROR，按 api-contract-spec.md 第六节拒绝冻结。")
        sys.exit(1)

    # 锁只存指纹不存内容：冻结后再改契约不会让旧锁自失效，校验方须自行重算 sha256 比对
    sha256 = sha256_file(args.contract)
    frozen_at = utc_now_iso()
    version = str((doc.get("info") or {}).get("version", "0.0.0"))

    lock = {
        "contract": args.contract,
        "version": version,
        "sha256": sha256,
        "frozen_at": frozen_at,
        "lint": report["summary"],
    }
    lock_path = args.contract + ".lock.json"
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump(lock, f, ensure_ascii=False, indent=2)

    registration = {"path": args.contract, "version": version, "sha256": sha256, "frozen_at": frozen_at}
    print(f"FREEZE OK: 锁文件已写入 {lock_path}")
    print("PM 登记块（核验后写入项目 contracts 登记表）:")
    print(json.dumps(registration, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
