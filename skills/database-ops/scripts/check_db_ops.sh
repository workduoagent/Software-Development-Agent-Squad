#!/usr/bin/env bash
# 数据库变更机检门禁，覆盖 D001-D015，对应 skills/database-ops/ 的规范条款。
# 用法：bash skills/database-ops/scripts/check_db_ops.sh [扫描根目录，默认 src/main/resources]
# 退出码：0 无 ERROR 级命中；1 有 ERROR 级命中（提测与上线前须清零）；2 目录不存在。
# WARN 级只进报告不拦门，PM 与评审按 review-criteria 追问处置。
# 单行豁免：行尾加 "-- nosec-db: 理由"；整文件豁免在文件头加 "-- dbops-ignore: D002,D003 理由"。
# 豁免必须写理由：无理由的 dbops-ignore 不生效并记 D015，理由要能让评审在十年后还看得懂为什么放行。
# 本脚本只做静态文本分析，不连接数据库：索引是否真命中、锁影响多大由变更单与人工评审负责。

set -uo pipefail

ROOT="${1:-src/main/resources}"
if [ ! -d "$ROOT" ]; then
  echo "usage: bash check_db_ops.sh [dir]  -- directory '$ROOT' not found"
  exit 2
fi

ERR=$(mktemp)
WARN=$(mktemp)
INFO=$(mktemp)
VERS=$(mktemp)
trap 'rm -f "$ERR" "$WARN" "$INFO" "$VERS"' EXIT

add_err()  { printf '%s\n' "$1" >>"$ERR"; }
add_warn() { printf '%s\n' "$1" >>"$WARN"; }
add_info() { printf '%s\n' "$1" >>"$INFO"; }

FIND_EXCL=( -type d \( -name target -o -name node_modules -o -name .git -o -name dist -o -name __pycache__ \) -prune -o )
SQL_LIST=$(find "$ROOT" "${FIND_EXCL[@]}" -type f -name '*.sql' -print 2>/dev/null | sort)
YML_LIST=$(find "$ROOT" "${FIND_EXCL[@]}" -type f \( -name '*.yml' -o -name '*.yaml' \) -print 2>/dev/null | sort)

IGN=""
DIALECT=""

hits() {  # $1=regex $2=file：行级命中，只放过写了理由的豁免行，同时跳过文件头的声明行
  grep -niE "$1" "$2" 2>/dev/null \
    | grep -vE 'nosec-db:[[:space:]]*[^[:space:]]' \
    | grep -viE 'dialect[[:space:]]*:|dbops-ignore' || true
}

detect_dialect() {
  awk 'NR <= 20 && tolower($0) ~ /dialect[[:space:]]*:/ {
         if (tolower($0) ~ /mysql/)    { print "mysql"; exit }
         if (tolower($0) ~ /postgres/) { print "pg";    exit }
       }' "$1"
}

ignored() {  # 返回文件头声明的豁免码，形如 ,D002,D003,；码表后面没写理由则视为未豁免
  awk 'NR <= 20 && tolower($0) ~ /dbops-ignore[[:space:]]*:/ {
         sub(/.*dbops-ignore[[:space:]]*:[[:space:]]*/, "", $0)
         codes = $1
         rest = $0
         sub(/^[^[:space:]]+/, "", rest)
         gsub(/[[:space:]]/, "", rest)
         if (rest == "") exit
         print "," toupper(codes) ","; exit
       }' "$1"
}

reasonless_ignore() {  # 只列码表、不写理由的豁免行，交给 D015 拦下
  awk 'NR <= 20 && tolower($0) ~ /dbops-ignore[[:space:]]*:/ {
         s = $0
         sub(/.*dbops-ignore[[:space:]]*:[[:space:]]*/, "", s)
         c = s
         gsub(/[[:space:]]/, "", c)
         sub(/^[Dd][0-9]+(,[Dd][0-9]+)*$/, "", c)
         if (c == "") printf "%s:%d:%s\n", FILENAME, NR, $0
       }' "$1"
}

