"""Plans browser screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Static, MarkdownViewer, LoadingIndicator
from textual.worker import Worker, WorkerState
from textual import work

from ..data.cache import DataCache
from ..data.parsers import read_plan_content
from ..data.models import Plan


class PlansScreen(Container):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._plans: list[Plan] = []

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  PLANS[/] [#a6adc8]- Browse plan documents[/]",
            markup=True,
        )
        yield LoadingIndicator(id="plans-loading")
        with Horizontal(id="plans-layout"):
            yield DataTable(id="plans-table")
            yield MarkdownViewer(id="plan-viewer", show_table_of_contents=False)

    def on_mount(self) -> None:
        self.load_data()

    @work(thread=True)
    def load_data(self) -> list[Plan]:
        return DataCache().plans()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self._plans = event.worker.result
            try:
                self.query_one("#plans-loading").remove()
            except Exception:
                pass
            table = self.query_one("#plans-table", DataTable)
            table.clear(columns=True)
            table.cursor_type = "row"
            table.add_columns("Plan", "Date", "Size")
            table.styles.width = 40

            for plan in self._plans:
                date_str = plan.modified.strftime("%Y-%m-%d") if plan.modified else "?"
                size_str = f"{plan.size // 1024}KB" if plan.size > 1024 else f"{plan.size}B"
                table.add_row(plan.name, date_str, size_str, key=plan.name)

            if self._plans:
                self._show_plan(self._plans[0])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        if row_key:
            plan = next((p for p in self._plans if p.name == row_key.value), None)
            if plan:
                self._show_plan(plan)

    def _show_plan(self, plan: Plan) -> None:
        viewer = self.query_one("#plan-viewer", MarkdownViewer)
        content = read_plan_content(plan)
        viewer.document.update(content)
