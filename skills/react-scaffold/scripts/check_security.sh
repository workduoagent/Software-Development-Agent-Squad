#!/usr/bin/env bash
# 交付门禁 · 前端安全基线机检（对应 docs/02-protocols/security-baseline.md 的 SEC-8 / DP-3 / AC-5 前端侧，检查项编号 F001–F008）
# 用法：bash scripts/check_security.sh [src]
# 退出码：0 = 无 ERROR 级命中；1 = 有 ERROR 级命中（必须清零后才能提测）；2 = 目录不存在
# 行尾加 "// nosec-fe: 理由" 可豁免单行命中；豁免必须在代码评审里被看到。
# 前端门禁只判"代码里写出来的东西"，Token 存储策略是否落地、越权是否真挡住由 QA 用例与 review-criteria 负责。

set -uo pipefail

ROOT="${1:-src}"
if [ ! -d "$ROOT" ]; then
  echo "usage: bash scripts/check_security.sh [src]  -- directory '$ROOT' not found"
  exit 2
fi

ERR=$(mktemp)
WARN=$(mktemp)
INFO=$(mktemp)
trap 'rm -f "$ERR" "$WARN" "$INFO"' EXIT

add_err()  { printf '%s\n' "$1" >>"$ERR"; }
add_warn() { printf '%s\n' "$1" >>"$WARN"; }
add_info() { printf '%s\n' "$1" >>"$INFO"; }

