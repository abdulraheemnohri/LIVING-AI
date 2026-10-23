#!/usr/bin/env bash
# Safe fast-forward updater for LIVING-AI on Debian/Linux, including Android Linux terminals.
set -Eeuo pipefail
cd "$(dirname "$0")/.."

command -v git >/dev/null 2>&1 || { echo "Git is required." >&2; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "Run this script from a Git checkout of LIVING-AI." >&2; exit 1;
}
[[ -x .venv/bin/python ]] || {
  echo "Virtual environment not found. Run: bash scripts/install_android_debian.sh" >&2; exit 1;
}

branch="$(git branch --show-current)"
[[ "$branch" == "main" ]] || {
  echo "Refusing to update branch '$branch'. Switch to main and retry." >&2; exit 1;
}
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree has local changes. Commit or back them up before updating:" >&2
  git status --short
  exit 1
fi

old_head="$(git rev-parse HEAD)"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="backups/update-$timestamp"
mkdir -p "$backup_dir"

# Preserve local config and data before updating code.
[[ ! -f .env ]] || cp -p .env "$backup_dir/.env"
[[ ! -d data ]] || tar -czf "$backup_dir/data.tar.gz" data

rollback() {
  status=$?
  if [[ $status -ne 0 ]]; then
    echo "Update failed; attempting code rollback to $old_head." >&2
    git reset --hard "$old_head" || echo "WARNING: automatic code rollback failed." >&2
    echo "Configuration/data backup retained at: $backup_dir" >&2
    echo "Dependencies may have changed; inspect the error before restarting." >&2
  fi
  exit "$status"
}
trap rollback ERR

git fetch --prune origin
git merge-base --is-ancestor HEAD origin/main || {
  echo "Local main is not an ancestor of origin/main; refusing a non-fast-forward update." >&2
  false
}
git merge --ff-only origin/main

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m compileall -q living_ai
if command -v node >/dev/null 2>&1 && [[ -f static/app.js ]]; then
  node --check static/app.js
  [[ ! -f static/tasks.js ]] || node --check static/tasks.js
fi
python -m pytest -q

trap - ERR
echo
echo "Update completed and checks passed."
echo "Previous code: $old_head"
echo "Current code:  $(git rev-parse HEAD)"
echo "Backup:        $backup_dir"
