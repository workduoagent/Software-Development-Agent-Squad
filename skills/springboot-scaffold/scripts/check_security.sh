#!/usr/bin/env bash
# 等保二级安全基线机检，覆盖 S002-S008、S010；S001 由 check_secrets.sh 负责，S009 由 CI 依赖扫描负责。
# 用法：bash scripts/check_security.sh [扫描根目录，默认 src]
# 退出码：0 无 ERROR 级命中；1 有 ERROR 级命中（提测前须清零）；2 目录不存在。
# WARN 级只进报告不拦门，PM/QA 可按 review-criteria 追问。
# 行尾 "#nosec: 理由" 豁免本行命中，豁免必须在代码评审里被看到。
# 无 nosec 过滤的项不适用豁免：fastjson autotype、TLS 绕过、MD5/SHA-1、System.out、S006、S010。

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

# 排除 target/（配置副本会重复计同一问题）与 test/（测试桩假凭据归 check_secrets.sh 管，不参与生产暴露面判定）
G=(grep -rnE --exclude-dir=target --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=test --include='*.java')
GI=(grep -rniE --exclude-dir=target --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=test --include='*.java')

# S002 SQL 注入面：Java 拼接、MyBatis ${} 未白名单、fastjson autotype
SQL_CONCAT=$("${G[@]}" \
  '"[^"]*(select|insert|update|delete|where|order by|from)[^"]*"\s*\+' "$ROOT" 2>/dev/null | grep -v 'nosec' || true)
[ -n "$SQL_CONCAT" ] && add_err "S002[ERROR] SQL 字符串拼接：
$SQL_CONCAT"

