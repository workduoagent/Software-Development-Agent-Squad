"""契约变更审计：比对新旧契约，按 api-contract-spec.md 第七节分级。

用法: python diff.py <old.yaml> <new.yaml> [--report <diff-report.json>]
退出码: 0 无变更或纯增量 ADDITIVE; 2 检出 BREAKING_CHANGE（须总架构师拍板）; 1 输入错误。
"""
import argparse
import json
import sys

from common import deref, fail, iter_operations, load_contract, utc_now_iso


def flatten_schema(doc, schema, prefix, out, seen):
    """把 schema 展平为 {dotted.path: {type, required, enum}} 供逐字段比对。
    allOf 各层的 required 合并计入本层，数组元素路径以 [] 结尾。
    """
    ref = schema.get("$ref") if isinstance(schema, dict) else None
    if ref:
        if ref in seen:
            return
        seen = seen | {ref}
    schema = deref(doc, schema)
    if not isinstance(schema, dict):
        return
    merged_required = set()
    parts = list(schema.get("allOf") or []) + [schema]
    for part in parts:
        part = deref(doc, part)
        merged_required |= set(part.get("required") or [])
        for name, sub in (part.get("properties") or {}).items():
            key = f"{prefix}.{name}" if prefix else name
            sub_d = deref(doc, sub if isinstance(sub, dict) else {})
            out[key] = {
                "type": sub_d.get("type"),
                "required": name in merged_required,
                "enum": sub_d.get("enum"),
            }
            flatten_schema(doc, sub, key, out, seen)
        if part.get("items"):
            flatten_schema(doc, part["items"], prefix + "[]", out, seen)


def snapshot(doc):
    """提取契约快照: {op_key: {params, request, responses}}。"""
    snap = {}
    for p, method, op in iter_operations(doc):
        entry = {"params": {}, "request": {}, "responses": {}}
        for param in op.get("parameters") or []:
            param_d = deref(doc, param if isinstance(param, dict) else {})
            name = str(param_d.get("name", "?"))
            schema = deref(doc, param_d.get("schema") or {})
            entry["params"][f"{name}@{param_d.get('in', '?')}"] = {
                "type": schema.get("type"),
                "required": bool(param_d.get("required")),
                "enum": schema.get("enum"),
            }
        rb = op.get("requestBody")
        if isinstance(rb, dict):
            rb = deref(doc, rb)
            rb_schema = ((rb.get("content") or {}).get("application/json") or {}).get("schema") or {}
            flatten_schema(doc, rb_schema, "", entry["request"], set())
        for status, resp in (op.get("responses") or {}).items():
            resp = deref(doc, resp if isinstance(resp, dict) else {})
            fields = {}
            json_content = (resp.get("content") or {}).get("application/json") or {}
            if json_content.get("schema"):
                flatten_schema(doc, json_content["schema"], "", fields, set())
            entry["responses"][str(status)] = fields
        snap[f"{method.upper()} {p}"] = entry
    return snap


def classify(changes):
    breaking = [c for c in changes if c["classification"] == "BREAKING_CHANGE"]
    additive = [c for c in changes if c["classification"] == "ADDITIVE"]
    return breaking, additive


def change(desc, location, classification):
    return {"change": desc, "location": location, "classification": classification}


