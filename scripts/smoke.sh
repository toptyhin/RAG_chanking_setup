#!/usr/bin/env bash
# Smoke E2E: upload → prep → chunk → testset → retrieval run → report
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API="${API_URL:-http://localhost:8000}"
TMP="${TMPDIR:-/tmp}/rageval-smoke-$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

echo "==> health"
curl -sf "$API/health" | tee "$TMP/health.json"
echo

echo "==> create project"
PID="$(curl -sf -X POST "$API/projects" \
  -H 'content-type: application/json' \
  -d '{"name":"smoke"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
echo "project_id=$PID"

echo "==> upload raw_bundle"
printf '%s\n' 'The return window is fourteen days for all online orders.' > "$TMP/notes.txt"
RAW="$(curl -sf -X POST "$API/projects/$PID/raw-bundles" \
  -F "files=@$TMP/notes.txt;type=text/plain" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["artifact"]["id"])')"
echo "raw_bundle_id=$RAW"

echo "==> prep"
CLEAN="$(curl -sf -X POST "$API/projects/$PID/prep" \
  -H 'content-type: application/json' \
  -d "{\"raw_bundle_id\":\"$RAW\",\"pipeline\":\"plaintext\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["artifact"]["id"])')"
echo "clean_corpus_id=$CLEAN"

echo "==> reference chunks"
CHUNKS="$(curl -sf -X POST "$API/projects/$PID/chunk-sets/reference" \
  -H 'content-type: application/json' \
  -d "{\"clean_corpus_id\":\"$CLEAN\",\"size\":128,\"overlap\":16}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["artifact"]["id"])')"
echo "chunk_set_id=$CHUNKS"

echo "==> import test_set"
TEST="$(curl -sf -X POST "$API/projects/$PID/test-sets/import" \
  -H 'content-type: application/json' \
  -d "{\"chunk_set_id\":\"$CHUNKS\",\"queries\":[{\"text\":\"return window is fourteen days\",\"relevant_doc_ids\":[]}],\"validate_chunk_refs\":false}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["artifact"]["id"])')"
echo "test_set_id=$TEST"

echo "==> start retrieval experiment (background)"
RUN="$(curl -sf -X POST "$API/experiments" \
  -H 'content-type: application/json' \
  -d "{\"project_id\":\"$PID\",\"evaluates\":\"retrieval\",\"chunk_set_id\":\"$CHUNKS\",\"test_set_id\":\"$TEST\",\"swept\":{\"retrieval.top_k\":[1,5]}}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
echo "run_id=$RUN"

echo "==> wait for completed"
python3 - <<PY
import json, time, urllib.request
api = "$API"
run_id = "$RUN"
deadline = time.time() + 120
while time.time() < deadline:
    with urllib.request.urlopen(f"{api}/experiments/{run_id}?wait=true&wait_timeout_sec=5") as r:
        body = json.load(r)
    status = body.get("status")
    prog = body.get("progress") or {}
    print(f"  status={status} progress={prog.get('done')}/{prog.get('total')}")
    if status in {"completed", "failed"}:
        if status != "completed":
            raise SystemExit(f"run failed: {body.get('error')}")
        if not body.get("report_object_key"):
            raise SystemExit("missing report_object_key")
        if len(body.get("metrics_rows") or []) < 1:
            raise SystemExit("no metrics rows")
        print("pareto points:", len(body.get("pareto") or []))
        break
else:
    raise SystemExit("timeout waiting for run")
PY

echo "==> download report"
curl -sf "$API/experiments/$RUN/report" -o "$TMP/report.html"
grep -q "Experiment report" "$TMP/report.html"
echo "report saved: $TMP/report.html"

echo
echo "SMOKE OK"
