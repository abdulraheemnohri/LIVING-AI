# GitHub Updates and Project Workspace

Last reviewed: 2026-10-23

## GitHub update workflow

The supported update path is a **safe fast-forward update from `origin/main`** on the Android Debian/Linux checkout. It is deliberately not a silent background self-modifier: an AI process should not overwrite running code, ignore local edits, or promote untested changes.

Run from the repository root. First check whether updates are available without changing the checked-out code:

```bash
bash scripts/check_github_updates.sh
```

When you are ready to apply an update, run:

```bash
bash scripts/update_android_debian.sh
```

The updater:
1. verifies Git, the checkout, `.venv`, branch `main`, and a clean working tree;
2. saves `.env` and `data/` to a timestamped `backups/update-*/` directory;
3. fetches GitHub and refuses non-fast-forward updates;
4. applies only a fast-forward update from `origin/main`;
5. installs declared development dependencies, compiles Python, syntax-checks the dashboard when Node.js is available, and runs tests;
6. attempts a code rollback to the previous commit on failure and leaves the backup for inspection.

Keep important data backups outside the repository too. The updater does not guarantee rollback of installed Python packages, and it does not restart an already-running server automatically.

### Suggested automation levels

- **Manual (default):** run the script when ready to update.
- **Scheduled notification/check:** use a scheduler to run `git fetch` and report whether `origin/main` is ahead; do not merge or restart automatically.
- **Opt-in unattended update:** only after adding a reviewed wrapper that requires a clean checkout, creates an external backup, enforces a maintenance window, runs all checks, logs output, and rolls back on failure. Keep it disabled by default on a phone.
- **GitHub CI:** pushes and pull requests run syntax, startup and test checks. A green CI run is evidence for that commit, not a guarantee for every Android architecture or optional model backend.

Do not store GitHub personal access tokens in scripts or commit them to the repository. Public repositories can fetch without a token; private repositories should use a narrowly scoped credential manager or SSH key.

## Project management API

Project management is protected by `LIVING_AI_ADMIN_PASSWORD` and the `X-Admin-Password` request header. Without the password, endpoints fail closed. Do not expose this dashboard to an untrusted network without TLS and a stronger access-control boundary.

Endpoints:
- `GET/POST /api/projects`
- `PATCH/DELETE /api/projects/{project_id}`
- `GET/POST /api/projects/{project_id}/items`
- `PATCH/DELETE /api/projects/{project_id}/items/{item_id}`
- `GET/POST /api/projects/{project_id}/milestones`
- `PATCH/DELETE /api/projects/{project_id}/milestones/{milestone_id}`
- `GET /api/projects/{project_id}/activity`
- `GET /api/projects/export`
- `POST /api/projects/import`

Project, milestone, task and activity records are stored in SQLite under the configured data directory. Export is a versioned JSON backup. Import creates new records rather than overwriting existing records. Review the JSON backup before importing it; never import files from untrusted sources without inspection.

Task dependencies must reference another task in the same project and cycles are rejected. Deleting a prerequisite clears dependent tasks' links and records an activity event.

## Troubleshooting

- **Local changes block update:** inspect `git status --short`; commit or copy your work before retrying. Do not blindly discard edits.
- **Branch is not main:** inspect your branch and switch only if that is intended.
- **Update says local main is not an ancestor:** inspect `git log --oneline --graph --decorate --all -20`; do not force-reset automatically.
- **Tests fail:** inspect the first failing test, retain the backup, fix the issue, and rerun tests before restarting.
- **Model download or memory issue:** app code updates do not update or download multi-gigabyte model artifacts. Keep model artifacts separate and verify runtime/device compatibility.
- **Need to restore data:** stop the app first and restore the appropriate archive from a known backup after checking its contents.

## Maintenance checklist

Before a release: review `README.md`, `docs/PROJECT_A_TO_Z.md`, `docs/PROJECT_MANAGEMENT.md`, environment examples, installation/update scripts, test coverage, security defaults, and the CI run. Update the "last reviewed" dates only after checking the relevant files.
