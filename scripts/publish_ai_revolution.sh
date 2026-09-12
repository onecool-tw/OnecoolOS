#!/usr/bin/env bash
# Run only in the disposable GitHub Actions checkout. Never force-push.
set -euo pipefail

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "This publisher requires a disposable GitHub Actions checkout." >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Refusing to discard uncommitted changes." >&2
  exit 2
fi

git config user.name "onecool-os-bot"
git config user.email "actions@users.noreply.github.com"

for attempt in 1 2 3; do
  echo "AI evidence publish attempt ${attempt}/3"
  git fetch origin main
  # A rejected attempt exists only in this disposable checkout. Recompute on
  # current main, including any newer evidence/review from the weekly writer.
  git reset --hard origin/main
  python scripts/update_ai_revolution.py
  python scripts/validate_fund_intelligence.py
  python scripts/check_system_health.py --scope weekly
  git add data/market/ai_revolution data/market/fund_intelligence \
    data/market/system_health/system_health_latest.json
  if git diff --cached --quiet; then
    echo "AI evidence, validation and health are unchanged."
    exit 0
  fi
  git commit -m "Update AI Revolution evidence, validation and health"
  if git push origin HEAD:main; then
    exit 0
  fi
  echo "Push rejected; refresh against current main before retrying."
done

echo "::error::AI evidence publication failed after 3 attempts."
exit 1
