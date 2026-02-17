"""Sessions browser screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Input, Static
from textual.message import Message

from ..data.parsers import discover_all_sessions
from ..data.models import Session


class SessionSelected(Message):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session


class SessionsScreen(Container):
    """Browse all sessions across projects."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sessions: list[Session] = []
        self._filtered: list[Session] = []

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  SESSIONS[/] [#a6adc8]- Browse all Claude sessions (Enter to view)[/]",
            markup=True,
        )
        yield Input(placeholder="Filter by project, date, or session ID...", id="session-filter")
        yield DataTable(id="sessions-table")

    def on_mount(self) -> None:
        self.load_sessions()

    def load_sessions(self) -> None:
        table = self.query_one("#sessions-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Date", "Project", "Session ID", "Size", "Prompts", "Duration")

        self._sessions = discover_all_sessions()
        self._filtered = self._sessions[:]
        self._populate_table()

    def filter_by_project(self, project_name: str) -> None:
        """Filter sessions to show only those from a specific project."""
        fi = self.query_one("#session-filter", Input)
        fi.value = project_name
        # The on_input_changed handler will trigger filtering

    def _populate_table(self) -> None:
        table = self.query_one("#sessions-table", DataTable)
        table.clear()
        for s in self._filtered:
            date_str = s.last_activity.strftime("%Y-%m-%d %H:%M") if s.last_activity else "?"
            table.add_row(
                date_str,
                s.project_short or s.project,
                s.session_id[:10] + "...",
                s.size_str,
                str(s.prompt_count),
                s.duration_str,
                key=s.session_id,
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "session-filter":
            query = event.value.lower().strip()
            if not query:
                self._filtered = self._sessions[:]
            else:
                self._filtered = [
                    s for s in self._sessions
                    if query in s.project_short.lower()
                    or query in s.session_id.lower()
                    or (s.last_activity and query in s.last_activity.strftime("%Y-%m-%d"))
                ]
            self._populate_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        if row_key:
            session = next((s for s in self._sessions if s.session_id == row_key.value), None)
            if session:
                self.post_message(SessionSelected(session))
