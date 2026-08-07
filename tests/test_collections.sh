#!/bin/bash
# test_collections.sh
# Ensures the mrotools-test conda env exists (creates it if not),
# installs the current package, then runs all collection JSONs against snr.py.
#
# Usage:
#   bash tests/test_collections.sh
#   bash tests/test_collections.sh --output /tmp/myout/
#   bash tests/test_collections.sh --collections mrotools/collections/AC

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
ENV_NAME="mrotools-test"
COLLECTIONS_DIR="mrotools/collections"
OUTPUT_DIR="/tmp/snr_test_output"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Parse optional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)      OUTPUT_DIR="$2"; shift 2 ;;
        --collections) COLLECTIONS_DIR="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

cd "$REPO_ROOT"
mkdir -p "$OUTPUT_DIR"

echo "======================================================"
echo " mroptimum-tools — Collection Test Runner"
echo "======================================================"
echo " Repo        : $REPO_ROOT"
echo " Collections : $COLLECTIONS_DIR"
echo " Output      : $OUTPUT_DIR"
echo " Conda env   : $ENV_NAME"
echo ""

# ── Step 1: ensure conda env ──────────────────────────────────────────────────
if conda env list | grep -q "^${ENV_NAME}\s"; then
    echo "[env] ✓ '$ENV_NAME' already exists"
else
    echo "[env] Creating conda env '$ENV_NAME' (python=3.11)..."
    conda create -n "$ENV_NAME" python=3.11 -y
    echo "[env] ✓ Created"
fi

# ── Step 2: install package into env ─────────────────────────────────────────
echo "[env] Installing mrotools into '$ENV_NAME'..."
conda run -n "$ENV_NAME" pip install -e . -q
echo "[env] ✓ Installed"
echo ""

# ── Step 3: collect JSON files ───────────────────────────────────────────────
mapfile -t JSONS < <(find "$COLLECTIONS_DIR" -name "*.json" | sort)
TOTAL=${#JSONS[@]}
echo "[test] Found $TOTAL JSON configs"
echo "------------------------------------------------------"

PASSED=()
FAILED=()
SKIPPED=()

# ── Step 4: run each config ───────────────────────────────────────────────────
for j in "${JSONS[@]}"; do
    printf "  %-60s " "$j"
    
    output=$(conda run -n "$ENV_NAME" python mrotools/snr.py \
        -j "$j" \
        -o "$OUTPUT_DIR" \
        --no-verbose \
        --no-gfactor \
        --no-parallel 2>&1) && rc=0 || rc=$?

    if [[ $rc -eq 0 ]]; then
        echo "✓  OK"
        PASSED+=("$j")
    elif echo "$output" | grep -qE "FileNotFoundError|No such file|cannot open"; then
        echo "⚠  SKIP  (data file not on this machine)"
        SKIPPED+=("$j")
    else
        echo "✗  FAILED"
        # Print last error line indented
        last_err=$(echo "$output" | grep -v "^$" | tail -1)
        echo "           → $last_err"
        FAILED+=("$j")
    fi
done

# ── Step 5: summary ───────────────────────────────────────────────────────────
echo ""
echo "======================================================"
echo " SUMMARY"
echo "======================================================"
echo " Total   : $TOTAL"
echo " Passed  : ${#PASSED[@]}"
echo " Skipped : ${#SKIPPED[@]}  (data files not on this machine)"
echo " Failed  : ${#FAILED[@]}"

if [[ ${#SKIPPED[@]} -gt 0 ]]; then
    echo ""
    echo "Skipped:"
    for j in "${SKIPPED[@]}"; do echo "  $j"; done
fi

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo ""
    echo "Failed:"
    for j in "${FAILED[@]}"; do echo "  $j"; done
    echo ""
    echo "Result: ✗ Some configs failed — check errors above"
    exit 1
else
    echo ""
    echo "Result: ✓ All runnable configs passed"
    exit 0
fi
