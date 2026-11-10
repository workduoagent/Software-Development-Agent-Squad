"""Mock 报文生成：从契约提取标准 Mock JSON，供前端 mock 体系使用。

用法: python mock_gen.py <contract.yaml> [--out <mocks.json>] [--operation-id <id>]
取数优先级: responses.examples > responses.example > schema 递归构造（含 schema.example/enum/default/format）。
退出码: 0 成功; 1 输入错误或未匹配到任何报文。
"""
import argparse
import json
import sys

from common import deref, fail, first_example_body, get_json_content, iter_operations, load_contract, utc_now_iso

FORMAT_SAMPLES = {
    "date-time": "2026-01-01T00:00:00Z",
    "date": "2026-01-01",
    "email": "user@example.com",
    "uri": "https://example.com",
    "uuid": "00000000-0000-0000-0000-000000000000",
}


def sample_from_schema(doc, schema, seen=None):
    """兜底样例构造：example/examples 优先，其次 allOf 合并（oneOf/anyOf 取首项）、enum 首值、default、类型零值。
    $ref 成环返回 None；数组按 minItems（下限 1）造元素，同组元素是同一对象引用，序列化后才成多份。
    """
    seen = seen if seen is not None else set()
    ref = schema.get("$ref") if isinstance(schema, dict) else None
    if ref:
        if ref in seen:
            return None
        seen = seen | {ref}
    schema = deref(doc, schema if isinstance(schema, dict) else {})
    if not isinstance(schema, dict) or not schema:
        return None

    if "example" in schema:
        return schema["example"]
    if isinstance(schema.get("examples"), list) and schema["examples"]:
        return schema["examples"][0]

    for combinator in ("allOf", "oneOf", "anyOf"):
        parts = schema.get(combinator)
        if isinstance(parts, list) and parts:
            if combinator == "allOf":
                merged = {}
                for part in parts:
                    val = sample_from_schema(doc, part, seen)
                    if isinstance(val, dict):
                        merged.update(val)
                    elif val is not None:
                        return val
                return merged or None
            return sample_from_schema(doc, parts[0], seen)

    if isinstance(schema.get("enum"), list) and schema["enum"]:
        return schema["enum"][0]
    if "default" in schema:
        return schema["default"]

    typ = schema.get("type")
    if typ == "object" or (typ is None and schema.get("properties")):
        return {
            name: sample_from_schema(doc, sub, seen)
            for name, sub in (schema.get("properties") or {}).items()
        }
    if typ == "array":
        items = schema.get("items") or {}
        count = max(int(schema.get("minItems") or 1), 1)
        return [sample_from_schema(doc, items, seen)] * count
    if typ == "string":
        return FORMAT_SAMPLES.get(schema.get("format"), "string")
    if typ == "integer":
        return 0
    if typ == "number":
        return 0.0
    if typ == "boolean":
        return True
    if typ == "null":
        return None
    return None


def run_mock_gen(contract_path, operation_id=None):
    doc = load_contract(contract_path)
    mocks = []
    for p, method, op in iter_operations(doc):
        op_id = op.get("operationId") or f"{method}_{p}"
        if operation_id and op_id != operation_id:
            continue
        for status, resp in (op.get("responses") or {}).items():
            resp = deref(doc, resp if isinstance(resp, dict) else {})
            json_content = get_json_content(resp)
            if json_content is None:
                continue
            body = first_example_body(json_content)
            source = "example"
            if body is None:
                body = sample_from_schema(doc, json_content.get("schema") or {})
                source = "schema"
            mocks.append({
                "operation_id": op_id,
                "method": method,
                "path": p,
                "status": int(status) if str(status).isdigit() else str(status),
                "source": source,
                "body": body,
            })
    return {
        "contract": contract_path,
        "generated_at": utc_now_iso(),
        "count": len(mocks),
        "mocks": mocks,
    }


def main():
    ap = argparse.ArgumentParser(description="契约 Mock 报文生成")
    ap.add_argument("contract")
    ap.add_argument("--out", help="输出 JSON 路径（缺省打印到 stdout）")
    ap.add_argument("--operation-id", help="仅生成指定 operationId 的报文")
    args = ap.parse_args()

    try:
        result = run_mock_gen(args.contract, args.operation_id)
    except FileNotFoundError:
        fail(f"契约文件不存在: {args.contract}")

    if not result["count"]:
        fail("未匹配到任何可生成的响应报文（检查 --operation-id 或契约内容）")

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        example_src = sum(1 for m in result["mocks"] if m["source"] == "example")
        print(f"MOCK GEN OK: {result['count']} 条报文（{example_src} 条来自契约样例，{result['count'] - example_src} 条由 Schema 构造）")
        print(f"已写入: {args.out}")
    else:
        print(text)
    sys.exit(0)


if __name__ == "__main__":
    main()
