"""
Agent collaboration coordinator.

Manages:
- agents/TASK_DIRECTIVE.md
- agents/WORK_LOG.md
- agents/archive/TASK_ARCHIVE_YYYY-MM.md
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"
DIRECTIVE_PATH = AGENTS_DIR / "TASK_DIRECTIVE.md"
LOG_PATH = AGENTS_DIR / "WORK_LOG.md"
ARCHIVE_DIR = AGENTS_DIR / "archive"

ACTIVE_START = "<!-- ACTIVE_TASKS_START -->"
ACTIVE_END = "<!-- ACTIVE_TASKS_END -->"
DONE_START = "<!-- COMPLETED_TASKS_START -->"
DONE_END = "<!-- COMPLETED_TASKS_END -->"

ARCHIVE_THRESHOLD_LINES = 220
ARCHIVE_TARGET_LINES = 170

TASK_LINE_RE = re.compile(r"^- \[(?P<done>[ xX])\] (?P<id>[^|]+)\| (?P<rest>.+)$")


@dataclass
class Task:
    done: bool
    task_id: str
    title: str
    owner: str
    priority: str
    status: str
    created: str
    details: str
    completed: str | None = None

    def to_line(self) -> str:
        mark = "x" if self.done else " "
        parts = [
            f"- [{mark}] {self.task_id}",
            self.title,
            f"owner:{self.owner}",
            f"priority:{self.priority}",
            f"status:{self.status}",
            f"created:{self.created}",
        ]
        if self.completed:
            parts.append(f"completed:{self.completed}")
        parts.append(f"details:{self.details}")
        return " | ".join(parts)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def sanitize(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ").strip()


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def find_marker_indices(lines: list[str], start: str, end: str) -> tuple[int, int]:
    try:
        s_idx = lines.index(start)
        e_idx = lines.index(end)
    except ValueError as exc:
        raise RuntimeError(f"Missing marker in {DIRECTIVE_PATH}: {start} or {end}") from exc
    if s_idx >= e_idx:
        raise RuntimeError(f"Invalid marker ordering for {start} and {end}")
    return s_idx, e_idx


def extract_section(lines: list[str], start: str, end: str) -> tuple[list[str], tuple[int, int]]:
    s_idx, e_idx = find_marker_indices(lines, start, end)
    return lines[s_idx + 1 : e_idx], (s_idx, e_idx)


def parse_task_line(line: str) -> Task | None:
    line = line.strip()
    match = TASK_LINE_RE.match(line)
    if not match:
        return None

    done = match.group("done").lower() == "x"
    task_id = match.group("id").strip()
    chunks = [chunk.strip() for chunk in match.group("rest").split("|")]
    if not chunks:
        return None

    title = chunks[0]
    fields: dict[str, str] = {}
    for chunk in chunks[1:]:
        if ":" not in chunk:
            continue
        key, value = chunk.split(":", 1)
        fields[key.strip()] = value.strip()

    return Task(
        done=done,
        task_id=task_id,
        title=title,
        owner=fields.get("owner", "unassigned"),
        priority=fields.get("priority", "P2"),
        status=fields.get("status", "active"),
        created=fields.get("created", today_str()),
        details=fields.get("details", ""),
        completed=fields.get("completed"),
    )


def parse_tasks(section_lines: list[str]) -> list[Task]:
    tasks: list[Task] = []
    for line in section_lines:
        task = parse_task_line(line)
        if task:
            tasks.append(task)
    return tasks


def render_tasks(tasks: list[Task], empty_token: str = "_none_") -> list[str]:
    if not tasks:
        return [empty_token]
    return [task.to_line() for task in tasks]


def load_directive() -> tuple[list[str], list[Task], list[Task], tuple[int, int], tuple[int, int]]:
    lines = read_lines(DIRECTIVE_PATH)
    if not lines:
        raise RuntimeError(f"{DIRECTIVE_PATH} not found or empty")

    active_lines, active_bounds = extract_section(lines, ACTIVE_START, ACTIVE_END)
    done_lines, done_bounds = extract_section(lines, DONE_START, DONE_END)
    active_tasks = parse_tasks(active_lines)
    done_tasks = parse_tasks(done_lines)
    return lines, active_tasks, done_tasks, active_bounds, done_bounds


def save_directive(lines: list[str], active_tasks: list[Task], done_tasks: list[Task]) -> None:
    a_s, a_e = find_marker_indices(lines, ACTIVE_START, ACTIVE_END)
    d_s, d_e = find_marker_indices(lines, DONE_START, DONE_END)

    new_lines = (
        lines[: a_s + 1]
        + render_tasks(active_tasks)
        + lines[a_e:d_s + 1]
        + render_tasks(done_tasks)
        + lines[d_e:]
    )
    write_lines(DIRECTIVE_PATH, new_lines)


def append_log(agent: str, task_id: str | None, action: str, message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text("# Agent Work Log\n\n## Entries\n", encoding="utf-8")
    line = (
        f"- {now_str()} | agent:{sanitize(agent)} | task:{sanitize(task_id or '-')} "
        f"| action:{sanitize(action)} | message:{sanitize(message)}"
    )
    with LOG_PATH.open("a", encoding="utf-8") as f:
        if LOG_PATH.stat().st_size > 0 and not read_lines(LOG_PATH)[-1].strip():
            f.write(line + "\n")
        else:
            f.write("\n" + line + "\n")


def next_task_id(active_tasks: list[Task], done_tasks: list[Task]) -> str:
    date_key = datetime.now().strftime("%Y%m%d")
    prefix = f"T-{date_key}-"
    existing = [task.task_id for task in (active_tasks + done_tasks) if task.task_id.startswith(prefix)]
    nums = []
    for task_id in existing:
        parts = task_id.split("-")
        if len(parts) == 3 and parts[-1].isdigit():
            nums.append(int(parts[-1]))
        elif len(parts) == 4 and parts[-1].isdigit():
            nums.append(int(parts[-1]))
    next_num = (max(nums) + 1) if nums else 1
    return f"{prefix}{next_num:03d}"


def auto_archive() -> int:
    lines, active_tasks, done_tasks, _, _ = load_directive()
    current_line_count = len(lines)
    if current_line_count <= ARCHIVE_THRESHOLD_LINES:
        return 0

    archived: list[Task] = []
    # Oldest completed tasks are at the end.
    while len(lines) > ARCHIVE_TARGET_LINES and done_tasks:
        archived.append(done_tasks.pop(-1))
        save_directive(lines, active_tasks, done_tasks)
        lines = read_lines(DIRECTIVE_PATH)

    if not archived:
        return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    month_key = datetime.now().strftime("%Y-%m")
    archive_file = ARCHIVE_DIR / f"TASK_ARCHIVE_{month_key}.md"
    if not archive_file.exists():
        archive_file.write_text(
            f"# Task Archive {month_key}\n\n## Completed Tasks\n",
            encoding="utf-8",
        )

    with archive_file.open("a", encoding="utf-8") as f:
        for task in archived:
            f.write(task.to_line() + "\n")

    return len(archived)


def cmd_add_task(args: argparse.Namespace) -> int:
    lines, active_tasks, done_tasks, _, _ = load_directive()
    task = Task(
        done=False,
        task_id=next_task_id(active_tasks, done_tasks),
        title=sanitize(args.title),
        owner=sanitize(args.owner),
        priority=sanitize(args.priority),
        status="active",
        created=today_str(),
        details=sanitize(args.details or ""),
    )
    active_tasks.append(task)
    save_directive(lines, active_tasks, done_tasks)
    append_log(args.agent, task.task_id, "add-task", f"created task: {task.title}")
    auto_archive()
    print(task.task_id)
    return 0


def cmd_complete_task(args: argparse.Namespace) -> int:
    lines, active_tasks, done_tasks, _, _ = load_directive()
    target_idx = None
    for idx, task in enumerate(active_tasks):
        if task.task_id == args.id:
            target_idx = idx
            break
    if target_idx is None:
        print(f"Task not found in active tasks: {args.id}", file=sys.stderr)
        return 1

    task = active_tasks.pop(target_idx)
    task.done = True
    task.status = "done"
    task.completed = today_str()
    if args.summary:
        task.details = sanitize(args.summary)
    done_tasks.insert(0, task)
    save_directive(lines, active_tasks, done_tasks)
    append_log(args.agent, task.task_id, "complete", args.summary or f"completed: {task.title}")
    archived_count = auto_archive()
    if archived_count:
        append_log(args.agent, task.task_id, "archive", f"auto-archived {archived_count} completed tasks")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    append_log(args.agent, args.task_id, "log", args.message)
    return 0


def cmd_archive(_: argparse.Namespace) -> int:
    count = auto_archive()
    print(f"archived={count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent collaboration coordinator")
    sub = parser.add_subparsers(dest="command", required=True)
    agent_choices = ["claude-pm", "codex-dev", "shared"]

    p_add = sub.add_parser("add-task", help="Add active task")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--owner", required=True, choices=agent_choices)
    p_add.add_argument("--priority", default="P2", choices=["P1", "P2", "P3"])
    p_add.add_argument("--details", default="")
    p_add.add_argument("--agent", default="claude-pm")
    p_add.set_defaults(func=cmd_add_task)

    p_done = sub.add_parser("complete-task", help="Complete active task and log")
    p_done.add_argument("--id", required=True)
    p_done.add_argument("--agent", required=True, choices=agent_choices)
    p_done.add_argument("--summary", default="")
    p_done.set_defaults(func=cmd_complete_task)

    p_log = sub.add_parser("log", help="Append a log entry")
    p_log.add_argument("--agent", required=True, choices=agent_choices)
    p_log.add_argument("--task-id", default="-")
    p_log.add_argument("--message", required=True)
    p_log.set_defaults(func=cmd_log)

    p_archive = sub.add_parser("archive", help="Manually run archive compaction")
    p_archive.set_defaults(func=cmd_archive)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
