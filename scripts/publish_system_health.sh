#!/usr/bin/env bash
# Recompute derived health on the latest inputs after any competing push.
set -euo pipefail

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "This publisher requires a disposable GitHub Actions checkout." >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Refusing to discard uncommitted changes." >&2
  exit 2
fi
scope="${1:-all}"
case "$scope" in all|morning|asia|weekly) ;; *) exit 2 ;; esac
git config user.name "onecool-os-bot"
git config user.email "actions@users.noreply.github.com"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

publish_outputs() {
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then cat "$scratch/outputs" >> "$GITHUB_OUTPUT"; fi
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then cat "$scratch/summary" >> "$GITHUB_STEP_SUMMARY"; fi
}

for attempt in 1 2 3; do
  echo "Health publish attempt ${attempt}/3"
  git fetch origin main
  # Only disposable Actions checkouts reach here. Never force-push or rebase
  # the old derived report over newer input caches.
  git reset --hard origin/main
  : > "$scratch/outputs"
  : > "$scratch/summary"
  GITHUB_OUTPUT="$scratch/outputs" GITHUB_STEP_SUMMARY="$scratch/summary" \
    python scripts/check_system_health.py --scope "$scope"
  git add data/market/system_health/system_health_latest.json
  if git diff --cached --quiet; then
    publish_outputs
    exit 0
  fi
  git commit -m "Update unified schedule health"
  if git push origin HEAD:main; then
    publish_outputs
    exit 0
  fi
  echo "Push rejected; recompute health from current main before retrying."
done
echo "::error::Health publication failed after 3 attempts."
exit 1
