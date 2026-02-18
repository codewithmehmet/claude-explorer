"""Todos screen - browse task lists from Claude sessions."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Static, RichLog
from textual.message import Message

from ..data.parsers import parse_todos, discover_all_sessions
from ..data.models import Session, SessionTodos, escape_markup


class TodoSessionSelected(Message):
    """Posted when user wants to open the session for a todo list."""
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session


STATUS_ICON = {
    "completed": "[#a6e3a1]✓[/]",
    "in_progress": "[#f9e2af]●[/]",
    "pending": "[#585b70]○[/]",
}

PRIORITY_COLOR = {
    "high": "#f38ba8",
    "normal": "#cdd6f4",
    "low": "#585b70",
}


class TodosScreen(Container):
    """Browse todo lists from all Claude sessions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._todos: list[SessionTodos] = []
        self._sessions_by_id: dict[str, Session] = {}

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  TODOS[/] [#a6adc8]- Task lists from Claude sessions (Enter to open)[/]",
            markup=True,
        )
        with Horizontal(id="todos-layout"):
            yield DataTable(id="todos-sessions-table")
            yield RichLog(id="todos-detail-log", wrap=True, markup=True)

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        self._todos = parse_todos()

        sessions = discover_all_sessions()
        self._sessions_by_id = {s.session_id: s for s in sessions}

        table = self.query_one("#todos-sessions-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Project", "Done", "Active", "Pending")
        table.styles.width = 50

        log = self.query_one("#todos-detail-log", RichLog)
        log.clear()

        if not self._todos:
            log.write("[bold #cba6f7]No todos found[/]")
            log.write("")
            log.write("[#a6adc8]Todo lists are created when Claude uses the[/]")
            log.write("[#cba6f7]TaskCreate / TodoWrite[/] [#a6adc8]tools during a session.[/]")
            return

        for st in self._todos:
            sess = self._sessions_by_id.get(st.session_id)
            project = sess.project_short if sess else st.session_id[:10] + "..."
            table.add_row(
                project,
                str(st.completed),
                str(st.in_progress),
                str(st.pending),
                key=st.session_id + ":" + st.agent_id,
            )

        # Show first entry by default
        if self._todos:
            self._show_todos(self._todos[0])

        total_items = sum(len(st.items) for st in self._todos)
        total_done = sum(st.completed for st in self._todos)
        log.write(
            f"[#a6adc8]{len(self._todos)} sessions with todos — "
            f"{total_done}/{total_items} tasks completed[/]"
        )

    def _get_todo_from_key(self, composite: str) -> tuple[SessionTodos | None, Session | None]:
        parts = composite.split(":", 1)
        if len(parts) != 2:
            return None, None
        session_id, agent_id = parts
        st = next(
            (t for t in self._todos if t.session_id == session_id and t.agent_id == agent_id),
            None,
        )
        sess = self._sessions_by_id.get(session_id) if st else None
        return st, sess

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Single click / Enter: show detail; Enter navigates to session."""
        row_key = event.row_key
        if not row_key:
            return
        st, sess = self._get_todo_from_key(row_key.value)
        if st:
            self._show_todos(st)
            if sess:
                self.post_message(TodoSessionSelected(sess))

    def _show_todos(self, st: SessionTodos) -> None:
        log = self.query_one("#todos-detail-log", RichLog)
        log.clear()

        sess = self._sessions_by_id.get(st.session_id)
        project = sess.project_short if sess else "unknown"
        log.write(f"[bold #cba6f7]Todo List[/]")
        log.write(f"[#a6adc8]Project: {project}[/]")
        log.write(f"[#a6adc8]Session: {st.session_id[:10]}...[/]")
        log.write(
            f"[#a6adc8]{st.completed} done · "
            f"{st.in_progress} active · "
            f"{st.pending} pending[/]"
        )
        log.write("[#45475a]" + "─" * 60 + "[/]")
        log.write("")

        for item in st.items:
            icon = STATUS_ICON.get(item.status, "○")
            color = PRIORITY_COLOR.get(item.priority, "#cdd6f4")
            priority_tag = f"[#f38ba8][high][/] " if item.priority == "high" else ""
            log.write(f"  {icon} {priority_tag}[{color}]{escape_markup(item.content)}[/]")
