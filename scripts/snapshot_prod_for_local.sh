#!/usr/bin/env bash
set -euo pipefail
: "${RENDER_DB_URL:?must be set}"
PG_DUMP="${PG_DUMP:-/opt/homebrew/opt/postgresql@16/bin/pg_dump}"
if [ ! -x "$PG_DUMP" ]; then
  echo "pg_dump not found at $PG_DUMP. Set PG_DUMP=/path/to/pg_dump or install postgresql@16." >&2
  exit 1
fi
OUT="instance/prod_snapshot_$(date +%Y%m%d_%H%M%S).sql"
mkdir -p instance
"$PG_DUMP" --no-owner --no-acl \
  --table=public.standards \
  --table=public.modules \
  --table=public.module_standard_mappings \
  --table=public.states \
  --data-only --column-inserts \
  "$RENDER_DB_URL" > "$OUT"
echo "Wrote $OUT"
