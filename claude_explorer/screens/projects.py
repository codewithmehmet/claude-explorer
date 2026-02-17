"""Projects browser screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static
from textual.message import Message

from ..data.parsers import discover_projects


class ProjectSelected(Message):
    def __init__(self, project_name: str) -> None:
        super().__init__()
        self.project_name = project_name


class ProjectsScreen(Container):
    """Browse projects and their sessions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._projects_map: dict[str, str] = {}  # key -> display_name

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  PROJECTS[/] [#a6adc8]- Browse by project (Enter to view sessions)[/]",
            markup=True,
        )
        yield DataTable(id="projects-table")

    def on_mount(self) -> None:
        self.load_projects()

    def load_projects(self) -> None:
        table = self.query_one("#projects-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Project", "Sessions", "Total Size", "Latest Session")
        self._projects_map = {}

        projects = discover_projects()

        for proj in projects:
            latest = "?"
            if proj.sessions:
                la = proj.sessions[0].last_activity
                if la:
                    latest = la.strftime("%Y-%m-%d %H:%M")

            table.add_row(
                proj.display_name,
                str(proj.session_count),
                proj.size_str,
                latest,
                key=proj.name,
            )
            self._projects_map[proj.name] = proj.display_name

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        if row_key and row_key.value in self._projects_map:
            display_name = self._projects_map[row_key.value]
            self.post_message(ProjectSelected(display_name))
