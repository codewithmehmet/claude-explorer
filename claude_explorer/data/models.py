"""Data models for Claude Explorer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_HOME = str(Path.home())


@dataclass
class Prompt:
    """A single user prompt from history.jsonl."""
    text: str
    timestamp: datetime
    project: str
    session_id: str

    @property
    def project_short(self) -> str:
        return self.project.replace(_HOME + "/Projects/", "").replace(_HOME + "/", "~/")


@dataclass
class SessionMessage:
    """A message within a session transcript."""
    role: str  # 'user', 'assistant', 'system', 'tool_result', 'tool_use'
    content: str
    timestamp: datetime | None = None
    tool_name: str | None = None
    message_type: str | None = None  # 'say', 'tool_use', 'tool_result', etc.


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
        home_encoded = _HOME.replace("/", "-")
        return (self.project
                .replace(_HOME + "/Projects/", "")
                .replace(_HOME + "/", "~/")
                .replace(home_encoded + "-Projects-", "")
                .replace(home_encoded + "-", "~/")
                .replace(home_encoded, "~/")
                .lstrip("-")
                .replace("~/-", "~/."))

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
        if self.jsonl_size > 1024 * 1024:
            return f"{self.jsonl_size / 1024 / 1024:.1f}MB"
        return f"{self.jsonl_size / 1024:.0f}KB"


@dataclass
class DailyStats:
    """Daily activity stats."""
    date: str
    message_count: int = 0
    session_count: int = 0
    tool_call_count: int = 0


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
        if self.total_size > 1024 * 1024:
            return f"{self.total_size / 1024 / 1024:.1f}MB"
        return f"{self.total_size / 1024:.0f}KB"


@dataclass
class TodoItem:
    """A todo item."""
    session_id: str
    content: str


@dataclass
class FileChange:
    """A file changed in a session."""
    session_id: str
    file_path: str
    timestamp: datetime | None = None
