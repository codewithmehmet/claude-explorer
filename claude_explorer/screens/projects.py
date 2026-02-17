"""Projects browser screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static, LoadingIndicator
from textual.worker import Worker, WorkerState
from textual import work

from ..data.cache import DataCache
from ..data.models import Project


class ProjectsScreen(Container):
    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  PROJECTS[/] [#a6adc8]- Browse by project[/]",
            markup=True,
        )
        yield LoadingIndicator(id="projects-loading")
        yield DataTable(id="projects-table")

    def on_mount(self) -> None:
        self.load_data()

    @work(thread=True)
    def load_data(self) -> list[Project]:
        return DataCache().projects()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            try:
                self.query_one("#projects-loading").remove()
            except Exception:
                pass
            self._render_projects(event.worker.result)

    def _render_projects(self, projects: list[Project]) -> None:
        table = self.query_one("#projects-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Project", "Sessions", "Total Size", "Latest Session")

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
