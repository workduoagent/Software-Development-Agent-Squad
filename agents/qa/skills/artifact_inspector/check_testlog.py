"""测试日志核验：解析 pytest / vitest / jest / surefire 汇总行，判 100% 通过率并核对退出码留存。对应 review-criteria 一节 2 证据真实性。

用法: python check_testlog.py <log> [<log> ...] [--report r.json]
退出码: 0 全部 PASS; 1 任一 FAIL; 2 日志文件不存在。
检查码 A020-A025 定义见 SKILL.md。xfail/预期失败等形态未覆盖，见 tests/run_tests.md 盲区清单。
"""
import argparse
import os
import re
import sys

from common import print_check, read_text, strip_ansi, usage, write_report

BANNER_RE = re.compile(r"^=+.*=+$")
EXIT_CODE_RE = re.compile(
    r"(?:exit\s+(?:with\s+)?(?:code|status)|退出码|exited\s+with\s+(?:exit\s+)?code"
    r"|process\s+finished\s+with\s+exit\s+code)\s*[:=]?\s*(-?\d+)", re.I)


def count_of(label, text):
    m = re.search(rf"(\d+) {label}", text)
    return int(m.group(1)) if m else 0


def parse_pytest(text):
    lines = [ln for ln in text.splitlines()
             if BANNER_RE.match(ln.strip()) and re.search(r"passed|failed|error", ln)]
    if not lines:
        return None
    s = lines[-1]
    return {"framework": "pytest", "passed": count_of("passed", s),
            "failed": count_of("failed", s) + count_of("error", s),
            "skipped": count_of("skipped", s)}


def parse_vitest(text):
    lines = [ln for ln in text.splitlines() if re.match(r"^\s*Tests\s+\S", ln)]
    if not lines:
        return None
    s = lines[-1]
    return {"framework": "vitest", "passed": count_of("passed", s),
            "failed": count_of("failed", s) + count_of("error", s),
            "skipped": count_of("skipped", s)}


def parse_jest(text):
    lines = [ln for ln in text.splitlines() if re.match(r"^\s*Tests:", ln)]
    if not lines:
        return None
    s = lines[-1]
    return {"framework": "jest", "passed": count_of("passed", s),
            "failed": count_of("failed", s), "skipped": count_of("skipped", s)}


def parse_surefire(text):
    ms = re.findall(r"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)", text)
    if not ms:
        return None
    run, failures, errors, skipped = (int(x) for x in ms[-1])
    return {"framework": "maven-surefire", "passed": max(run - failures - errors - skipped, 0),
            "failed": failures + errors, "skipped": skipped}


PARSERS = (parse_pytest, parse_vitest, parse_jest, parse_surefire)


def check_one(log, results):
    text = strip_ansi(read_text(log))
    counts = None
    for parser in PARSERS:
        counts = parser(text)
        if counts:
            break
    errors = 0

    if counts is None:
        print_check("A020", "ERROR", log, "未识别到 pytest/vitest/jest/surefire 汇总行，日志不可信")
        results.append({"log": log, "verdict": "UNRECOGNIZED"})
        return 1
    if counts["failed"] > 0:
        print_check("A021", "ERROR", log, f"存在失败/错误用例: failed={counts['failed']}")
        errors += 1
    if counts["passed"] == 0:
        print_check("A022", "ERROR", log, "通过用例数为 0，等同没跑")
        errors += 1

    exit_hits = EXIT_CODE_RE.findall(text)
    if not exit_hits:
        print_check("A023", "ERROR", log, "日志中无退出码留存（review-criteria 要求含退出码）")
        errors += 1
    elif int(exit_hits[-1]) != 0:
        print_check("A024", "ERROR", log, f"退出码非 0: {exit_hits[-1]}")
        errors += 1

    if counts["skipped"] > 0:
        print_check("A025", "WARN", log, f"存在 {counts['skipped']} 个 skipped，按红线核对是否绕门")

    verdict = "PASS" if errors == 0 else "FAIL"
    print_check("A000", "INFO", log,
                f"{counts['framework']}: passed={counts['passed']} failed={counts['failed']} "
                f"skipped={counts['skipped']} exit_code={exit_hits[-1] if exit_hits else 'MISSING'}")
    results.append({"log": log, "verdict": verdict, **counts,
                    "exit_code": int(exit_hits[-1]) if exit_hits else None})
    return errors


def main():
    ap = argparse.ArgumentParser(description="测试日志核验")
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--report")
    args = ap.parse_args()

    for log in args.logs:
        if not os.path.isfile(log):
            usage(f"日志文件不存在: {log}")

    results, total_errors = [], 0
    for log in args.logs:
        total_errors += check_one(log, results)
    if args.report:
        write_report(args.report, {"logs": results, "errors": total_errors})
    if total_errors:
        print(f"TESTLOG FAILED: {len(args.logs)} 份日志中 {total_errors} 项 ERROR 判据命中")
        sys.exit(1)
    print(f"TESTLOG PASSED: {len(args.logs)} 份日志全部 100% 通过且退出码留存")
    sys.exit(0)


if __name__ == "__main__":
    main()
