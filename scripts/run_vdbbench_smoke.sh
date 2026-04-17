#!/bin/bash
set -e

# Resolve project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables from .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Default values if not set
export ES_HOSTS=${ES_HOSTS:-"http://localhost:9200"}
export ES_USER=${ES_USER:-"elastic"}
export ES_PASSWORD=${ES_PASSWORD:-""}
export ES_VERIFY_CERTS=${ES_VERIFY_CERTS:-"false"}

PYTHON="${PYTHON:-python3}"

echo "=== Phase 1: Connection Check ==="
$PYTHON "$PROJECT_ROOT/scripts/check_es_connection.py"

echo -e "\n=== Phase 2: Smoke Data Preparation ==="
$PYTHON "$PROJECT_ROOT/scripts/smoke_prepare_dataset.py"

echo -e "\n=== Phase 3: VDBBench Smoke Execution ==="
$PYTHON "$PROJECT_ROOT/scripts/run_vdbbench_smoke.py"

echo -e "\n=== Phase 4: Summarizing Results ==="
$PYTHON "$PROJECT_ROOT/scripts/summarize_results.py"
