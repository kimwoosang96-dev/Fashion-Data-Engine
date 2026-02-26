# Agent Collaboration System

This folder is the shared operating system for multi-agent execution.

## Roles
- `claude-pm`: planning, prioritization, task assignment
- `codex-dev`: implementation, tests, delivery
- `gemini-db`: paused temporarily (as of 2026-02-27)

## Core Files
- `TASK_DIRECTIVE.md`: single task board (active + recent completed)
- `WORK_LOG.md`: append-only activity log for all agents
- `archive/`: archived completed tasks moved out automatically

## Task Line Schema
Use one line per task:

`- [ ] T-YYYYMMDD-XXX | <title> | owner:<agent> | priority:P1|P2|P3 | status:active | created:YYYY-MM-DD | details:<text>`

When completed:

`- [x] ... | status:done | ... | completed:YYYY-MM-DD | ...`

## Automation
Use:

`python scripts/agent_coord.py add-task --title "..." --owner claude-pm --priority P1 --details "..."`

`python scripts/agent_coord.py complete-task --id T-YYYYMMDD-XXX --agent codex-dev --summary "..."`

`python scripts/agent_coord.py log --agent claude-pm --task-id T-YYYYMMDD-XXX --message "..."`

`python scripts/agent_coord.py add-task --title "DB audit ..." --owner codex-dev --priority P1 --details "..."`

`python scripts/agent_coord.py archive`

`complete-task` always appends to `WORK_LOG.md` and then auto-runs archive check.

## Auto-Archive Rules
- Trigger when `TASK_DIRECTIVE.md` exceeds 220 lines.
- Oldest completed tasks are moved to monthly archive files in `archive/`.
- The directive is compacted to around 170 lines.
