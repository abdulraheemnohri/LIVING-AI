# Project Management Workspace

Last reviewed: 2026-10-23

## Scope

The Projects workspace is a lightweight local SQLite project tracker inside LIVING-AI. It is not a GitHub issue/PR mirror yet; GitHub source-code updates are handled separately by `scripts/update_android_debian.sh`.

## Current capabilities

- Create, update, list and delete projects.
- Project status: active, on hold, completed, archived.
- Project priority: low, medium, high, critical.
- Optional due dates and descriptions.
- Work items with todo, in progress, blocked and done states.
- Task priority and due date.
- Task dependency links; cross-project links, self-dependencies and dependency cycles are rejected.
- Milestones with planned, in-progress, completed and at-risk statuses.
- Per-project activity history.
- Progress summary based on completed work items.
- Versioned JSON export and additive import; existing records are not overwritten.
- Authenticated endpoints fail closed if `LIVING_AI_ADMIN_PASSWORD` is unset.

## API routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/projects` | List projects and aggregate progress |
| POST | `/api/projects` | Create a project |
| PATCH | `/api/projects/{project_id}` | Update a project |
| DELETE | `/api/projects/{project_id}` | Delete a project |
| GET | `/api/projects/{project_id}/items` | List tasks |
| POST | `/api/projects/{project_id}/items` | Create a task |
| PATCH | `/api/projects/{project_id}/items/{item_id}` | Update a task |
| DELETE | `/api/projects/{project_id}/items/{item_id}` | Delete a task |
| GET / POST | `/api/projects/{project_id}/milestones` | List/create milestones |
| PATCH / DELETE | `/api/projects/{project_id}/milestones/{milestone_id}` | Update/delete milestones |
| GET | `/api/projects/{project_id}/activity` | Read recent activity |
| GET | `/api/projects/export` | Export a versioned backup |
| POST | `/api/projects/import` | Import records as new projects |

All endpoints require the `X-Admin-Password` header matching `LIVING_AI_ADMIN_PASSWORD`.

## Local setup

```bash
bash scripts/install_android_debian.sh
source .venv/bin/activate
export LIVING_AI_ADMIN_PASSWORD='use-a-long-unique-password'
bash scripts/run.sh
```

Keep secrets out of shell history where possible and never commit them. The API currently uses a shared admin password, not per-user accounts or roles. Treat the dashboard as a trusted local tool and do not expose it directly to the public internet.

## Backup and restore

1. Export through the dashboard or `GET /api/projects/export`.
2. Store the JSON file outside the project directory and review it before sharing.
3. To import, send the file's JSON to `POST /api/projects/import`.
4. Import creates new records and remaps project/task/milestone identifiers; it does not replace existing records.
5. Keep an independent backup of the SQLite database before major changes.

## Roadmap — not yet implemented

These are follow-up features, not claims about the current app:
- Schedule/overdue dashboard, critical path and risk summaries.
- GitHub repository connection: repository selector, branch/commit/PR/issues sync, webhook or polling status, last-sync metadata, and conflict resolution.
- Two-way mapping between GitHub Issues and project work items.
- Per-project roles, audit export and stronger session-based authentication.
- Automated update notifications and optional scheduled updater with explicit opt-in, health checks, backup and rollback.

GitHub integration should use minimum-scope credentials, treat repository content as untrusted, avoid running code from commits automatically, and show a diff/preview before importing issues or metadata. Application updates should remain a separate, reviewed operation.
