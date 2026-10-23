#!/usr/bin/env bash
# Read-only update checker. It never merges, resets, installs packages, or restarts the app.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
command -v git >/dev/null 2>&1 || { echo "Git is required." >&2; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Run inside a LIVING-AI Git checkout." >&2; exit 1; }
branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  echo "Current branch: $branch (updates are checked against origin/main)."
fi
git fetch --prune origin
local_head="$(git rev-parse HEAD)"
remote_ref="origin/main"
git rev-parse --verify "$remote_ref" >/dev/null 2>&1 || { echo "Remote origin/main is unavailable." >&2; exit 1; }
remote_head="$(git rev-parse "$remote_ref")"
echo "Local:  $local_head"
echo "Remote: $remote_head"
if [[ "$local_head" == "$remote_head" ]]; then
  echo "LIVING-AI is up to date with origin/main."
  exit 0
fi
if git merge-base --is-ancestor "$local_head" "$remote_head"; then
  count="$(git rev-list --count "$local_head..$remote_ref")"
  echo "Update available: $count commit(s) behind origin/main."
  git --no-pager log --oneline --decorate "$local_head..$remote_ref"
  echo "Review the commits, then run: bash scripts/update_android_debian.sh"
  exit 0
fi
if git merge-base --is-ancestor "$remote_head" "$local_head"; then
  echo "Local branch contains commits not present in origin/main; no update needed."
  exit 0
fi
echo "Local and remote histories diverged. Resolve manually; the updater will refuse this state." >&2
exit 2
