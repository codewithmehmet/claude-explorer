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
