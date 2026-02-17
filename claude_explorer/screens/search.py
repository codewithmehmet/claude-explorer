"""Full-text search across all history."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Input, Static

from ..data.parsers import parse_history
from ..data.models import Prompt


class SearchScreen(Container):
    """Search across all prompts and history."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prompts: list[Prompt] = []
        self._loaded = False

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  SEARCH[/] [#a6adc8]- Full-text search across all prompts[/]",
            markup=True,
        )
        yield Input(placeholder="Type to search across all your Claude prompts...", id="search-input")
        yield Static("[#a6adc8]Type at least 2 characters to search[/]", id="search-status", markup=True)
        yield DataTable(id="search-results-table")

    def on_mount(self) -> None:
        table = self.query_one("#search-results-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Date", "Project", "Prompt")

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._prompts = parse_history()
            self._loaded = True

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return

        query = event.value.lower().strip()
        status = self.query_one("#search-status", Static)
        table = self.query_one("#search-results-table", DataTable)

        if len(query) < 2:
            table.clear()
            status.update(f"[#a6adc8]Type at least 2 characters to search ({len(self._prompts)} prompts loaded)[/]")
            return

        self._ensure_loaded()

        results = [
            p for p in self._prompts
            if query in p.text.lower()
        ]

        table.clear()
        for p in results[:100]:
            date_str = p.timestamp.strftime("%Y-%m-%d %H:%M")
            text_preview = p.text[:120].replace("\n", " ").strip()
            table.add_row(date_str, p.project_short, text_preview)

        count = len(results)
        shown = min(count, 100)
        status.update(
            f"[#a6e3a1]{count} results[/] [#a6adc8](showing {shown})[/]"
            if count > 0
            else "[#f38ba8]No results[/]"
        )
