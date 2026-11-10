"""契约 Lint：按 docs/02-protocols/api-contract-spec.md 第六节逐项机检。

用法: python lint.py <contract.yaml> [--report <report.json>]
退出码: 0 通过（可含 WARN）; 1 存在 ERROR，或契约文件读不到。
"""
import argparse
import json
import sys

from common import (
    SEMVER, ID_FIELD, deref, fail, first_example_body, get_json_content,
    is_2xx, is_error_status, is_result_wrapped, iter_operations, load_contract,
    utc_now_iso,
)


def run_syntax_check(doc, errors):
    try:
        from openapi_spec_validator import validate
        validate(doc)
    except ImportError:
        errors.append(item("E100", "openapi-spec-validator 未安装，无法执行语法校验（pip install -r requirements.txt）", "-"))
    except Exception as exc:  # noqa: BLE001 - 汇总校验库抛出的所有违规
        msg = str(exc).strip().splitlines()[0][:300] if str(exc).strip() else exc.__class__.__name__
        errors.append(item("E100", f"OpenAPI 语法校验失败: {msg}", "document"))


def item(check, message, location, level="ERROR"):
    return {"check": check, "level": level, "location": location, "message": message}


def run_lint(path):
    doc = load_contract(path)
    errors, warnings = [], []
    run_syntax_check(doc, errors)

    # E001 版本闸门：只收 OpenAPI 3.1.x
    if not str(doc.get("openapi", "")).startswith("3.1"):
        errors.append(item("E001", f"openapi 版本必须为 3.1.x，当前: {doc.get('openapi', '(缺失)')}", "openapi"))

    # E002 info.title 非空、info.version 合法 semver（freeze 锁文件以此作版本号）
    info = doc.get("info") if isinstance(doc.get("info"), dict) else {}
    if not isinstance(info.get("title"), str) or not info.get("title"):
        errors.append(item("E002", "info.title 缺失", "info.title"))
    version = str(info.get("version", ""))
    if not SEMVER.match(version):
        errors.append(item("E002", f"info.version 缺失或非 semver: {version or '(缺失)'}", "info.version"))

    # E005 Result 统一响应壳：code integer、msg string、data 必须存在
    schemas = (doc.get("components") or {}).get("schemas") or {}
    result = schemas.get("Result")
    if not isinstance(result, dict):
        errors.append(item("E005", "components.schemas.Result 未定义", "components.schemas.Result"))
    else:
        props = result.get("properties") or {}
        if (props.get("code") or {}).get("type") != "integer":
            errors.append(item("E005", "Result.code 必须为 integer", "components.schemas.Result.code"))
        if (props.get("msg") or {}).get("type") != "string":
            errors.append(item("E005", "Result.msg 必须为 string", "components.schemas.Result.msg"))
        if "data" not in props:
            errors.append(item("E005", "Result 缺少 data 字段", "components.schemas.Result.data"))

    # E006 错误码登记表：条目字段合法，登记的 code 集合供后续样例比对
    registry = doc.get("x-error-codes")
    registered_codes = set()
    if not isinstance(registry, list) or not registry:
        errors.append(item("E006", "顶层 x-error-codes 登记表缺失或为空", "x-error-codes"))
    else:
        for i, entry in enumerate(registry):
            entry = entry if isinstance(entry, dict) else {}
            loc = f"x-error-codes[{i}]"
            for field, typ in (("code", int), ("http_status", int), ("message", str), ("trigger", str)):
                if not isinstance(entry.get(field), typ):
                    errors.append(item("E006", f"错误码条目缺少合法 {field}（类型 {typ.__name__}）", loc))
            if isinstance(entry.get("code"), int):
                registered_codes.add(entry["code"])

    # 逐 operation 检查：seen_error_codes 要在此过程中收齐全量样例 code，E011 覆盖率判定依赖它
    seen_op_ids = {}
    seen_error_codes = set()
    for p, method, op in iter_operations(doc):
        loc_op = f"{method.upper()} {p}"

        # E003 operationId 必填且全局唯一
        op_id = op.get("operationId")
        if not isinstance(op_id, str) or not op_id:
            errors.append(item("E003", "缺少 operationId", loc_op))
        elif op_id in seen_op_ids:
            errors.append(item("E003", f"operationId 重复（与 {seen_op_ids[op_id]} 冲突）", loc_op))
        else:
            seen_op_ids[op_id] = loc_op

        responses = op.get("responses") if isinstance(op.get("responses"), dict) else {}
        if not responses:
            errors.append(item("E004", "缺少 responses 定义", loc_op))

        has_2xx = has_error_resp = False
        for status, resp in responses.items():
            resp = resp if isinstance(resp, dict) else {}
            loc_resp = f"{loc_op} responses.{status}"
            json_content = get_json_content(resp)

            if is_2xx(status):
                has_2xx = True
                # E004 2xx 必须有 application/json 且 schema 包 Result
                schema = (json_content or {}).get("schema")
                if json_content is None:
                    errors.append(item("E004", "2xx 响应缺少 application/json content", loc_resp))
                elif not is_result_wrapped(schema):
                    errors.append(item("E004", "2xx 响应 schema 必须 $ref Result 或以 allOf 组合 Result", loc_resp))
                # E007 2xx 必须给 Mock 样例，否则 mock_gen 只能退回 schema 构造的假数据
                if json_content is not None and first_example_body(json_content) is None:
                    errors.append(item("E007", "2xx 响应缺少 Mock 样例（examples/example）", loc_resp))

            if is_error_status(status):
                has_error_resp = True
                body = first_example_body(json_content) if json_content else None
                if json_content is not None and body is None:
                    warnings.append(item("W003", "错误响应缺少样例报文", loc_resp, "WARN"))
                if isinstance(body, dict) and body.get("code") is not None:
                    if isinstance(body["code"], int):
                        seen_error_codes.add(body["code"])
                    # registered_codes 为空说明登记表本身已报 E006，逐条比对再报只会刷屏
                    if registered_codes and body["code"] not in registered_codes:
                        errors.append(item("E006", f"错误样例 code={body['code']} 未在 x-error-codes 登记", loc_resp))

        if responses and not has_2xx:
            errors.append(item("E004", "缺少 2xx 成功响应", loc_op))
        # 错误面按 is_error_status 认定，4XX/5XX/default 任一存在即算已定义
        if responses and not has_error_resp:
            errors.append(item("E006", "缺少 4xx/5xx 错误响应定义", loc_op))

        # E008 requestBody / parameters 必须有 schema；W001 字符串约束；W002 分页命名
        rb = op.get("requestBody")
        if isinstance(rb, dict):
            rb = deref(doc, rb)
            rb_json = (rb.get("content") or {}).get("application/json") or {}
            if not rb_json.get("schema"):
                errors.append(item("E008", "requestBody 缺少 application/json schema", f"{loc_op} requestBody"))
            else:
                walk_request_schema(doc, rb_json["schema"], f"{loc_op} requestBody", warnings)

        for i, param in enumerate(op.get("parameters") or []):
            param = deref(doc, param) if isinstance(param, dict) else {}
            loc_param = f"{loc_op} parameters[{i}]({param.get('name', '?')})"
            if not param.get("schema") and not param.get("content"):
                errors.append(item("E008", "parameter 缺少 schema/content", loc_param))
            if str(param.get("name", "")) in {"page", "current", "pageNumber", "page_number", "offset", "limit", "size", "page_size", "pagesize"}:
                warnings.append(item("W002", f"分页参数 {param.get('name')} 应统一为 pageNum/pageSize", loc_param, "WARN"))

    # E011 错误码样例覆盖率：登记表内每个 code 必须被至少一个错误响应样例使用
    if isinstance(registry, list):
        for i, entry in enumerate(registry):
            entry = entry if isinstance(entry, dict) else {}
            code = entry.get("code")
            if isinstance(code, int) and code not in seen_error_codes:
                errors.append(item("E011", f"登记错误码 {code} 未被任何错误响应样例使用（覆盖率不足 100%）", f"x-error-codes[{i}]"))

    # E009 ID 字段字符串化：只遍历 components.schemas，requestBodies 里的内联 schema 不在覆盖范围
    for name, schema in schemas.items():
        walk_id_fields(doc, schema, f"components.schemas.{name}", errors, set())

    report = {
        "contract": path,
        "generated_at": utc_now_iso(),
        "summary": {"errors": len(errors), "warnings": len(warnings)},
        "errors": errors,
        "warnings": warnings,
    }
    return report


