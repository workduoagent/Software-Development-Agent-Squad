"""机密扫描门禁（S001 口径）：扫描源码树中的疑似硬编码机密。退出码 0 干净 / 1 命中 / 2 用法错误。

用法：python python-backend-scaffold/scripts/check_secrets.py "<root_dir>/src"
脚本只留在本 skill 里，不复制进项目；行内 `#nosec` 为显式豁免标记，须在交付报告说明理由。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS: list[tuple[str, str]] = [
    (r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*[\"'][^\"']{6,}[\"']", "硬编码机密赋值"),
    (r"(?i)postgres(ql)?(\+psycopg)?://[^/\s\"']+:[^@\s\"']+@", "连接串内嵌口令"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "私钥内容"),
    (r"(?i)(mysql|redis)://[^/\s\"']+:[^@\s\"']+@", "连接串内嵌口令"),
]
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".idea"}
TEXT_SUFFIXES = {".py", ".yml", ".yaml", ".toml", ".json", ".md", ".txt", ".cfg", ".ini", ".sh"}


def main() -> int:
    if len(sys.argv) != 2:
        print("USAGE: python check_secrets.py <扫描目录>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"FAIL: 目录不存在: {root}", file=sys.stderr)
        return 2
    hits: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for no, line in enumerate(lines, start=1):
            if "#nosec" in line:
                continue
            for pattern, label in PATTERNS:
                if re.search(pattern, line):
                    hits.append(f"{path.relative_to(root)}:{no} [{label}] {line.strip()[:120]}")
    if hits:
        print("FAIL: 机密扫描命中", file=sys.stderr)
        for hit in hits:
            print(f"  {hit}", file=sys.stderr)
        return 1
    print("[INFO] 机密扫描通过：0 命中（S001 口径）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
