# PM-Dev Playbook (Claude PM + Codex Dev)

## Workflow
1. `claude-pm` adds a task in `TASK_DIRECTIVE.md` via `agent_coord.py add-task`.
2. `codex-dev` executes implementation and posts progress using `agent_coord.py log`.
3. DB-centric tasks are temporarily handled by `codex-dev` (gemini-db paused).
4. `codex-dev` closes the task using `agent_coord.py complete-task`.
5. Completion auto-writes `WORK_LOG.md` and runs archive compaction check.

## Ownership Rules
- PM owns prioritization, scope control, acceptance criteria.
- Dev owns implementation details, tests, and technical risk notes.
- DB responsibilities are currently under `codex-dev` ownership.
- Every completed task must include a completion summary in `--summary`.

## Required Logging
- Start log:
  - `action:log` with plan or implementation start note.
- Finish log:
  - `action:complete` via `complete-task`.
- Optional handoff log:
  - PM can add a review note with `action:log`.

## Naming Convention
- task id: `T-YYYYMMDD-XXX`
- owner: `claude-pm`, `codex-dev`, or `shared`
- priority: `P1`, `P2`, `P3`

## Command Examples
- Add:
  - `python scripts/agent_coord.py add-task --title "..." --owner claude-pm --priority P1 --details "..."`
- Add DB task (temporary):
  - `python scripts/agent_coord.py add-task --title "..." --owner codex-dev --priority P1 --details "..."`
- Progress log:
  - `python scripts/agent_coord.py log --agent codex-dev --task-id T-YYYYMMDD-001 --message "..."`
- Complete:
  - `python scripts/agent_coord.py complete-task --id T-YYYYMMDD-001 --agent codex-dev --summary "..."`
