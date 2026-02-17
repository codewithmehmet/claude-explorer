"""Plans browser screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Static, MarkdownViewer

from ..data.parsers import parse_plans, read_plan_content
from ..data.models import Plan, format_size


class PlansScreen(Container):
    """Browse and read plan documents."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._plans: list[Plan] = []

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  PLANS[/] [#a6adc8]- Browse plan documents[/]",
            markup=True,
        )
        with Horizontal(id="plans-layout"):
            yield DataTable(id="plans-table")
            yield MarkdownViewer(id="plan-viewer", show_table_of_contents=False)

    def on_mount(self) -> None:
        self.load_plans()

    def load_plans(self) -> None:
        table = self.query_one("#plans-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Plan", "Date", "Size")
        table.styles.width = 40

        self._plans = parse_plans()

        for plan in self._plans:
            date_str = plan.modified.strftime("%Y-%m-%d") if plan.modified else "?"
            size_str = format_size(plan.size)
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
