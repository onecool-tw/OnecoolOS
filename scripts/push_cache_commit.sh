#!/usr/bin/env bash
# Publish an already committed cache update without overwriting remote work.
set -euo pipefail
snapshot=data/public/taiwan_stock_family_latest.json
context=data/market/taiwan_stock_intelligence/daily_context_latest.json

rebuild_taiwan_snapshot() {
  # Rebuild from synchronized formal inputs; never calculate signals or pressure.
  python -m scripts.refresh_taiwan_final_context
  python scripts/export_taiwan_family_snapshot.py --check
  git add "$context" "$snapshot"
  if ! git diff --cached --quiet; then
    if [[ $(git rev-list --count origin/main..HEAD) == 1 ]]; then
      git commit --amend --no-edit
    else
      git commit -m "Rebuild Taiwan snapshot from synchronized formal inputs"
    fi
  fi
}

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "::error::Commit cache changes before publication; refusing uncommitted edits."
  exit 2
fi
for attempt in 1 2 3; do
  echo "Publish attempt ${attempt}/3"
  local_head=$(git rev-parse HEAD)
  snapshot_changed=false
  if ! git diff-tree --quiet "$local_head^" "$local_head" -- "$snapshot"; then
    snapshot_changed=true
  fi
  if ! git pull --rebase origin main; then
    mapfile -t conflicts < <(git diff --name-only --diff-filter=U)
    # Only a single generated projection may be replaced during an Actions
    # cache commit. A context/price/CTA/pressure conflict must still stop.
    if [[ "${GITHUB_ACTIONS:-}" == true && "$snapshot_changed" == true &&
          ${#conflicts[@]} == 1 && "${conflicts[0]}" == "$snapshot" &&
          $(git rev-list --count "origin/main..$local_head") == 1 ]]; then
      echo "Concurrent derived Taiwan snapshot; rebuild after synchronizing formal inputs."
      # During rebase 'ours' is the fetched remote projection. It is only a
      # temporary placeholder and must pass regeneration before any push.
      git checkout --ours -- "$snapshot"
      git add "$snapshot"
      if ! GIT_EDITOR=true git rebase --continue; then
        git rebase --abort || true
        exit 1
      fi
    else
      git rebase --abort || true
      echo "::error::Overlapping source cache changes require recomputation; refusing overwrite."
      exit 1
    fi
  fi
  # Even a clean textual rebase can leave a projection using old source hashes.
  if [[ "$snapshot_changed" == true && $(git rev-parse HEAD) != "$local_head" ]]; then
    rebuild_taiwan_snapshot
  fi
  if git push origin HEAD:main; then
    exit 0
  fi
done
echo "::error::Cache push failed after 3 synchronized attempts."
exit 1