# ${} 仅在 mapper XML 中是 SQL 拼接，pom/logback 里的是属性引用，故限定 mapper 路径（约定 mapper-locations=classpath:mapper/*.xml），免得无害命中把门禁刷成噪音。
# 白名单标注须在命中行本身或其上两行；放宽成"含 order by 即放过"恰好吞掉最高危的排序字段注入。
MAPPER_HIT=""
while IFS= read -r -d '' f; do
    HIT=$(awk '
      { lines[NR] = $0 }
      /\$\{[A-Za-z0-9_.]+\}/ {
        allowed = 0
        for (i = NR - 2; i <= NR; i++) {
          if (i > 0 && lines[i] ~ /nosec:|白名单|whitelist|Whitelist/) { allowed = 1 }
        }
        if (!allowed) printf "%s:%d:%s\n", FILENAME, NR, $0
      }
    ' "$f" 2>/dev/null || true)
  [ -n "$HIT" ] && MAPPER_HIT+="$HIT"$'\n'
done < <(find "$ROOT" -type d -name target -prune -o -type f -name '*.xml' -path '*mapper*' -print0 2>/dev/null)
if [ -n "$MAPPER_HIT" ]; then
  MAPPER_HIT="${MAPPER_HIT%?}"   # 去掉累加时多带的结尾换行，否则报告里出空行
  add_err "S002[ERROR] MyBatis \${} 拼接且无白名单标注（同行或紧邻上方注释写明 nosec/白名单 才放行）：
$MAPPER_HIT"
fi

FASTJSON_AUTOTYPE=$("${G[@]}" 'setAutoTypeSupport\s*\(\s*true|AutoTypeSupport' "$ROOT" 2>/dev/null || true)
[ -n "$FASTJSON_AUTOTYPE" ] && add_err "S002[ERROR] fastjson autotype 开启（反序列化 RCE）：
$FASTJSON_AUTOTYPE"

# S003 口令处理：明文比较 ERROR，弱哈希 WARN
PLAIN_CMP=$("${G[@]}" \
  'getPassword\s*\(\s*\)\s*\.\s*(equals|equalsIgnoreCase|startsWith)|\.equals\s*\(\s*[A-Za-z0-9_.{}]*getPassword\s*\(\s*\)|password\.equals\s*\(' \
  "$ROOT" 2>/dev/null | grep -v 'nosec' || true)
[ -n "$PLAIN_CMP" ] && add_err "S003[ERROR] 口令明文比较，应改 BCrypt matches：
$PLAIN_CMP"

# 40 字符内与口令词同现的启发式判定，精度不足，故降为 WARN 交人确认
WEAK_HASH=$("${GI[@]}" \
  '(md5|sha-?1).{0,40}(password|口令|密码)|(password|口令|密码).{0,40}(md5|sha-?1)' "$ROOT" 2>/dev/null || true)
[ -n "$WEAK_HASH" ] && add_warn "S003[WARN] 口令使用 MD5/SHA-1，应改 BCrypt/PBKDF2：
$WEAK_HASH"

# S004 日志敏感信息
# 在 nosec 之后再排除同行写明掩码/desensitize 的命中：脱敏后打印不算泄漏
LOG_SENSITIVE=$("${G[@]}" \
  'log(ger)?\.(trace|debug|info|warn|error)\s*\(.*(passw(or)?d|passwd|token|secret|idCard|id_card|身份证|银行卡|手机号|authorization)' \
  "$ROOT" 2>/dev/null | grep -v 'nosec' | grep -vE '(password|token)[^a-zA-Z]*(掩码|mask|desensit|MaskUtils)' || true)
[ -n "$LOG_SENSITIVE" ] && add_err "S004[ERROR] 日志打印凭据/个人敏感信息：
$LOG_SENSITIVE"

CONSOLE_OUT=$("${G[@]}" 'System\.(out|err)\.print|printStackTrace\(\)' "$ROOT" 2>/dev/null || true)
[ -n "$CONSOLE_OUT" ] && add_warn "S004[WARN] System.out/printStackTrace 会绕过日志治理与脱敏：
$CONSOLE_OUT"

# S005 审计能力存在性
AUDIT_IMPL=$(grep -rlE --exclude-dir=target --exclude-dir=.git --include='*.java' \
  'AuditLog|AuditEvent|AUDIT_|audit_log|LoggerFactory\.getLogger\("AUDIT"' "$ROOT" 2>/dev/null || true)
if [ -z "$AUDIT_IMPL" ]; then
  add_err "S005[ERROR] 未发现审计事件写入实现（等保二级·安全审计 a)：审计须覆盖每个用户与重要行为）"
else
  add_info "S005 审计实现命中 $(printf '%s\n' "$AUDIT_IMPL" | wc -l | tr -d ' ') 个文件，示例：$(printf '%s\n' "$AUDIT_IMPL" | head -3 | tr '\n' ' ')"
fi

# S006 审计日志留存不少于 180 天
# 只读审计 appender 那一段：运行日志的 <maxHistory> 再大也不代表审计留存，全文取"任一值达标即放行"会让只留 7 天的工程混过门禁。
# 止步于首个含 audit appender 的文件，多环境各自配置时需人工核对其余文件。
LOGBACK=$(find "$ROOT" -type d -name target -prune -o -type f \( -name 'logback*.xml' -o -name 'log-config*.xml' \) -print 2>/dev/null || true)
if [ -z "$LOGBACK" ]; then
  add_warn "S006[WARN] 未找到 logback 配置文件，无法核验审计留存周期"
else
  VERDICT=""
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    BLOCK=$(awk 'BEGIN{RS="</appender>"} /<appender/ && tolower($0) ~ /audit/ { print; exit }' "$f" 2>/dev/null)
    [ -z "$BLOCK" ] && continue
    RAW=$(printf '%s' "$BLOCK" | sed -n 's/.*<[Mm]ax[Hh]istory>\([^<]*\)<.*/\1/p' | head -1 | tr -d '[:space:]')
    if [ -z "$RAW" ]; then VERDICT="FAIL:none"; break; fi
    NUM="$RAW"
    case "$RAW" in
      '${'*'}')
        # 占位写法 ${NAME:-默认}：同名 property 定义优先，其次行内默认值，两者都取不到才转人工核对
        NAME=$(printf '%s' "$RAW" | sed -e 's/^${//' -e 's/[:}].*$//')
        PROP=$(grep -oE "name=\"$NAME\"[^>]*value=\"[0-9]+\"" "$f" 2>/dev/null | grep -oE '[0-9]+' | tail -1)
        DEFAULT=$(printf '%s' "$RAW" | sed -n 's/.*:-\(.*\)}/\1/p')
        NUM="${PROP:-$DEFAULT}"
        ;;
    esac
    if [[ "$NUM" =~ ^[0-9]+$ ]]; then
      if [ "$NUM" -ge 180 ]; then VERDICT="PASS:$NUM"; else VERDICT="FAIL:$NUM"; fi
    elif [ -z "$VERDICT" ]; then
      VERDICT="UNRESOLVED:$RAW"
    fi
    break
  done <<< "$LOGBACK"
  case "${VERDICT%%:*}" in
    PASS) add_info "S006 审计留存 maxHistory=${VERDICT#PASS:} ≥ 180 天" ;;
    FAIL) add_err "S006[ERROR] 审计日志留存不足 180 天（法定下限，网安法二十一条(三)）：maxHistory=${VERDICT#FAIL:}" ;;
    UNRESOLVED) add_warn "S006[WARN] 审计留存取值为 ${VERDICT#UNRESOLVED:}，静态无法判定，需人工核对运行环境实际值" ;;
    *) add_err "S006[ERROR] 运行日志配置里没有独立的审计 appender/file（审计与运行日志必须物理分离）" ;;
  esac
