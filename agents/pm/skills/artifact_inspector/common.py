"""artifact_inspector 共享工具：路径安全、文件指纹、检查行输出与 JSON 凭证。纯标准库，无第三方依赖。"""
import hashlib
import json
import os
import re
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PLACEHOLDER_RE = re.compile(r"占位|待填充|待补充|placeholder|\btodo\b|\btbd\b", re.I)
COMMENTISH_RE = re.compile(r"^\s*(#|//|\*|--|>|;|<!--|\*/|\"\"\"|''')")


def fail(msg, code=1):
    print(f"FAIL: {msg}")
    sys.exit(code)


def usage(msg):
    print(f"USAGE ERROR: {msg}")
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_join(root, rel):
    """root_dir 内路径拼接；绝对路径、盘符路径或逃逸出 root 时返回 None。"""
    if not isinstance(rel, str) or not rel:
        return None
    if os.path.isabs(rel) or re.match(r"^[A-Za-z]:[\\/]", rel):
        return None
    candidate = os.path.normpath(os.path.join(root, rel))
    root_real = os.path.normcase(os.path.realpath(root))
    cand_real = os.path.normcase(os.path.realpath(candidate))
    if cand_real != root_real and not cand_real.startswith(root_real + os.sep):
        return None
    return candidate


def strip_ansi(text):
    return ANSI_RE.sub("", text)


def placeholder_only(text):
    """review-criteria 一节"仅占位 TODO 视为不存在"的机器判据：全部非空行都是注释形态，且正文命中占位词。"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    if any(not COMMENTISH_RE.match(ln) for ln in lines):
        return False
    return bool(PLACEHOLDER_RE.search(" ".join(lines)))


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def print_check(item, level, loc, msg):
    print(f"[{item}] {level} @ {loc}: {msg}")


def write_report(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"报告已写入: {path}")
