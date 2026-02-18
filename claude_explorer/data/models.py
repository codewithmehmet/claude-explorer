"""Data models for Claude Explorer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_HOME = str(Path.home())
_HOME_ENCODED = _HOME.replace("/", "-")


def escape_markup(text: str) -> str:
    """Escape Rich markup brackets in user-derived text."""
    return text.replace("[", "\\[").replace("]", "\\]")


def format_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable size string."""
    if size_bytes == 0:
        return "0B"
    if size_bytes > 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f}MB"
    if size_bytes > 1024:
        return f"{size_bytes / 1024:.0f}KB"
    return f"{size_bytes}B"


def shorten_path(path: str) -> str:
    """Replace the user's home directory with ~/ in a path."""
    home_slash = _HOME + "/"
    if path.startswith(home_slash):
        return "~/" + path[len(home_slash):]
    if path == _HOME:
        return "~"
    return path


def shorten_project_dir(name: str) -> str:
    """Convert a .claude project directory name to a readable name.

    Project dirs encode the full path with dashes, e.g.:
    'home-mehmet-Projects-foo-bar' -> 'foo-bar'
    'home-mehmet--claude' -> '~/.claude'
    'home-mehmet-Projects' -> 'Projects'
    """
    prefix_projects = _HOME_ENCODED + "-Projects-"
    prefix_home = _HOME_ENCODED + "-"
    # e.g. "home-mehmet-Projects-istiqami" -> "istiqami"
    if name.startswith(prefix_projects):
        result = name[len(prefix_projects):]
        return result if result else "Projects"
    # e.g. "home-mehmet-Projects" (exact match, no trailing dash)
    if name == _HOME_ENCODED + "-Projects":
        return "Projects"
    # e.g. "home-mehmet--claude" -> suffix is "-claude" -> "~/.claude"
    if name.startswith(prefix_home):
        suffix = name[len(prefix_home):]
        if suffix.startswith("-"):
            # Double dash encodes a dot directory: --claude -> .claude
            return "~/" + "." + suffix[1:]
        return "~/" + suffix if suffix else "~"
    if name == _HOME_ENCODED:
        return "~"
    return name


@dataclass
class Prompt:
    """A single user prompt from history.jsonl."""
    text: str
    timestamp: datetime
    project: str
    session_id: str

    @property
    def project_short(self) -> str:
        return shorten_path(self.project)


@dataclass
class SessionMessage:
    """A message within a session transcript."""
    role: str
    content: str
    timestamp: datetime | None = None
    tool_name: str | None = None
    message_type: str | None = None


@dataclass
class Session:
    """A Claude session with metadata."""
    session_id: str
    project: str
    project_path: str
    first_activity: datetime | None = None
    last_activity: datetime | None = None
    prompt_count: int = 0
    message_count: int = 0
    jsonl_path: Path | None = None
    jsonl_size: int = 0

    @property
    def project_short(self) -> str:
        return self.project or shorten_project_dir(self.project_path)

    @property
    def duration_str(self) -> str:
        if self.first_activity and self.last_activity:
            delta = self.last_activity - self.first_activity
            mins = int(delta.total_seconds() / 60)
            if mins < 60:
                return f"{mins}m"
            hours = mins // 60
            remaining = mins % 60
            return f"{hours}h{remaining:02d}m"
        return "?"

    @property
    def size_str(self) -> str:
        return format_size(self.jsonl_size)


@dataclass
class DailyStats:
    """Daily activity stats."""
    date: str
    message_count: int = 0
    session_count: int = 0
    tool_call_count: int = 0


@dataclass
class ModelUsage:
    """Token usage statistics for a single model."""
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def model_short(self) -> str:
        m = self.model_id
        if "opus-4-6" in m:
            return "Opus 4.6"
        if "opus-4-5" in m:
            return "Opus 4.5"
        if "sonnet-4" in m:
            return "Sonnet 4"
        if "haiku-4" in m:
            return "Haiku 4"
        return m[:24]

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_read_tokens + self.cache_creation_tokens


@dataclass
class TodoItem:
    """A single todo task item."""
    id: str
    content: str
    status: str        # "pending" | "in_progress" | "completed"
    priority: str = "normal"  # "high" | "normal" | "low"


@dataclass
class SessionTodos:
    """Todo list for a session."""
    session_id: str
    agent_id: str
    items: list[TodoItem] = field(default_factory=list)

    @property
    def pending(self) -> int:
        return sum(1 for t in self.items if t.status == "pending")

    @property
    def in_progress(self) -> int:
        return sum(1 for t in self.items if t.status == "in_progress")

    @property
    def completed(self) -> int:
        return sum(1 for t in self.items if t.status == "completed")


@dataclass
class GlobalStats:
    """Aggregate stats for the dashboard."""
    total_messages: int = 0
    total_sessions: int = 0
    total_tools: int = 0
    total_prompts: int = 0
    total_projects: int = 0
    total_data_bytes: int = 0
    first_date: str = "?"
    last_date: str = "?"
    active_days: int = 0
    daily_stats: list[DailyStats] = field(default_factory=list)
    model_usages: list[ModelUsage] = field(default_factory=list)
    hour_counts: dict[int, int] = field(default_factory=dict)
    longest_session_id: str = ""
    longest_session_duration_ms: int = 0
    longest_session_msgs: int = 0


@dataclass
class ClaudeJsonProject:
    """Per-project settings from ~/.claude.json."""
    path: str
    last_cost: float = 0.0
    last_duration_ms: int = 0
    mcp_servers: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    has_trust: bool = False

    @property
    def display_path(self) -> str:
        return shorten_path(self.path)

    @property
    def cost_str(self) -> str:
        if self.last_cost <= 0:
            return ""
        return f"${self.last_cost:.4f}"


@dataclass
class Plan:
    """A plan document."""
    name: str
    path: Path
    content: str = ""
    modified: datetime | None = None
    size: int = 0


@dataclass
class Project:
    """A project with its sessions."""
    name: str
    path: str
    display_name: str
    sessions: list[Session] = field(default_factory=list)
    total_size: int = 0
    session_count: int = 0

    @property
    def size_str(self) -> str:
        return format_size(self.total_size)