fi

# S007 暴露面收敛
# exposure 与 include 在 YAML 里分处不同层级，单行 grep 永远匹配不到；先定位含 exposure 的配置文件，再在文件内查 include。
ACTUATOR_WIDE=""
while IFS= read -r -d '' f; do
  HIT=$(grep -HnE 'include\s*:\s*(\[[^]]*\*|\*|"[^"]*\*|'\''[^'\'']*\*)|include\s*=\s*[^,]*(env|heapdump|\*)' "$f" 2>/dev/null | grep -v 'nosec:' || true)
  [ -n "$HIT" ] && ACTUATOR_WIDE+="$HIT"$'\n'
done < <(find "$ROOT" -type d -name target -prune -o -type f \( -name '*.yml' -o -name '*.yaml' -o -name '*.properties' \) -print0 2>/dev/null | \
         xargs -0 -r grep -lE 'exposure' 2>/dev/null | tr '\n' '\0')
if [ -n "$ACTUATOR_WIDE" ]; then
  ACTUATOR_WIDE="${ACTUATOR_WIDE%?}"
  add_err "S007[ERROR] actuator 暴露过宽（生产只允许 health,info）：
$ACTUATOR_WIDE"
fi

# CORS 写法太散（allowedOrigins("*")、List.of("*")、yml 列表），单条正则易漏；先框出 CORS 行再筛含 * 的，既不放过也不误报具体域名。
CORS_WIDE=$(grep -rniE --exclude-dir=target --exclude-dir=.git --include='*.java' --include='*.yml' --include='*.yaml' \
  'allowed.?origin|@CrossOrigin|addCorsMappings|allowCredentials' "$ROOT" 2>/dev/null | grep -E '\*' || true)
[ -n "$CORS_WIDE" ] && add_err "S007[ERROR] CORS 通配来源（携带凭据时为高危，必须列白名单域名）：
$CORS_WIDE"

# 不带 origins 的 @CrossOrigin 在 Spring 里等价于允许任意来源，评审最容易当成"已经配过了"放过
BARE_CORS=$("${G[@]}" '@CrossOrigin($|[^A-Za-z(])' "$ROOT" 2>/dev/null | grep -v 'nosec' || true)
[ -n "$BARE_CORS" ] && add_err "S007[ERROR] 裸 @CrossOrigin（默认等价允许任意来源），请显式写 origins：
$BARE_CORS"

TLS_BYPASS=$("${G[@]}" \
  'ALLOW_ALL_HOSTNAME_VERIFIER|setHostnameVerifier\s*\(\s*new.*TrustAll|trustAllCerts|X509TrustAll|checkClientTrusted\s*\(\s*\)\s*\{' "$ROOT" 2>/dev/null || true)
[ -n "$TLS_BYPASS" ] && add_err "S007[ERROR] 绕过证书/主机名校验（等同明文传输）：
$TLS_BYPASS"

# S008 内部信息外泄
MSG_LEAK=$("${G[@]}" 'Result\.fail\([^)]*(getMessage|getLocalizedMessage)' "$ROOT" 2>/dev/null | grep -v 'nosec' || true)
[ -n "$MSG_LEAK" ] && add_warn "S008[WARN] 异常原始信息透出到响应体，应收敛为错误码 + traceId：
$MSG_LEAK"

# S010 鉴权声明覆盖：仅在工程使用 @ApiRegister 时校验（单体拓扑），数量少于 mapping 即存在未声明鉴权的接口
if [ -n "$(grep -rl '@ApiRegister' --exclude-dir=target --exclude-dir=.git --exclude-dir=test "$ROOT" 2>/dev/null || true)" ]; then
  MAPPING_CNT=$("${G[@]}" -o '@(Get|Post|Put|Delete|Patch)Mapping' "$ROOT" 2>/dev/null | wc -l | tr -d ' ')
  REG_CNT=$("${G[@]}" -o '@ApiRegister' "$ROOT" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$REG_CNT" -lt "$MAPPING_CNT" ]; then
    add_err "S010[ERROR] 鉴权声明少于接口数量（存在未声明鉴权的 mapping）：mapping=$MAPPING_CNT apiRegister=$REG_CNT"
  else
    add_info "S010 mapping=$MAPPING_CNT apiRegister=$REG_CNT — 声明覆盖 OK"
  fi
fi

echo "=== check_security.sh — 等保二级基线机检 (root: $ROOT) ==="
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
