#!/usr/bin/env bash
# Publish an already committed cache update without overwriting remote work.
set -euo pipefail
for attempt in 1 2 3; do
  echo "Publish attempt ${attempt}/3"
  if ! git pull --rebase origin main; then
    git rebase --abort || true
    echo "::error::Overlapping cache changes require recomputation; refusing overwrite."
    exit 1
  fi
  if git push origin HEAD:main; then
    exit 0
  fi
done
echo "::error::Cache push failed after 3 synchronized attempts."
exit 1
