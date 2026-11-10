#!/usr/bin/env bash
# 机密泄漏自查（交付门禁第三项）。
# 用法：bash scripts/check_secrets.sh [扫描根目录，默认 src]
# 退出码：0 干净；1 有命中（提测前须清零）；2 目录不存在。
# 三类命中：A 配置文件写死的机密值，B Java 里 ${key:默认值} 形态的默认口令，C 内网地址与 namespace UUID 等资源标识。

set -uo pipefail

ROOT="${1:-src}"
if [ ! -d "$ROOT" ]; then
  echo "usage: bash scripts/check_secrets.sh [src]  -- directory '$ROOT' not found"
  exit 2
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP" "$TMP.clean"' EXIT

# A 键名含机密语义词即命中；值以 $ 开头（${ENV} 占位）不计
# 后置三条排除是已知误报：token 计数类配置（max-tokens 等）、显式空串、纯数字值
grep -rniE --include='*.yml' --include='*.yaml' --include='*.properties' \
  '^[[:space:]]*[A-Za-z0-9_.-]*(password|passwd|secret|access[_-]?key|api[_-]?key|apikey|token)[A-Za-z0-9_.-]*[[:space:]]*[:=][[:space:]]*[^$[:space:]]' \
  "$ROOT" 2>/dev/null \
  | grep -viE '(max[-_]?tokens?|total[-_]?tokens?|prompt[-_]?tokens?|completion[-_]?tokens?|input[-_]?tokens?|output[-_]?tokens?)' \
  | grep -v ':[[:space:]]*""' \
  | grep -vE ':[[:space:]]*"?[0-9]+"?$' >>"$TMP" || true

# B 占位符自带默认口令（@Value("${jwt.secret:defaultSecretKey123}")）；默认值至少 3 个字符才算机密，短占位默认不报
grep -rnE --include='*.java' \
  '\$\{[A-Za-z0-9_.-]*(secret|password|passwd|token|accessKey|apiKey)[A-Za-z0-9_.-]*:[^}]{3,}\}' \
  "$ROOT" 2>/dev/null >>"$TMP" || true

# C 只认 IP:port 同现与 namespace 取值为 UUID 前缀两种形态，孤立 IP 不判，避免误伤示例地址
grep -rnE --include='*.yml' --include='*.yaml' --include='*.properties' --include='*.java' \
  '([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{2,5}|namespace[A-Za-z_-]*[[:space:]]*[:=][[:space:]]*[0-9a-fA-F]{8}-' \
  "$ROOT" 2>/dev/null >>"$TMP" || true

# 同一行可被多类规则重复命中，剔空行后按整行去重
grep -vE '^[[:space:]]*$' "$TMP" | sort -u >"$TMP.clean"

if [ -s "$TMP.clean" ]; then
  echo "SECRETS FOUND — 以下命中必须改成 \${ENV} 占位、迁到配置中心或删掉："
  cat "$TMP.clean"
  exit 1
fi

echo "SECRETS OK — no hardcoded credentials under $ROOT"
exit 0
