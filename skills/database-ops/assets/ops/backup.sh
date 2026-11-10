#!/usr/bin/env bash
# 数据库备份最小实现：逻辑备份 + 校验和 + 保留期清理，供发布机或定时任务调用。
# 用法：DB_ENGINE=postgresql|mysql DB_HOST=... DB_NAME=app_db DB_USERNAME=... DB_PASSWORD=... \
#       BACKUP_DIR=/backup/db bash backup.sh
# 口令只从环境变量注入，脚本内不得出现任何默认值；缺失即退出，不产出空备份。
# 结构快照是变更前必须留存的产物，配合 references/operations.md 第四节的物理备份使用。

set -euo pipefail

ENGINE="${DB_ENGINE:?set DB_ENGINE to postgresql or mysql}"
HOST="${DB_HOST:?set DB_HOST}"
PORT="${DB_PORT:-}"
DB_NAME="${DB_NAME:?set DB_NAME}"
DB_USER="${DB_USERNAME:?set DB_USERNAME}"
DB_PASSWORD="${DB_PASSWORD:?set DB_PASSWORD}"
BACKUP_DIR="${BACKUP_DIR:-./db-backup}"
KEEP_DAYS="${KEEP_DAYS:-7}"

STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

case "$ENGINE" in
  postgresql)
    export PGPASSWORD="$DB_PASSWORD"                       # 避免口令出现在进程参数里
    PGPORT="${PORT:-5432}"
    DATA_FILE="$BACKUP_DIR/${DB_NAME}_data_${STAMP}.dump"
    SCHEMA_FILE="$BACKUP_DIR/${DB_NAME}_schema_${STAMP}.sql"
    pg_dump -h "$HOST" -p "$PGPORT" -U "$DB_USER" -d "$DB_NAME" -Fc -Z zstd -f "$DATA_FILE"
    pg_dump -h "$HOST" -p "$PGPORT" -U "$DB_USER" -d "$DB_NAME" --schema-only > "$SCHEMA_FILE"
    ;;
  mysql)
    export MYSQL_PWD="$DB_PASSWORD"
    MYSQL_TCP_PORT="${PORT:-3306}"
    DATA_FILE="$BACKUP_DIR/${DB_NAME}_data_${STAMP}.sql.gz"
    SCHEMA_FILE="$BACKUP_DIR/${DB_NAME}_schema_${STAMP}.sql"
    mysqldump -h "$HOST" -P "$MYSQL_TCP_PORT" -u "$DB_USER" \
      --single-transaction --routines --triggers --events \
      --set-gtid-purged=OFF --source-data=2 "$DB_NAME" | gzip > "$DATA_FILE"
    mysqldump -h "$HOST" -P "$MYSQL_TCP_PORT" -u "$DB_USER" --no-data "$DB_NAME" > "$SCHEMA_FILE"
    ;;
  *)
    echo "unsupported DB_ENGINE: $ENGINE (postgresql|mysql)" >&2
    exit 3
    ;;
esac

# 校验和与体积：恢复前必须能证明备份完整，只看文件存在不算
sha256sum "$DATA_FILE" "$SCHEMA_FILE" > "$BACKUP_DIR/latest.sha256"
du -h "$DATA_FILE" "$SCHEMA_FILE" | sed "s#^#size: #"

# 空备份是事故而不是幸运：结构快照小于阈值直接失败，避免保留期把可用备份挤掉
SIZE_BYTES=$(stat -c %s "$SCHEMA_FILE" 2>/dev/null || wc -c < "$SCHEMA_FILE")
if [ "$SIZE_BYTES" -lt 1024 ]; then
  echo "backup looks empty: $SCHEMA_FILE is ${SIZE_BYTES} bytes" >&2
  exit 4
fi

find "$BACKUP_DIR" -type f \( -name "${DB_NAME}_data_*" -o -name "${DB_NAME}_schema_*" \) \
  -mtime +"$KEEP_DAYS" -print -delete

echo "BACKUP OK — engine=$ENGINE data=$DATA_FILE schema=$SCHEMA_FILE keep=${KEEP_DAYS}d"
echo "RESTORE 参考见 skills/database-ops/references/operations.md 第四节；恢复演练每季度一次。"
