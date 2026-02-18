"""Parsers for all .claude data sources."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ClaudeJsonProject,
    DailyStats,
    GlobalStats,
    ModelUsage,
    Plan,
    Project,
    Prompt,
    Session,
    SessionMessage,
    SessionTodos,
    TodoItem,
    shorten_project_dir,
)

CLAUDE_DIR = Path.home() / ".claude"


# --- Cache layer ---

class DataCache:
    """In-memory cache for parsed data."""

    def __init__(self):
        self._history: list[Prompt] | None = None
        self._stats: list[DailyStats] | None = None
        self._projects: list[Project] | None = None
        self._sessions: list[Session] | None = None
        self._file_history: dict[str, list[str]] | None = None
        self._raw_stats_json: dict | None = None  # shared backing for model/hour/longest
        self._model_usages: list[ModelUsage] | None = None
        self._hour_counts: dict[int, int] | None = None
        self._longest_session: dict | None = None
        self._todos: list[SessionTodos] | None = None
        self._settings: dict | None = None
        self._claude_json_projects: list[ClaudeJsonProject] | None = None

    def invalidate(self):
        self._history = None
        self._stats = None
        self._projects = None
        self._sessions = None
        self._file_history = None
        self._raw_stats_json = None
        self._model_usages = None
        self._hour_counts = None
        self._longest_session = None
        self._todos = None
        self._settings = None
        self._claude_json_projects = None

    @property
    def history(self) -> list[Prompt]:
        if self._history is None:
            self._history = _parse_history()
        return self._history

    @property
    def stats(self) -> list[DailyStats]:
        if self._stats is None:
            self._stats = _parse_stats()
        return self._stats

    @property
    def projects(self) -> list[Project]:
        if self._projects is None:
            self._projects = _discover_projects()
        return self._projects

    @property
    def sessions(self) -> list[Session]:
        if self._sessions is None:
            self._sessions = _discover_all_sessions(self.history, self.projects)
        return self._sessions

    @property
    def file_history(self) -> dict[str, list[str]]:
        if self._file_history is None:
            self._file_history = _parse_file_history()
        return self._file_history

    @property
    def raw_stats_json(self) -> dict:
        if self._raw_stats_json is None:
            self._raw_stats_json = _load_stats_json()
        return self._raw_stats_json

    @property
    def model_usages(self) -> list[ModelUsage]:
        if self._model_usages is None:
            self._model_usages = _parse_model_usages(self.raw_stats_json)
        return self._model_usages

    @property
    def hour_counts(self) -> dict[int, int]:
        if self._hour_counts is None:
            self._hour_counts = _parse_hour_counts(self.raw_stats_json)
        return self._hour_counts

    @property
    def longest_session(self) -> dict:
        if self._longest_session is None:
            self._longest_session = _parse_longest_session(self.raw_stats_json)
        return self._longest_session

    @property
    def todos(self) -> list[SessionTodos]:
        if self._todos is None:
            self._todos = _parse_todos()
        return self._todos

    @property
    def settings(self) -> dict:
        if self._settings is None:
            self._settings = _parse_settings()
        return self._settings

    @property
    def claude_json_projects(self) -> list[ClaudeJsonProject]:
        if self._claude_json_projects is None:
            self._claude_json_projects = _parse_claude_json_projects()
        return self._claude_json_projects


cache = DataCache()


# --- Public API (use cache) ---

def parse_history() -> list[Prompt]:
    return cache.history

def parse_stats() -> list[DailyStats]:
    return cache.stats

def discover_projects() -> list[Project]:
    return cache.projects

def discover_all_sessions() -> list[Session]:
    return cache.sessions

def parse_file_history() -> dict[str, list[str]]:
    return cache.file_history

def parse_model_usages() -> list[ModelUsage]:
    return cache.model_usages

def parse_hour_counts() -> dict[int, int]:
    return cache.hour_counts

def parse_longest_session() -> dict:
    return cache.longest_session

def parse_todos() -> list[SessionTodos]:
    return cache.todos

def parse_settings() -> dict:
    return cache.settings

def parse_claude_json_projects() -> list[ClaudeJsonProject]:
    return cache.claude_json_projects

def refresh_data():
    """Invalidate all caches and force reload."""
    cache.invalidate()


# --- Internal parsers ---

def _parse_history() -> list[Prompt]:
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
                    timestamp=datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else datetime.min.replace(tzinfo=timezone.utc),
                    project=data.get("project", "unknown"),
                    session_id=data.get("sessionId", ""),
                ))
            except (json.JSONDecodeError, ValueError):
                continue
    return sorted(prompts, key=lambda p: p.timestamp, reverse=True)


def _parse_stats() -> list[DailyStats]:
    stats_file = CLAUDE_DIR / "stats-cache.json"
    if not stats_file.exists():
        return []

    try:
        with open(stats_file, "r", encoding="utf-8", errors="replace") as f:
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


def _discover_projects() -> list[Project]:
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []

    projects = []
    for entry in sorted(projects_dir.iterdir()):
        if not entry.is_dir():
            continue

        name = entry.name
        display = shorten_project_dir(name)

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
                last_activity=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            ))
        sessions.sort(key=lambda s: s.last_activity or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        projects.append(Project(
            name=name,
            path=str(entry),
            display_name=display,
            sessions=sessions,
            total_size=total_size,
            session_count=len(jsonl_files),
        ))

    return sorted(projects, key=lambda p: p.total_size, reverse=True)


def _discover_all_sessions(history: list[Prompt], projects: list[Project]) -> list[Session]:
    session_prompts: dict[str, list[Prompt]] = {}
    for p in history:
        session_prompts.setdefault(p.session_id, []).append(p)

    sessions = []
    for proj in projects:
        for session in proj.sessions:
            prompts = session_prompts.get(session.session_id, [])
            if prompts:
                session.prompt_count = len(prompts)
                session.first_activity = min(p.timestamp for p in prompts)
                ts_from_prompts = max(p.timestamp for p in prompts)
                if session.last_activity is None or ts_from_prompts > session.last_activity:
                    session.last_activity = ts_from_prompts
            sessions.append(session)

    return sorted(sessions, key=lambda s: s.last_activity or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


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
                                elif part.get("type") == "thinking":
                                    thinking = part.get("thinking", "").strip()
                                    if thinking:
                                        messages.append(SessionMessage(
                                            role="system",
                                            content=f"[Thinking] {thinking[:300]}",
                                            timestamp=ts,
                                            message_type="thinking",
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


def search_conversations(query: str, max_results: int = 50) -> list[dict]:
    """Deep search across all session transcripts."""
    query_lower = query.lower()
    results = []
    sessions = discover_all_sessions()

    for session in sessions:
        if len(results) >= max_results:
            break
        if not session.jsonl_path or not session.jsonl_path.exists():
            continue
        # Only search sessions with data
        if session.jsonl_size < 100:
            continue

        try:
            with open(session.jsonl_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if len(results) >= max_results:
                        break
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg_type = data.get("type", "")
                    text = ""

                    if msg_type == "user":
                        msg = data.get("message", {})
                        if isinstance(msg, dict):
                            c = msg.get("content", "")
                            if isinstance(c, str):
                                text = c
                            elif isinstance(c, list):
                                for p in c:
                                    if isinstance(p, dict) and p.get("type") == "text":
                                        text += p.get("text", "") + " "
                                    elif isinstance(p, str):
                                        text += p + " "
                    elif msg_type == "assistant":
                        msg = data.get("message", {})
                        if isinstance(msg, dict):
                            parts = msg.get("content", [])
                            if isinstance(parts, list):
                                for p in parts:
                                    if isinstance(p, dict) and p.get("type") == "text":
                                        text += p.get("text", "") + " "

                    if query_lower in text.lower():
                        # Extract snippet around match
                        idx = text.lower().find(query_lower)
                        start = max(0, idx - 40)
                        end = min(len(text), idx + len(query) + 40)
                        snippet = text[start:end].replace("\n", " ").strip()
                        if start > 0:
                            snippet = "..." + snippet
                        if end < len(text):
                            snippet += "..."

                        results.append({
                            "session": session,
                            "role": "user" if msg_type == "user" else "assistant",
                            "snippet": snippet,
                            "timestamp": data.get("timestamp", ""),
                        })
        except OSError:
            continue

    return results


def export_conversation_markdown(session: Session) -> str:
    """Export a session conversation as markdown."""
    if not session.jsonl_path:
        return ""

    messages = parse_session_transcript(session.jsonl_path, max_messages=2000)
    lines = [
        f"# Conversation: {session.session_id}",
        f"**Project:** {session.project_short}",
        f"**Date:** {session.last_activity.strftime('%Y-%m-%d %H:%M') if session.last_activity else '?'}",
        f"**Size:** {session.size_str}",
        "",
        "---",
        "",
    ]

    for msg in messages:
        ts = msg.timestamp.strftime("%H:%M:%S") if msg.timestamp else ""
        if msg.role == "user":
            lines.append(f"## You ({ts})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
        elif msg.role == "assistant":
            lines.append(f"## Claude ({ts})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
        elif msg.role == "tool":
            lines.append(f"> `{msg.content}`")
            lines.append("")
        elif msg.role == "system":
            lines.append(f"> *{msg.content}*")
            lines.append("")

    return "\n".join(lines)


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
    return f"{tool_name}()"


def _load_stats_json() -> dict:
    """Load stats-cache.json once, return raw dict."""
    stats_file = CLAUDE_DIR / "stats-cache.json"
    if not stats_file.exists():
        return {}
    try:
        with open(stats_file, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {}


def _parse_model_usages(data: dict) -> list[ModelUsage]:
    usages = []
    for model_id, vals in data.get("modelUsage", {}).items():
        usages.append(ModelUsage(
            model_id=model_id,
            input_tokens=vals.get("inputTokens", 0),
            output_tokens=vals.get("outputTokens", 0),
            cache_read_tokens=vals.get("cacheReadInputTokens", 0),
            cache_creation_tokens=vals.get("cacheCreationInputTokens", 0),
        ))
    return sorted(usages, key=lambda u: u.total_tokens, reverse=True)


def _parse_hour_counts(data: dict) -> dict[int, int]:
    raw = data.get("hourCounts", {})
    return {int(h): int(c) for h, c in raw.items()}


def _parse_longest_session(data: dict) -> dict:
    return data.get("longestSession", {})


def _parse_claude_json_projects() -> list[ClaudeJsonProject]:
    claude_json = Path.home() / ".claude.json"
    if not claude_json.exists():
        return []
    try:
        data = json.loads(claude_json.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return []

    result = []
    for path, proj in data.get("projects", {}).items():
        if not isinstance(proj, dict):
            continue
        mcp = list(proj.get("mcpServers", {}).keys())
        result.append(ClaudeJsonProject(
            path=path,
            last_cost=proj.get("lastCost", 0.0) or 0.0,
            last_duration_ms=proj.get("lastDuration", 0) or 0,
            mcp_servers=mcp,
            allowed_tools=proj.get("allowedTools", []),
            has_trust=proj.get("hasTrustDialogAccepted", False),
        ))
    return sorted(result, key=lambda p: p.last_cost, reverse=True)


def _parse_todos() -> list[SessionTodos]:
    todos_dir = CLAUDE_DIR / "todos"
    if not todos_dir.exists():
        return []

    result = []
    for f in todos_dir.glob("*.json"):
        # filename: {sessionId}-agent-{agentId}.json
        stem = f.stem
        parts = stem.split("-agent-")
        if len(parts) != 2:
            continue
        session_id, agent_id = parts[0], parts[1]
        try:
            raw = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(raw, list) or not raw:
            continue
        items = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            items.append(TodoItem(
                id=str(item.get("id", "")),
                content=item.get("content", ""),
                status=item.get("status", "pending"),
                priority=item.get("priority", "normal"),
            ))
        if items:
            result.append(SessionTodos(
                session_id=session_id,
                agent_id=agent_id,
                items=items,
            ))
    return result


def _parse_settings() -> dict:
    settings_file = CLAUDE_DIR / "settings.json"
    if not settings_file.exists():
        return {}
    try:
        with open(settings_file, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {}


def parse_plans() -> list[Plan]:
    plans_dir = CLAUDE_DIR / "plans"
    if not plans_dir.exists():
        return []

    plans = []
    for f in sorted(plans_dir.glob("*.md")):
        stat = f.stat()
        plans.append(Plan(
            name=f.stem.replace("-", " ").title(),
            path=f,
            modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            size=stat.st_size,
        ))
    return sorted(plans, key=lambda p: p.modified or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


def read_plan_content(plan: Plan) -> str:
    try:
        return plan.path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "(Could not read plan)"


def _parse_file_history() -> dict[str, list[str]]:
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


def get_global_stats() -> GlobalStats:
    """Get aggregate stats for the dashboard."""
    stats = parse_stats()
    history = parse_history()
    projects = discover_projects()
    longest = parse_longest_session()

    return GlobalStats(
        total_messages=sum(s.message_count for s in stats),
        total_sessions=sum(s.session_count for s in stats),
        total_tools=sum(s.tool_call_count for s in stats),
        total_prompts=len(history),
        total_projects=len([p for p in projects if p.session_count > 0]),
        total_data_bytes=sum(p.total_size for p in projects),
        first_date=stats[0].date if stats else "?",
        last_date=stats[-1].date if stats else "?",
        active_days=len(stats),
        daily_stats=stats,
        model_usages=parse_model_usages(),
        hour_counts=parse_hour_counts(),
        longest_session_id=longest.get("sessionId", ""),
        longest_session_duration_ms=longest.get("duration", 0),
        longest_session_msgs=longest.get("messageCount", 0),
    )
