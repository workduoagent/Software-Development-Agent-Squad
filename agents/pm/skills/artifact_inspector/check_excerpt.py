"""摘录回溯核验：提测报告里引用的日志摘录必须能在落盘日志原文中找到。对应 review-criteria 一节 2 后半句。

用法:
  python check_excerpt.py <log> --excerpt "摘录原文" [--excerpt ...] [--report r.json]
  python check_excerpt.py <log> --from-report <报告.md>   # 取报告所有 fenced code block 逐块回溯
匹配为精确子串；精确不中时做空白归一化（换行/连续空白折叠为单空格）再比一次。
退出码: 0 全部命中; 1 任一未命中; 2 文件缺失。
检查码 A030-A031 定义见 SKILL.md。报告侧改写措辞（非原文摘录）检测不出，属人工对账范围。
"""
import argparse
import os
import re
import sys

from common import print_check, read_text, strip_ansi, usage, write_report

CODEBLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)


def norm_ws(text):
    return " ".join(text.split())


def check_one(log_path, excerpts, results):
    haystack_raw = strip_ansi(read_text(log_path))
    haystack_norm = norm_ws(haystack_raw)
    missing = 0
    for i, excerpt in enumerate(excerpts):
        loc = f"{log_path}#excerpt{i}"
        if excerpt.strip() and excerpt in haystack_raw:
            print_check("A000", "INFO", loc, "精确命中")
            results.append({"excerpt": excerpt[:80], "match": "EXACT"})
        elif norm_ws(excerpt) and norm_ws(excerpt) in haystack_norm:
            print_check("A031", "WARN", loc, "空白归一化后命中，摘录排版与日志原始换行不一致")
            results.append({"excerpt": excerpt[:80], "match": "NORMALIZED"})
        else:
            print_check("A030", "ERROR", loc, "摘录在日志原文中找不到，涉嫌裁剪或伪造")
            results.append({"excerpt": excerpt[:80], "match": "MISSING"})
            missing += 1
    return missing


def main():
    ap = argparse.ArgumentParser(description="日志摘录回溯核验")
    ap.add_argument("log")
    ap.add_argument("--excerpt", action="append", default=[])
    ap.add_argument("--from-report", dest="report_file")
    ap.add_argument("--report", dest="json_out")
    args = ap.parse_args()

    if not os.path.isfile(args.log):
        usage(f"日志不存在: {args.log}")

    excerpts = list(args.excerpt)
    if args.report_file:
        if not os.path.isfile(args.report_file):
            usage(f"提测报告不存在: {args.report_file}")
        blocks = CODEBLOCK_RE.findall(read_text(args.report_file))
        for b in blocks:
            s = b.strip()
            # 只回溯像日志行的代码块（含时间戳/等号横幅/结果汇总特征），纯目录清单块跳过
            if re.search(r"passed|failed|error|exit|====|Tests run", s, re.I):
                excerpts.append(s)
    if not excerpts:
        usage("至少提供一条 --excerpt 或含日志摘录的 --from-report")

    results = []
    missing = check_one(args.log, excerpts, results)
    if args.json_out:
        write_report(args.json_out, {"log": args.log, "excerpts": results})
    if missing:
        print(f"EXCERPTS MISSING: {missing}/{len(excerpts)} 条摘录无法回溯到日志原文")
        sys.exit(1)
    print(f"EXCERPTS VERIFIED: {len(excerpts)} 条摘录全部可在日志原文回溯")
    sys.exit(0)


if __name__ == "__main__":
    main()