G=(grep -rnE --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.git --exclude-dir=coverage
   --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx')

# F001 未过滤 HTML 注入检测
RAW_HTML=$("${G[@]}" 'dangerouslySetInnerHTML|document\.write\s*\(|\.html\s*\(' "$ROOT" 2>/dev/null | grep -v 'nosec-fe:' || true)
if [ -n "$RAW_HTML" ]; then
  UNSANITIZED=""
  while IFS= read -r hit; do
    line=$(printf '%s' "$hit" | cut -d: -f1)
    [ -f "$line" ] || continue
    # 同文件里出现 sanitizer 标记即认为已过滤；没有则按未过滤处理（宁可误报，不可漏报 XSS）
    grep -qiE 'DOMPurify|dompurify|sanitize' "$line" 2>/dev/null || UNSANITIZED+="$hit"$'\n'
  done <<< "$RAW_HTML"
  [ -n "$UNSANITIZED" ] && add_err "F001[ERROR] 未过滤的 HTML 注入面（dangerouslySetInnerHTML / document.write），必须先过 DOMPurify：
${UNSANITIZED%$'\n'}"
fi

# F002 凭据明文写入 web storage 检测
# 键名常藏在常量里，同行匹配会漏。改为文件级两步判定：同一文件同时出现 web storage 写入与凭据语义才算命中。
STORAGE=""
for f in $(grep -rlE --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.git \
             --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' \
             '(localStorage|sessionStorage)\.(setItem|removeItem)' "$ROOT" 2>/dev/null); do
  grep -qiE 'token|authorization|credential|passwd|password|access_key' "$f" 2>/dev/null || continue
  HIT=$(grep -HnE '(localStorage|sessionStorage)\.(setItem|removeItem)' "$f" 2>/dev/null | grep -v 'nosec-fe:' || true)
  [ -n "$HIT" ] && STORAGE+="$HIT"$'\n'
done
if [ -n "$STORAGE" ]; then
  STORAGE="${STORAGE%?}"
  add_err "F002[ERROR] 凭据/Token 走 web storage 明文持久化（XSS 一次性全拿走），改内存 + 短时效或 httpOnly Cookie：
$STORAGE"
fi

# F003 控制台输出凭据或个人信息检测
CONSOLE_LEAK=$("${G[@]}" 'console\.(log|info|debug|warn|error)\s*\([^)]*(token|password|passwd|authorization|phone|mobile|idCard|email|userInfo|profile|address|realName)' "$ROOT" 2>/dev/null | grep -v 'nosec-fe:' || true)
[ -n "$CONSOLE_LEAK" ] && add_err "F003[ERROR] 控制台打印凭据或个人信息（DP-3）：
$CONSOLE_LEAK"

CONSOLE_ANY=$("${G[@]}" 'console\.(log|info|debug)\s*\(' "$ROOT" 2>/dev/null | grep -v 'nosec-fe:' || true)
[ -n "$CONSOLE_ANY" ] && add_warn "F003[WARN] 残留 console 输出（生产包会带着用户上下文进浏览器控制台）：
$CONSOLE_ANY"

# F004 明文 http 端点检测
PLAIN_HTTP=$(grep -rnE --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.git \
  --include='*.ts' --include='*.tsx' --include='*.js' --include='*.env*' --include='*.json' \
  'http://[^"'\'' ]+' "$ROOT" 2>/dev/null | grep -vE 'localhost|127\.0\.0\.1|0\.0\.0\.0|::1|w3\.org|nosec-fe:' || true)
[ -n "$PLAIN_HTTP" ] && add_err "F004[ERROR] 明文 http 端点（ID-3/DP-2：鉴别信息与业务数据不得走非加密通道）：
$PLAIN_HTTP"

# F005 动态执行检测
DYN_EVAL=$("${G[@]}" '\beval\s*\(|new\s+Function\s*\(' "$ROOT" 2>/dev/null | grep -v 'nosec-fe:' || true)
[ -n "$DYN_EVAL" ] && add_err "F005[ERROR] eval / new Function 动态执行（等同开放注入面）：
$DYN_EVAL"

# F006 反向标签劫持检测（target=_blank 未配 rel）
BLANK=$(grep -rnE --include='*.tsx' --include='*.jsx' --include='*.html' \
  --exclude-dir=node_modules --exclude-dir=dist 'target="_blank"' "$ROOT" 2>/dev/null | grep -v 'rel=' | grep -v 'nosec-fe:' || true)
[ -n "$BLANK" ] && add_warn "F006[WARN] target=\"_blank\" 未配 rel=\"noopener noreferrer\"（反向标签劫持）：
$BLANK"

# F007 Mock 开关默认值检测
# 开发环境开 mock 是设计如此，.env.development / .env.local / *.example 一并排除；其余 env 与源码里仍为 true 才算风险。
MOCK_ON=$(grep -rnE --include='.env' --include='.env.*' --include='*.ts' 'VITE_USE_MOCK\s*[=:]\s*("?true"?)' "$ROOT" 2>/dev/null \
  | grep -vE '\.env\.development|\.env\.local|\.example' || true)
if [ -n "$MOCK_ON" ]; then
  add_warn "F007[WARN] 非开发环境的 VITE_USE_MOCK 仍为 true，出包前必须确认生产为 false（否则接口全是假数据）：
$MOCK_ON"
else
  add_info "F007 VITE_USE_MOCK 仅出现在 .env.development / 测试代码中（生产默认关闭）"
fi

# F008 依赖漏洞检测：脚本无法判定，只把 npm audit 命令钉在门禁输出里提醒真实执行
if [ -f package.json ]; then
  add_info "F008 依赖扫描需真实执行：npm audit --omit=dev --audit-level=high（S009，高危未处置不得提测）"
fi

echo "=== check_security.sh (frontend) — 安全基线机检 (root: $ROOT) ==="
if [ -s "$INFO" ]; then
  echo "[INFO] 通过项取证："
  sed 's/^/  /' "$INFO"
fi
if [ -s "$WARN" ]; then
  echo "[WARN] 以下项不拦门，但需在提测报告里说明处置："
  cat "$WARN"
fi
if [ -s "$ERR" ]; then
  echo "[BLOCKER] 以下 ERROR 级命中必须修复后才能提测："
  cat "$ERR"
  echo "SECURITY CHECK FAILED"
  exit 1
fi
echo "SECURITY CHECK PASSED — 无 ERROR 级命中"
exit 0
