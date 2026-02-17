"""File History screen - browse files changed per session."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Static, RichLog

from ..data.parsers import parse_file_history, discover_all_sessions
from ..data.models import Session, escape_markup


class FileHistoryScreen(Container):
    """Browse files changed in each session."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._fh: dict[str, list[str]] = {}
        self._sessions_map: dict[str, Session] = {}

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  FILE HISTORY[/] [#a6adc8]- Files changed per session[/]",
            markup=True,
        )
        with Horizontal(id="fh-layout"):
            yield DataTable(id="fh-sessions-table")
            yield RichLog(id="fh-files-log", wrap=True, markup=True)

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        self._fh = parse_file_history()
        sessions = discover_all_sessions()
        self._sessions_map = {s.session_id: s for s in sessions}

        table = self.query_one("#fh-sessions-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Date", "Project", "Files Changed")
        table.styles.width = 50

        # Sort sessions by date, only show those with file history
        entries = []
        for sid, files in self._fh.items():
            session = self._sessions_map.get(sid)
            date_str = "?"
            project = sid[:10] + "..."
            if session:
                if session.last_activity:
                    date_str = session.last_activity.strftime("%Y-%m-%d %H:%M")
                project = session.project_short
            entries.append((date_str, project, len(files), sid))

        entries.sort(key=lambda x: x[0], reverse=True)

        for date_str, project, file_count, sid in entries:
            table.add_row(date_str, project, str(file_count), key=sid)

        # Show summary
        log = self.query_one("#fh-files-log", RichLog)
        log.clear()
        total_files = sum(len(f) for f in self._fh.values())
        log.write(f"[bold #cba6f7]File History Summary[/]")
        log.write(f"[#a6adc8]{len(self._fh)} sessions with file changes[/]")
        log.write(f"[#a6adc8]{total_files} total file operations tracked[/]")
        log.write("")
        log.write("[#585b70]Select a session to see its file changes.[/]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        if not row_key:
            return

        sid = row_key.value
        files = self._fh.get(sid, [])
        session = self._sessions_map.get(sid)

        log = self.query_one("#fh-files-log", RichLog)
        log.clear()

        project = session.project_short if session else sid[:10]
        date_str = session.last_activity.strftime("%Y-%m-%d %H:%M") if session and session.last_activity else "?"

        log.write(f"[bold #cba6f7]Files changed in session[/]")
        log.write(f"[#a6adc8]Project: {project} | Date: {date_str}[/]")
        log.write(f"[#a6adc8]{len(files)} files[/]")
        log.write("[#45475a]" + "─" * 60 + "[/]")
        log.write("")

        for f in files:
            # Color by extension
            if f.endswith((".ts", ".tsx", ".js", ".jsx")):
                color = "#f9e2af"
            elif f.endswith((".py",)):
                color = "#89b4fa"
            elif f.endswith((".md", ".txt")):
                color = "#a6e3a1"
            elif f.endswith((".json", ".yaml", ".yml", ".toml")):
                color = "#cba6f7"
            elif f.endswith((".css", ".scss", ".tcss")):
                color = "#f38ba8"
            else:
                color = "#cdd6f4"
            log.write(f"  [{color}]{escape_markup(f)}[/]")
