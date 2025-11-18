#!/bin/bash

# Script to run database migrations

set -e

echo "Running database migrations..."

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default database URL
DB_URL=${DATABASE_URL:-"postgresql://aismsuser:aismspass@localhost:5432/aismsdb"}
export DB_URL

# Extract connection details (use Python for reliable URI parsing)
PARSED=$(python3 <<'PY'
import os
from urllib.parse import urlparse

url = os.environ.get("DB_URL")
parsed = urlparse(url)
parts = [
    parsed.hostname or "localhost",
    str(parsed.port or 5432),
    (parsed.path or "/").lstrip("/"),
    parsed.username or "",
    parsed.password or "",
]
print("|".join(parts))
PY
)

IFS='|' read -r DB_HOST DB_PORT DB_NAME DB_USER DB_PASS <<< "$PARSED"

echo "Connecting to: $DB_HOST:$DB_PORT/$DB_NAME as $DB_USER"

# Run migration files
for migration in backend/app/migrations/*.sql; do
    echo "Running migration: $migration"
    PGPASSWORD="$DB_PASS" \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration"
done

echo "✅ Migrations completed successfully!"