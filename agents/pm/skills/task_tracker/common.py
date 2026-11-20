"""task_tracker 共享工具：账本读写、状态机、任务定位、路径安全、指纹与输出格式。"""
import hashlib
import json
import os
import re
import sys

# Windows 控制台默认 GBK，中文输出会乱码；统一切到 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

TASK_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3}$")
UTC_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

# 权威流转边，与软件团队知识库 任务状态机.md 一致；BLOCKED 恢复目标由 PM 按挂起前状态显式指定
ALLOWED_TRANSITIONS = {
    ("TODO", "IN_PROGRESS"),
    ("IN_PROGRESS", "IN_REVIEW"),
    ("IN_REVIEW", "ACCEPTED"),
    ("IN_REVIEW", "REJECTED"),
    ("REJECTED", "IN_PROGRESS"),
    ("TODO", "BLOCKED"),
    ("IN_PROGRESS", "BLOCKED"),
    ("BLOCKED", "TODO"),
    ("BLOCKED", "IN_PROGRESS"),
}

STATUSES = {"TODO", "IN_PROGRESS", "IN_REVIEW", "ACCEPTED", "REJECTED", "BLOCKED"}


def fail(msg, code=1):
    print(f"FAIL: {msg}")
    sys.exit(code)


def usage(msg):
    print(f"USAGE ERROR: {msg}")
    sys.exit(2)


def utc_now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ledger(path):
    if not os.path.isfile(path):
        usage(f"账本不存在: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        fail(f"账本不是合法 JSON: {path}: {e}")
    if not isinstance(data, dict) or not isinstance(data.get("projects"), list):
        fail(f"账本顶层结构不合法（需含 projects 数组）: {path}")
    return data


def write_ledger(data, path):
    """单写者落盘：先写临时文件再原子替换，避免中途失败损坏账本。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")
    os.replace(tmp, path)


def find_project(ledger, project_id):
    for p in ledger["projects"]:
        if isinstance(p, dict) and p.get("project_id") == project_id:
            return p
    fail(f"项目不存在: {project_id}", 2)


def find_task(ledger, task_id):
    for p in ledger["projects"]:
        for t in p.get("tasks", []):
            if isinstance(t, dict) and t.get("task_id") == task_id:
                return p, t
    fail(f"任务不存在: {task_id}", 2)


def project_root_abs(ledger_path, project):
    """root_dir 相对仓库根（账本所在目录）解析为绝对路径。"""
    base = os.path.dirname(os.path.abspath(ledger_path)) or "."
    return os.path.normpath(os.path.join(base, project.get("root_dir", ".")))


def safe_join(root, rel):
    """root_dir 内路径拼接；包含绝对路径或逃逸出 root 时返回 None。"""
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


def print_check(item, level, loc, msg):
    print(f"[{item}] {level} @ {loc}: {msg}")


def write_report(path, data):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"报告已写入: {path}")