def walk_request_schema(doc, schema, loc, warnings, _prefix="", _seen=None):
    """W001：字符串入参缺 format/pattern/enum/maxLength 即告警，递归 properties/allOf/items。
    seen 按当前路径复制而非全局共享，只截路径上已展开过的 $ref（环），菱形复用仍会展开。
    """
    _seen = _seen if _seen is not None else set()
    ref = schema.get("$ref") if isinstance(schema, dict) else None
    if ref:
        if ref in _seen:
            return
        _seen = _seen | {ref}
    schema = deref(doc, schema)
    if not isinstance(schema, dict):
        return
    for part in schema.get("allOf") or []:
        walk_request_schema(doc, part, loc, warnings, _prefix, _seen)
    for name, sub in (schema.get("properties") or {}).items():
        sub_d = deref(doc, sub if isinstance(sub, dict) else {})
        path = f"{_prefix}.{name}" if _prefix else name
        if sub_d.get("type") == "string" and not any(
            k in sub_d for k in ("format", "pattern", "enum", "maxLength")
        ):
            warnings.append(item("W001", f"字符串入参 {path} 缺少 format/pattern/enum/maxLength 约束", loc, "WARN"))
        walk_request_schema(doc, sub, loc, warnings, path, _seen)
    if schema.get("items"):
        walk_request_schema(doc, schema["items"], loc, warnings, _prefix + "[]", _seen)


