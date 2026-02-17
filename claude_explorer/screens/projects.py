"""Projects browser screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static

from ..data.parsers import discover_projects


class ProjectsScreen(Container):
    """Browse projects and their sessions."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  PROJECTS[/] [#a6adc8]- Browse by project[/]",
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
