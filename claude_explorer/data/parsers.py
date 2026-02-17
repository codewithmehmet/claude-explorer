"""Parsers for all .claude data sources."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import (
    DailyStats,
    FileChange,
    Plan,
    Project,
    Prompt,
    Session,
    SessionMessage,
)

CLAUDE_DIR = Path.home() / ".claude"


def parse_history() -> list[Prompt]:
    """Parse history.jsonl into a list of prompts."""
    history_file = CLAUDE_DIR / "history.jsonl"
    if not history_file.exists():
        return []

    prompts = []
    with open(history_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ts = data.get("timestamp", 0)
                prompts.append(Prompt(
                    text=data.get("display", ""),
                    timestamp=datetime.fromtimestamp(ts / 1000) if ts else datetime.min,
                    project=data.get("project", "unknown"),
                    session_id=data.get("sessionId", ""),
                ))
            except (json.JSONDecodeError, ValueError):
                continue
    return sorted(prompts, key=lambda p: p.timestamp, reverse=True)


def parse_stats() -> list[DailyStats]:
    """Parse stats-cache.json into daily stats."""
    stats_file = CLAUDE_DIR / "stats-cache.json"
    if not stats_file.exists():
        return []

    try:
        with open(stats_file, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []

    stats = []
    for day in data.get("dailyActivity", []):
        stats.append(DailyStats(
            date=day.get("date", ""),
            message_count=day.get("messageCount", 0),
            session_count=day.get("sessionCount", 0),
            tool_call_count=day.get("toolCallCount", 0),
        ))
    return sorted(stats, key=lambda s: s.date)


def discover_projects() -> list[Project]:
    """Discover all projects with their sessions."""
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []

    projects = []
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir():
            continue

        name = entry.name
        home_encoded = str(Path.home()).replace("/", "-")
        display = (name
                   .replace(home_encoded + "-Projects-", "")
                   .replace(home_encoded + "-", "~/")
                   .replace(home_encoded, "~/")
                   .lstrip("-")
                   .replace("~/-", "~/."))
        if not display:
            display = name

        jsonl_files = list(entry.glob("*.jsonl"))
        total_size = sum(f.stat().st_size for f in jsonl_files)

        sessions = []
        for jf in jsonl_files:
            sid = jf.stem
            stat = jf.stat()
            sessions.append(Session(
                session_id=sid,
                project=display,
                project_path=name,
                jsonl_path=jf,
                jsonl_size=stat.st_size,
                last_activity=datetime.fromtimestamp(stat.st_mtime),
            ))
        sessions.sort(key=lambda s: s.last_activity or datetime.min, reverse=True)

        projects.append(Project(
            name=name,
            path=str(entry),
            display_name=display,
            sessions=sessions,
            total_size=total_size,
            session_count=len(jsonl_files),
        ))

    return sorted(projects, key=lambda p: p.total_size, reverse=True)


def discover_all_sessions() -> list[Session]:
    """Discover all sessions across all projects."""
    history = parse_history()

    # Build a map of session_id -> prompts from history
    session_prompts: dict[str, list[Prompt]] = {}
    for p in history:
        session_prompts.setdefault(p.session_id, []).append(p)

    projects = discover_projects()
    sessions = []

    for proj in projects:
        for session in proj.sessions:
            # Enrich with prompt data from history
            prompts = session_prompts.get(session.session_id, [])
            if prompts:
                session.prompt_count = len(prompts)
                session.first_activity = min(p.timestamp for p in prompts)
                ts_from_prompts = max(p.timestamp for p in prompts)
                if session.last_activity is None or ts_from_prompts > session.last_activity:
                    session.last_activity = ts_from_prompts
            sessions.append(session)

    return sorted(sessions, key=lambda s: s.last_activity or datetime.min, reverse=True)


def parse_session_transcript(jsonl_path: Path, max_messages: int = 500) -> list[SessionMessage]:
    """Parse a session JSONL file into messages."""
    if not jsonl_path.exists():
        return []

    messages = []
    count = 0

    with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if count >= max_messages:
                break
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")
            ts_str = data.get("timestamp")
            ts = None
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            if msg_type == "user":
                # User message - content can be string or list
                content = ""
                msg_data = data.get("message", {})
                if isinstance(msg_data, dict):
                    parts = msg_data.get("content", "")
                    if isinstance(parts, str):
                        content = parts
                    elif isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict) and part.get("type") == "text":
                                content += part.get("text", "")
                            elif isinstance(part, str):
                                content += part
                # Filter out system/command content
                clean = content.strip()
                if clean and not clean.startswith("<command-"):
                    messages.append(SessionMessage(
                        role="user",
                        content=clean,
                        timestamp=ts,
                        message_type="user",
                    ))
                    count += 1

            elif msg_type == "assistant":
                msg_data = data.get("message", {})
                if isinstance(msg_data, dict):
                    parts = msg_data.get("content", [])
                    if isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict):
                                if part.get("type") == "text" and part.get("text", "").strip():
                                    messages.append(SessionMessage(
                                        role="assistant",
                                        content=part["text"].strip(),
                                        timestamp=ts,
                                        message_type="text",
                                    ))
                                    count += 1
                                elif part.get("type") == "tool_use":
                                    tool_name = part.get("name", "unknown")
                                    tool_input = part.get("input", {})
                                    summary = _summarize_tool_use(tool_name, tool_input)
                                    messages.append(SessionMessage(
                                        role="tool",
                                        content=summary,
                                        timestamp=ts,
                                        tool_name=tool_name,
                                        message_type="tool_use",
                                    ))
                                    count += 1
                    elif isinstance(parts, str) and parts.strip():
                        messages.append(SessionMessage(
                            role="assistant",
                            content=parts.strip(),
                            timestamp=ts,
                            message_type="text",
                        ))
                        count += 1

            elif msg_type == "summary":
                content = data.get("summary", "")
                if content:
                    messages.append(SessionMessage(
                        role="system",
                        content=f"[Summary] {content[:200]}",
                        timestamp=ts,
                        message_type="summary",
                    ))
                    count += 1

            elif msg_type == "system":
                subtype = data.get("subtype", "")
                content = data.get("content", "")
                if subtype and content:
                    messages.append(SessionMessage(
                        role="system",
                        content=f"[{subtype}] {content[:150]}",
                        timestamp=ts,
                        message_type="system",
                    ))
                    count += 1

    return messages


def _summarize_tool_use(tool_name: str, tool_input: dict) -> str:
    """Create a short summary of a tool use."""
    if tool_name == "Read":
        return f"Read {tool_input.get('file_path', '?')}"
    elif tool_name == "Write":
        return f"Write {tool_input.get('file_path', '?')}"
    elif tool_name == "Edit":
        return f"Edit {tool_input.get('file_path', '?')}"
    elif tool_name == "Bash":
        cmd = tool_input.get("command", "?")
        return f"$ {cmd[:100]}"
    elif tool_name == "Glob":
        return f"Glob {tool_input.get('pattern', '?')}"
    elif tool_name == "Grep":
        return f"Grep '{tool_input.get('pattern', '?')}'"
    elif tool_name == "Task":
        return f"Task: {tool_input.get('description', '?')}"
    elif tool_name == "WebSearch":
        return f"Search: {tool_input.get('query', '?')}"
    else:
        return f"{tool_name}()"


def parse_plans() -> list[Plan]:
    """Parse all plan files."""
    plans_dir = CLAUDE_DIR / "plans"
    if not plans_dir.exists():
        return []

    plans = []
    for f in sorted(plans_dir.glob("*.md")):
        stat = f.stat()
        plans.append(Plan(
            name=f.stem.replace("-", " ").title(),
            path=f,
            modified=datetime.fromtimestamp(stat.st_mtime),
            size=stat.st_size,
        ))
    return sorted(plans, key=lambda p: p.modified or datetime.min, reverse=True)


def read_plan_content(plan: Plan) -> str:
    """Read full content of a plan."""
    try:
        return plan.path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "(Could not read plan)"


def parse_file_history() -> dict[str, list[str]]:
    """Parse file history - returns session_id -> list of file paths."""
    fh_dir = CLAUDE_DIR / "file-history"
    if not fh_dir.exists():
        return {}

    result = {}
    for session_dir in fh_dir.iterdir():
        if session_dir.is_dir():
            files = []
            for f in session_dir.rglob("*"):
                if f.is_file():
                    files.append(str(f.relative_to(session_dir)))
            if files:
                result[session_dir.name] = sorted(files)
    return result


def get_global_stats() -> dict:
    """Get aggregate stats for the dashboard."""
    stats = parse_stats()
    history = parse_history()
    projects = discover_projects()

    total_messages = sum(s.message_count for s in stats)
    total_sessions = sum(s.session_count for s in stats)
    total_tools = sum(s.tool_call_count for s in stats)
    total_prompts = len(history)
    total_projects = len([p for p in projects if p.session_count > 0])
    total_data = sum(p.total_size for p in projects)

    # Date range
    first_date = stats[0].date if stats else "?"
    last_date = stats[-1].date if stats else "?"

    return {
        "total_messages": total_messages,
        "total_sessions": total_sessions,
        "total_tools": total_tools,
        "total_prompts": total_prompts,
        "total_projects": total_projects,
        "total_data_bytes": total_data,
        "first_date": first_date,
        "last_date": last_date,
        "daily_stats": stats,
        "active_days": len(stats),
    }