def walk_id_fields(doc, schema, loc, errors, seen):
    """E009：id/*Id/*_id 命名（口径见 common.ID_FIELD）的字段必须 type: string，避免前端精度丢失。"""
    ref = schema.get("$ref") if isinstance(schema, dict) else None
    if ref:
        if ref in seen:
            return
        seen = seen | {ref}
    schema = deref(doc, schema)
    if not isinstance(schema, dict):
        return
    for part in schema.get("allOf") or []:
        walk_id_fields(doc, part, loc, errors, seen)
    for name, sub in (schema.get("properties") or {}).items():
        sub_d = deref(doc, sub if isinstance(sub, dict) else {})
        if ID_FIELD.search(name) and sub_d.get("type") != "string":
            errors.append(item("E009", f"ID 字段 {name} 必须 type: string，当前: {sub_d.get('type', '(未声明)')}", f"{loc}.{name}"))
        walk_id_fields(doc, sub, f"{loc}.{name}", errors, seen)
    if schema.get("items"):
        walk_id_fields(doc, schema["items"], loc + "[]", errors, seen)


def print_report(report):
    for e in report["errors"]:
        print(f"[{e['check']}] ERROR @ {e['location']}: {e['message']}")
    for w in report["warnings"]:
        print(f"[{w['check']}] WARN  @ {w['location']}: {w['message']}")
    s = report["summary"]
    verdict = "LINT PASSED" if s["errors"] == 0 else "LINT FAILED"
    print(f"{verdict}: {s['errors']} errors, {s['warnings']} warnings ({report['contract']})")


def main():
    ap = argparse.ArgumentParser(description="OpenAPI 3.1 契约 Lint")
    ap.add_argument("contract")
    ap.add_argument("--report", help="lint 报告 JSON 输出路径")
    args = ap.parse_args()

    try:
        report = run_lint(args.contract)
    except FileNotFoundError:
        fail(f"契约文件不存在: {args.contract}")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"报告已写入: {args.report}")
    print_report(report)
    sys.exit(0 if report["summary"]["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
