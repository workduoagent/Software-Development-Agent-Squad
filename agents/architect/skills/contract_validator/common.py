"""contract_validator 共享工具：加载、$ref 解析、遍历、指纹、ID 字段识别。"""
import hashlib
import re
import sys

import yaml

# Windows 控制台默认 GBK，中文输出会乱码；统一切到 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
# ID 字段口径：裸 id、camelCase 的 *Id、snake_case 的 *_id 三种命名
ID_FIELD = re.compile(r"(?:^id$|[A-Za-z0-9]Id$|_id$)")
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}


def load_contract(path):
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        fail(f"{path} 不是合法的 YAML 映射（契约根节点必须是对象）")
    return doc


def fail(msg):
    """统一失败出口：打印 FAIL 行并以退出码 1 终止，调用方无需再抛异常。"""
    print(f"FAIL: {msg}")
    sys.exit(1)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def deref(doc, node, seen=None):
    """解析 $ref，只认本文档内的 #/ 引用；外链、断链和成环一律返回空 dict，由上层按缺失报错。"""
    seen = seen if seen is not None else set()
    while isinstance(node, dict) and isinstance(node.get("$ref"), str):
        ref = node["$ref"]
        if not ref.startswith("#/") or ref in seen:
            return {}
        seen = seen | {ref}
        cur = doc
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(cur, dict) or part not in cur:
                return {}
            cur = cur[part]
        node = cur
    return node if isinstance(node, dict) else {}


def iter_operations(doc):
    """yield (path, method, operation)，method 统一小写；paths 缺失或非映射时静默产出空序列。"""
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        return
    for p, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() in HTTP_METHODS and isinstance(op, dict):
                yield p, method.lower(), op


def is_2xx(status_key):
    """状态键容忍两种写法：数字 200-299 与通配 2XX。"""
    return (str(status_key).isdigit() and 200 <= int(status_key) < 300) or str(status_key).upper() == "2XX"


def is_error_status(status_key):
    """400 以上及 4XX/5XX/DEFAULT 通配都算错误面。"""
    k = str(status_key)
    if k.upper() in ("4XX", "5XX", "DEFAULT"):
        return True
    return k.isdigit() and int(k) >= 400


def get_json_content(response):
    """返回 2xx/错误响应的 application/json content 节点（无则 None）。"""
    content = response.get("content")
    if not isinstance(content, dict):
        return None
    return content.get("application/json")


def is_result_wrapped(schema):
    """2xx schema 必须是 Result 的 $ref 或含 Result 的 allOf 组合。"""
    if not isinstance(schema, dict):
        return False
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.endswith("/Result"):
        return True
    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        return any(is_result_wrapped(part) for part in all_of)
    return False


def first_example_body(json_content):
    """取首个报文体，无则 None：examples 优先于 example，条目带 value 包装时取 value。"""
    if not isinstance(json_content, dict):
        return None
    examples = json_content.get("examples")
    if isinstance(examples, dict) and examples:
        first = next(iter(examples.values()))
        if isinstance(first, dict) and "value" in first:
            return first["value"]
        return first
    if "example" in json_content:
        return json_content["example"]
    return None


def utc_now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
