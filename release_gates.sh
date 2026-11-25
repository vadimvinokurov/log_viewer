#!/usr/bin/env bash
# Release gates — per kit skill vvv-claude-kit:release-gates (see
# docs/PIPELINE.md §6a). A release tag (v*) is pushed only after this script
# ran green on the exact commit the tag will point to; the marker
# .release-gates/last-run.json (commit SHA, ok) is the evidence.
#
# The gates mirror the release workflow (.github/workflows/release.yml, job
# "gate") plus the golden gate that CI runs only on macOS (job "goldens").
# Run: bash release_gates.sh

set -u

GATES=(
  # Rust core + shell (also regenerates ui/src/bindings.ts — a dirty tree
  # after this gate is a finding, not commit noise).
  "cargo test --workspace"
  # TypeScript is the point of this gate: wipe stale incremental caches first
  # (tsc -b can hide breakage behind tsbuildinfo), then tsc -b + vite build.
  "npm --prefix ui run build"
  "npm --prefix ui test"
  # Visual goldens (playwright-core + pixelmatch, committed PNGs). Resolved
  # from ui/ — a run from the repo root silently tests the wrong environment.
  "npm --prefix ui run e2e"
)

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
cd "$PROJECT_DIR"

MARKER_DIR=".release-gates"
MARKER="$MARKER_DIR/last-run.json"
LOG="$MARKER_DIR/last-run.log"
mkdir -p "$MARKER_DIR"

sha="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "release gates @ $sha  $now" | tee "$LOG"

if [ "${#GATES[@]}" -eq 0 ] || [ -z "${GATES[0]}" ]; then
  echo "ERROR: GATES is empty — fill in the project's release checks before use." | tee -a "$LOG"
  printf '{"sha": "%s", "started": "%s", "ok": false, "error": "GATES empty"}\n' "$sha" "$now" > "$MARKER"
  exit 1
fi

# tsc -b is the decisive type gate; stale tsbuildinfo can hide breakage
# (the v0.2.0 release lesson: PIPELINE.md §6a).
rm -f ui/tsconfig*.tsbuildinfo ui/node_modules/.tmp/*.tsbuildinfo

for gate in "${GATES[@]}"; do
  echo "── gate: $gate" | tee -a "$LOG"
  if ! bash -c "$gate" >>"$LOG" 2>&1; then
    echo "── FAIL: $gate  (log: $LOG)" | tee -a "$LOG"
    printf '{"sha": "%s", "started": "%s", "ok": false, "failed_gate": "%s"}\n' \
      "$sha" "$now" "$gate" > "$MARKER"
    exit 1
  fi
done

printf '{"sha": "%s", "started": "%s", "ok": true, "gates": %d}\n' \
  "$sha" "$now" "${#GATES[@]}" > "$MARKER"
echo "── all gates green; marker: $MARKER" | tee -a "$LOG"