is_ignored() { case "$IGN" in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

# 表块分析：D002 六大基石、D003 tenant 前导索引、D008 金额类型、D011 MySQL 索引键长。
# CREATE INDEX 常写在建表块之后，所以先收集全部块与索引语句，END 阶段再判定，避免把已有索引漏认成缺失。
analyze_tables() {
  awk -v file="$1" -v diale="$DIALECT" '
    BEGIN {
      inblk = 0; isidx = 0; blk = ""; tbl = ""; idxtxt = ""; cnt = 0; ref = 0
      fields[1] = "id"; fields[2] = "created_at"; fields[3] = "updated_at"
      fields[4] = "created_by"; fields[5] = "updated_by"; fields[6] = "tenant"
    }
    function wordre(w) { return "(^|[^a-z0-9_])" w "([^a-z0-9_]|$)" }
    function report(  i, n, c, miss, all, lines, keylines, overs, oa, m, name, len) {
      miss = ""
      for (i = 1; i <= 6; i++) if (sb[ref] !~ wordre(fields[i])) miss = miss " " fields[i]
      if (miss != "") printf "D002 %s:%d:表 %s 缺基石列:%s\n", file, st[ref], sn[ref], miss

      if (sb[ref] ~ wordre("tenant")) {
        all = sb[ref] "\n" idxtxt
        if (all !~ /(key|unique key|index)[^,(]*[(][[:space:]]*tenant[[:space:]]*[,)]/)
          printf "D003 %s:%d:表 %s 有 tenant 列但没有以 tenant 为前导列的索引\n", file, st[ref], sn[ref]
      }

      n = split(sb[ref], lines, "\n")
      keylines = ""; overs = ""
      for (i = 1; i <= n; i++) {
        c = lines[i]; sub(/^[[:space:]]*/, "", c)
        if (c ~ /^(primary[[:space:]]+key|unique[[:space:]]+key|key|index|constraint)/) keylines = keylines "\n" c
        if (c ~ wordre("amount") || c ~ wordre("price") || c ~ wordre("money") || c ~ wordre("fee") \
            || c ~ wordre("balance") || c ~ wordre("cost") || c ~ wordre("total") || c ~ wordre("discount") \
            || c ~ wordre("subtotal")) {
          if (c ~ /(^|[[:space:]])(float|double|real)([[:space:]]|[(,]|$)/ \
              || c ~ /(^|[^a-z0-9_])(numeric|decimal)([^a-z0-9_(]|$)/)
            printf "D008 %s:%d:%s\n", file, st[ref] + i, substr(c, 1, 90)
        }
        if (diale == "mysql" && match(c, /varchar[(][0-9]+[)]/)) {
          len = substr(c, RSTART, RLENGTH); gsub(/[^0-9]/, "", len)
          if (len + 0 > 768) { name = c; sub(/[[:space:]].*/, "", name); overs = overs " " name }
        }
      }
      if (diale == "mysql" && overs != "") {
        m = split(overs, oa, " ")
        for (i = 1; i <= m; i++)
          if (oa[i] != "" && index(keylines, oa[i]) > 0)
            printf "D011 %s:%d:列 %s 为 varchar>768，utf8mb4 下索引键长上限 3072 字节，需前缀索引或收窄长度\n",
                   file, st[ref], oa[i]
      }
    }
    {
      raw = $0
      sub(/--.*$/, "", raw)
      low = tolower(raw)
      gsub(/`/, "", low)
      # 索引语句常把 ON 与列另起一行，攒到分号再交给前导列判定，否则正常排版会被误判成缺索引
      if (isidx) {
        idxtxt = idxtxt low
        if (low ~ /;/) isidx = 0
        next
      }
      if (low ~ /create[[:space:]]+(unique[[:space:]]+)?index/) {
        idxtxt = idxtxt "\n" low
        if (low !~ /;/) isidx = 1
      }
      if (!inblk && low ~ /create[[:space:]]+table/) {
        t = low
        sub(/.*create[[:space:]]+table([[:space:]]+if[[:space:]]+not[[:space:]]+exists)?[[:space:]]*/, "", t)
        sub(/[[:space:]]*[(;].*/, "", t)
        gsub(/[[:space:]]/, "", t)
        inblk = 1; tblstart = NR; tbl = t; blk = ""
      }
      if (inblk) {
        blk = blk "\n" low
        if (low ~ /^[[:space:]]*[)]/ || low ~ /[)][[:space:]]*(engine|;|$)/) {
          inblk = 0; cnt++
          st[cnt] = tblstart; sn[cnt] = tbl; sb[cnt] = blk
        }
      }
    }
    END { for (ref = 1; ref <= cnt; ref++) report() }
  ' "$1"
}

# 语句级检查：D005 UPDATE / DELETE FROM 必须带 WHERE
analyze_stmts() {
  awk -v file="$1" '
    BEGIN { RS = ";" }
    { rec[NR] = $0; nlc[NR] = gsub(/\n/, "\n", rec[NR]) }
    END {
      cum = 0
      for (i = 1; i <= NR; i++) {
        s = rec[i]
        before = gsub(/\n/, "\n", s)
        while (sub(/^[ \t]*--[^\n]*\n/, "", s)) { }
        sub(/^[ \t\n]+/, "", s)
        start = cum + 1 + before - gsub(/\n/, "\n", s)
        cum += nlc[i]
        l = tolower(s)
        if (l !~ /^(update|delete[[:space:]]+from)/) continue
        if (l ~ /[[:space:]]where[[:space:]]/ || l ~ /[[:space:]]using[[:space:]]/) continue
        if (l ~ /nosec-db:[[:space:]]*[^[:space:]]/) continue
        # 行尾豁免注释跟在分号后面，会被切进下一条记录的开头，这里接回上一条语句
        tail = rec[i + 1]
        sub(/\n.*/, "", tail)
        gsub(/[ \t]/, "", tail)
        if (substr(tail, 1, 2) == "--" && tail ~ /nosec-db:[[:space:]]*[^[:space:]]/) continue
        first = s; sub(/\n.*/, "", first)
        printf "D005 %s:%d:%s 缺少 WHERE\n", file, start, substr(first, 1, 90)
      }
    }
  ' "$1"
}

# 池大小可能是 ${ENV:默认值} 形态，取末段数字作为生效值判定上限
pool_size_of() {
  local raw num
  raw=$(grep -oiE 'maximum[-_]pool[-_]size[[:space:]]*:[[:space:]]*[^[:space:]#]+' "$1" 2>/dev/null | head -1)
  raw=${raw#*:}
  raw=$(printf '%s' "$raw" | sed 's/^[[:space:]]*//')
  [ -z "$raw" ] && return 1
  case "$raw" in
    '${'*) num=$(printf '%s' "$raw" | grep -oE '[0-9]+' | tail -1) ;;
    *)     num=$(printf '%s' "$raw" | grep -oE '^[0-9]+') ;;
  esac
  printf '%s' "${num:-}"
  return 0
}

SQL_CNT=0
YML_CNT=0
DS_CNT=0

if [ -n "$SQL_LIST" ]; then
  while IFS= read -r f; do
    SQL_CNT=$((SQL_CNT + 1))
    DIALECT=$(detect_dialect "$f")
    IGN=$(ignored "$f")

    R=$(reasonless_ignore "$f")
    [ -n "$R" ] && add_err "D015[ERROR] $f 的整文件豁免只列了码表没写理由，该豁免不生效：
$R"
    R=$(grep -niE 'nosec-db:[[:space:]]*$' "$f" 2>/dev/null || true)
    [ -n "$R" ] && add_err "D015[ERROR] $f 的行尾豁免只写了标记没写理由：
$R"

    if [ -z "$DIALECT" ]; then
      add_warn "D009[WARN] $f 文件头未声明 -- dialect: postgresql|mysql，方言混用无法判定"
    fi

    if ! is_ignored D001; then
      H=$(hits '(^|[^a-z0-9_])(big|small)?serial([^a-z0-9_(]|$)|auto_increment|generated[[:space:]]+(always|by[[:space:]]+default)[[:space:]]+as[[:space:]]+identity' "$f")
      [ -n "$H" ] && add_err "D001[ERROR] 业务主键禁用数据库自增与序列，雪花 ID 由应用侧生成：
$H"
    fi

    if ! is_ignored D004; then
      H=$(hits 'create[[:space:]]+table' "$f" | grep -viE 'if[[:space:]]+not[[:space:]]+exists' || true)
      [ -n "$H" ] && add_err "D004[ERROR] CREATE TABLE 缺 IF NOT EXISTS，脚本不可重复执行：
$H"
      if [ "$DIALECT" = "pg" ]; then
        H=$(hits 'create[[:space:]]+(unique[[:space:]]+)?index|add[[:space:]]+column' "$f" \
            | grep -viE 'if[[:space:]]+not[[:space:]]+exists|pg_constraint|information_schema|constraint' || true)
        [ -n "$H" ] && add_err "D004[ERROR] PG 侧建索引/加列缺 IF NOT EXISTS，重跑即报错中断迁移：
$H"
      fi
    fi

    if ! is_ignored D005; then
      H=$(analyze_stmts "$f")
      [ -n "$H" ] && add_err "D005[ERROR] 数据变更语句无 WHERE，影响面不可控：
$H"
    fi

    if ! is_ignored D006; then
      if grep -qiE 'drop[[:space:]]+(table|database|column)|truncate' "$f" 2>/dev/null; then
        { grep -qiE '备份|pg_dump|mysqldump' "$f" && grep -qiE '恢复|pg_restore|备份产物' "$f"; } \
          || add_err "D006[ERROR] $f 含破坏性语句，但未写明备份产物与恢复命令（无备份即无回滚方案）"
      fi
    fi

    if ! is_ignored D007 && grep -qiE 'create[[:space:]]+table' "$f"; then
      if [ "$DIALECT" = "pg" ]; then
        H=$(hits '\btimestamp\b' "$f")
        [ -n "$H" ] && add_warn "D007[WARN] PG 无时区 timestamp 会在跨时区部署时整体偏移，基线要求 timestamptz：
$H"
      elif [ "$DIALECT" = "mysql" ]; then
        grep -qiE '时区|timezone' "$f" \
          || add_warn "D007[WARN] $f 用 MySQL DATETIME 但文件头没声明时区口径，服务端与 JVM 时区不一致即静默偏移"
      fi
    fi

    if ! is_ignored D009; then
      if [ "$DIALECT" = "pg" ]; then
        H=$(hits 'on[[:space:]]+duplicate[[:space:]]+key|[^a-z_]engine[[:space:]]*=|utf8mb4|ifnull[(]|group_concat[(]|datetime[(]|modify[[:space:]]+(column|table)' "$f")
        [ -n "$H" ] && add_err "D009[ERROR] 声明为 postgresql 却出现 MySQL 专有语法：
$H"
      elif [ "$DIALECT" = "mysql" ]; then
        H=$(hits 'on[[:space:]]+conflict|[^a-z_]jsonb[^a-z_]|returning[^x]|timestamptz|ilike|to_char[(]|pg_stat|pg_class|pg_constraint' "$f")
        [ -n "$H" ] && add_err "D009[ERROR] 声明为 mysql 却出现 PostgreSQL 专有语法：
$H"
      fi
    fi

    if ! is_ignored D012; then
      H=$(hits 'select[[:space:]]+\*' "$f")
      [ -n "$H" ] && add_warn "D012[WARN] SELECT * 会随列变动静默错位并放弃覆盖索引收益，改为显式列：
$H"
    fi

    if ! is_ignored D014; then
      H=$(hits 'add[[:space:]]+column.*not[[:space:]]+null' "$f" | grep -viE 'default|check' || true)
      [ -n "$H" ] && add_warn "D014[WARN] 加非空列未带默认值，存量行会导致语句失败或长锁；按加可空列-回填-补约束三步走：
$H"
    fi

    H=$(analyze_tables "$f")
    if [ -n "$H" ]; then
      if ! is_ignored D002; then
        E=$(printf '%s\n' "$H" | grep '^D002' || true)
        [ -n "$E" ] && add_err "D002[ERROR] 表结构缺六大基石列（id/created_at/updated_at/created_by/updated_by/tenant）：
$E"
      fi
      if ! is_ignored D003; then
        T=$(printf '%s\n' "$H" | grep '^D003' || true)
        [ -n "$T" ] && add_err "D003[ERROR] 租户隔离缺索引支撑（tenant 必须是某索引的前导列）：
$T"
      fi
      if ! is_ignored D008; then
        M=$(printf '%s\n' "$H" | grep '^D008' || true)
        [ -n "$M" ] && add_err "D008[ERROR] 金额列使用浮点或无精度 DECIMAL，存在分位误差：
$M"
      fi
      N=$(printf '%s\n' "$H" | grep '^D011' || true)
      [ -n "$N" ] && add_warn "D011[WARN] MySQL utf8mb4 索引键长风险：
$N"
    fi

    base=$(basename "$f")
    case "$base" in
      V*.sql)
        ver="${base#V}"; ver="${ver%%__*}"
        case "$base" in
          *'__'*) : ;;
          *) add_err "D010[ERROR] $f 命名不合法，应为 V{n}__{描述}.sql（版本号与描述之间双下划线）" ;;
        esac
        case "$ver" in
          ''|*[!0-9.]*) add_err "D010[ERROR] $f 的版本号段非法：'$ver'" ;;
          *) printf '%s|%s\n' "$(dirname "$f")" "$ver" >>"$VERS" ;;
        esac
        ;;
    esac
  done <<< "$SQL_LIST"
fi

if [ -n "$YML_LIST" ]; then
  while IFS= read -r f; do
    YML_CNT=$((YML_CNT + 1))
    grep -q 'jdbc:' "$f" 2>/dev/null || continue
    DS_CNT=$((DS_CNT + 1))
    IGN=""

    H=$(hits 'autoreconnect[[:space:]]*=[[:space:]]*true' "$f")
    [ -n "$H" ] && add_err "D013[ERROR] 驱动自动重连会丢会话变量、临时表与事务上下文，重连交给连接池：
$H"

    if MAXP=$(pool_size_of "$f"); then
      [ -n "$MAXP" ] && [ "$MAXP" -gt 100 ] \
        && add_err "D013[ERROR] $f 的 maximum-pool-size=$MAXP 超过 100：先查慢查询与池模型，加连接只会把排队从池子搬到锁上"
    else
      add_warn "D013[WARN] $f 有数据源却未设 maximum-pool-size，沿用默认值等于没做容量评估"
    fi
    for key in 'pool-name|poolname' 'max-lifetime|maxlifetime' 'connection-timeout|connectiontimeout'; do
      grep -qiE "$key" "$f" \
        || add_warn "D013[WARN] $f 连接池缺 ${key%%|*}，回收行为与指标归属都不可控（取值依据见 references/connection.md）"
    done

    H=$(grep -niE 'jdbc:postgresql' "$f" 2>/dev/null | grep -viE 'sockettimeout|nosec-db' || true)
    [ -n "$H" ] && add_warn "D014[WARN] PG JDBC URL 缺 socketTimeout（单位秒，默认 0 即永不超时），挂死的查询会永久占住连接：
$H"
    H=$(grep -niE 'jdbc:mysql' "$f" 2>/dev/null | grep -viE 'rewritebatchedstatements|nosec-db' || true)
    [ -n "$H" ] && add_warn "D014[WARN] MySQL JDBC URL 缺 rewriteBatchedStatements，批量写会退化为逐条发送：
$H"
  done <<< "$YML_LIST"
fi

if [ -s "$VERS" ]; then
  DUP=$(sort "$VERS" | uniq -d || true)
  [ -n "$DUP" ] && add_err "D010[ERROR] 同一迁移目录下 Flyway 版本号重复（已提交的脚本不可改写，请递增版本号）：
$DUP"
fi

add_info "D001-D015 覆盖范围：sql 文件 $SQL_CNT 个，配置文件 $YML_CNT 个（含数据源 $DS_CNT 个）"

echo "=== check_db_ops.sh — 数据库变更机检 (root: $ROOT) ==="
if [ -s "$INFO" ]; then
  echo "[INFO] 通过项取证："
  sed 's/^/  /' "$INFO"
fi
if [ -s "$WARN" ]; then
  echo "[WARN] 以下项不拦门，但需在提测报告里说明处置："
  cat "$WARN"
fi
if [ -s "$ERR" ]; then
  echo "[BLOCKER] 以下 ERROR 级命中必须修复后才能提测/上线："
  cat "$ERR"
  echo "DB OPS CHECK FAILED"
  exit 1
fi
echo "DB OPS CHECK PASSED — 无 ERROR 级命中"
exit 0
