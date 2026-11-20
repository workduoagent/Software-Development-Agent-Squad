"""状态流转与记账：按软件团队知识库 任务状态机.md 的合法边流转，REJECTED 强制证据落账，原子写回 tasks.json。

用法: python transition.py <TASK-ID> <TO_STATUS> [--ledger tasks.json]
        REJECTED 必带: --reason "..." --evidence "路径或摘录"（可多次）
        ACCEPTED 建议带: --log "验收摘要"（review-criteria 四节，缺则 WARN）
        BLOCKED 建议带: --log "阻塞原因与等待项"
退出码: 0 流转成功; 1 非法流转或证据缺失（不写账）; 2 参数/定位失败;
        3 流转已落账，但同一原因打回达到报警红线（PM 须中断并向用户报警）。
检查码 P3xx 定义见 SKILL.md。
"""
import argparse
import sys

from common import (ALLOWED_TRANSITIONS, STATUSES, find_task, load_ledger,
                    print_check, utc_now_iso, usage, write_ledger)


def append_rejection(task, reason, evidence):
    history = task.setdefault("rejection_history", [])
    rounds = [r.get("round", 0) for r in history if isinstance(r, dict)]
    entry = {
        "round": max(rounds or [0]) + 1,
        "rejected_at": utc_now_iso(),
        "reason": reason,
        "evidence": list(evidence),
    }
    history.append(entry)
    same = sum(1 for r in history if isinstance(r, dict) and r.get("reason") == reason)
    return entry, same


def run_transition(task_id, to_status, ledger_path, reason=None, evidence=(), log=None):
    ledger = load_ledger(ledger_path)
    project, task = find_task(ledger, task_id)
    pid = project["project_id"]
    loc = f"{pid}.{task_id}"
    frm = task.get("status")

    if to_status not in STATUSES:
        usage(f"未知状态 {to_status!r}，合法值: {sorted(STATUSES)}")
    if (frm, to_status) not in ALLOWED_TRANSITIONS:
        print_check("P301", "ERROR", loc, f"非法流转 {frm} -> {to_status}（任务状态机.md 未定义该边）")
        return None, "非法流转，未写账本"

    if to_status == "REJECTED":
        if not reason or not evidence:
            print_check("P302", "ERROR", loc, "REJECTED 必须携带 --reason 与至少一条 --evidence（打回证据强制）")
            return None, "证据缺失，未写账本"

    alarm = False
    task["status"] = to_status
    note = log
    if to_status == "REJECTED":
        entry, same_reason = append_rejection(task, reason, evidence)
        if same_reason == 2:
            print_check("P303", "WARN", loc, f"同一原因已第 {same_reason} 次打回：返工第三轮前先与用户对齐判据")
        elif same_reason >= 3:
            print_check("P303", "ALARM", loc,
                        f"同一原因打回超过 2 次（第 {same_reason} 次），触发报警红线：立即中断并向总架构师求助")
            alarm = True
        note = f"round={entry['round']} reason={reason}"
    if to_status == "ACCEPTED":
        task["accepted_at"] = utc_now_iso()
        if not note:
            print_check("P304", "WARN", loc, "ACCEPTED 建议附 --log 验收摘要（review-criteria 四节落账要求）")
    if to_status == "BLOCKED" and not note:
        print_check("P305", "WARN", loc, "BLOCKED 建议以 --log 写明等待何种决策或外部输入")

    if note:
        prev = task.get("verification_log", "")
        stamp = utc_now_iso()
        task["verification_log"] = f"{prev}\n{stamp}: {note}".strip() if prev else f"{stamp}: {note}"

    ledger["updated_at"] = utc_now_iso()
    write_ledger(ledger, ledger_path)
    msg = f"{loc}: {frm} -> {to_status} 已落账 {ledger_path}"
    return alarm, msg


def main():
    ap = argparse.ArgumentParser(description="任务状态流转与记账")
    ap.add_argument("task_id")
    ap.add_argument("to_status")
    ap.add_argument("--ledger", default="tasks.json")
    ap.add_argument("--reason")
    ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--log", dest="log", help="验收/阻塞摘要，写入 verification_log")
    args = ap.parse_args()

    alarm, msg = run_transition(args.task_id.upper(), args.to_status.upper(), args.ledger,
                                reason=args.reason, evidence=args.evidence, log=args.log)
    if msg.startswith("非法") or msg.startswith("证据"):
        print(f"TRANSITION REFUSED: {msg}")
        sys.exit(1)
    print(f"TRANSITION OK {msg}")
    if alarm:
        print("ALARM: 报警红线命中，PM 必须中断本轮执行并向用户汇报（任务状态机.md 打回红线）")
        sys.exit(3)
    sys.exit(0)


if __name__ == "__main__":
    main()