def compare_fields(old_f, new_f, loc, changes, side):
    """按 side 定级，同一变更在两侧方向相反：请求收紧必填是 BREAKING，响应提高保证是 ADDITIVE。"""
    for key, meta in old_f.items():
        if key not in new_f:
            changes.append(change(f"{'响应' if side == 'response' else '请求'}字段被删除: {key}", loc, "BREAKING_CHANGE"))
            continue
        new_meta = new_f[key]
        if meta["type"] is not None and new_meta["type"] is not None and meta["type"] != new_meta["type"]:
            changes.append(change(f"字段类型变更: {key} {meta['type']} -> {new_meta['type']}", loc, "BREAKING_CHANGE"))
        if meta["enum"] and new_meta["enum"] is not None:
            removed = set(map(str, meta["enum"])) - set(map(str, new_meta["enum"]))
            if removed:
                changes.append(change(f"枚举值删除: {key} 移除 {sorted(removed)}", loc, "BREAKING_CHANGE"))
        if side == "request":
            if not meta["required"] and new_meta["required"]:
                changes.append(change(f"请求新增必填约束: {key}", loc, "BREAKING_CHANGE"))
            elif meta["required"] and not new_meta["required"]:
                changes.append(change(f"请求必填放宽: {key}", loc, "ADDITIVE"))
        else:
            if meta["required"] and not new_meta["required"]:
                changes.append(change(f"响应字段不再保证返回: {key}", loc, "BREAKING_CHANGE"))
            elif not meta["required"] and new_meta["required"]:
                changes.append(change(f"响应字段升级为必返: {key}", loc, "ADDITIVE"))
    for key, meta in new_f.items():
        if key in old_f:
            continue
        if side == "request" and meta["required"]:
            changes.append(change(f"请求新增必填字段: {key}", loc, "BREAKING_CHANGE"))
        else:
            changes.append(change(f"新增{'响应' if side == 'response' else '可选请求'}字段: {key}", loc, "ADDITIVE"))


def run_diff(old_path, new_path):
    old_doc, new_doc = load_contract(old_path), load_contract(new_path)
    old_snap, new_snap = snapshot(old_doc), snapshot(new_doc)
    changes = []

    for op_key in old_snap:
        if op_key not in new_snap:
            changes.append(change("接口被删除", op_key, "BREAKING_CHANGE"))
    for op_key in new_snap:
        if op_key not in old_snap:
            changes.append(change("新增接口", op_key, "ADDITIVE"))

    for op_key in set(old_snap) & set(new_snap):
        old_op, new_op = old_snap[op_key], new_snap[op_key]
        for pk, meta in old_op["params"].items():
            if pk not in new_op["params"]:
                changes.append(change(f"参数被删除: {pk}", op_key, "BREAKING_CHANGE"))
            elif meta["type"] != new_op["params"][pk]["type"]:
                changes.append(change(f"参数类型变更: {pk}", op_key, "BREAKING_CHANGE"))
            elif not meta["required"] and new_op["params"][pk]["required"]:
                changes.append(change(f"参数升级为必填: {pk}", op_key, "BREAKING_CHANGE"))
        for pk, meta in new_op["params"].items():
            if pk not in old_op["params"]:
                cls = "BREAKING_CHANGE" if meta["required"] else "ADDITIVE"
                changes.append(change(f"新增参数: {pk}", op_key, cls))
        compare_fields(old_op["request"], new_op["request"], op_key, changes, "request")
        for status, fields in old_op["responses"].items():
            if status not in new_op["responses"]:
                changes.append(change(f"响应 {status} 被删除", op_key, "BREAKING_CHANGE"))
            else:
                compare_fields(fields, new_op["responses"][status], f"{op_key} responses.{status}", changes, "response")
        for status in new_op["responses"]:
            if status not in old_op["responses"]:
                changes.append(change(f"新增响应 {status}", op_key, "ADDITIVE"))

    breaking, additive = classify(changes)
    return {
        "old": old_path,
        "new": new_path,
        "generated_at": utc_now_iso(),
        "summary": {"breaking": len(breaking), "additive": len(additive)},
        "changes": changes,
    }


def main():
    ap = argparse.ArgumentParser(description="契约兼容性 Diff 审计")
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--report", help="diff 报告 JSON 输出路径")
    args = ap.parse_args()

    try:
        report = run_diff(args.old, args.new)
    except FileNotFoundError as exc:
        fail(f"契约文件不存在: {exc.filename}")

    for c in report["changes"]:
        print(f"[{c['classification']}] {c['location']}: {c['change']}")
    s = report["summary"]
    if s["breaking"]:
        print(f"DIFF VERDICT: BREAKING_CHANGE x{s['breaking']}（须总架构师拍板并留存决策结论），另有 ADDITIVE x{s['additive']}")
        verdict = 2
    elif s["additive"]:
        print(f"DIFF VERDICT: 纯增量 ADDITIVE x{s['additive']}，可重新校验冻结")
        verdict = 0
    else:
        print("DIFF VERDICT: NO CHANGES")
        verdict = 0

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已写入: {args.report}")
    sys.exit(verdict)


if __name__ == "__main__":
    main()
