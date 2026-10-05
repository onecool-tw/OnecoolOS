#!/usr/bin/env bash
# Merge formal inputs only; never fetch prices, calculate CTA, pressure or scores.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "Requires a disposable Actions checkout." >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Refusing to discard uncommitted changes." >&2
  exit 2
fi
git config user.name "onecool-os-bot"
git config user.email "actions@users.noreply.github.com"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
for attempt in 1 2 3; do
  echo "Taiwan final context publish attempt ${attempt}/3"
  git fetch origin main
  git reset --hard origin/main
  : > "$scratch/outputs"
  : > "$scratch/summary"
  python scripts/check_taiwan_regression.py --output data/market/taiwan_stock_intelligence/regression_latest.json
  python scripts/refresh_taiwan_final_context.py
  python scripts/export_taiwan_family_snapshot.py --check
  GITHUB_OUTPUT="$scratch/outputs" GITHUB_STEP_SUMMARY="$scratch/summary" \
    python scripts/check_system_health.py --scope asia
  git add data/market/taiwan_stock_intelligence/daily_context_latest.json \
    data/market/taiwan_stock_intelligence/regression_latest.json \
    data/public/taiwan_stock_family_latest.json \
    data/market/system_health/system_health_latest.json
  if git diff --cached --quiet; then
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then cat "$scratch/outputs" >> "$GITHUB_OUTPUT"; fi
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then cat "$scratch/summary" >> "$GITHUB_STEP_SUMMARY"; fi
    exit 0
  fi
  git commit -m "Refresh Taiwan final context, snapshot and health"
  if git push origin HEAD:main; then
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then cat "$scratch/outputs" >> "$GITHUB_OUTPUT"; fi
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then cat "$scratch/summary" >> "$GITHUB_STEP_SUMMARY"; fi
    exit 0
  fi
  echo "Push rejected; rebuild all derived files from latest main."
done
echo "::error::Taiwan final context publication failed after 3 attempts."
exit 1
