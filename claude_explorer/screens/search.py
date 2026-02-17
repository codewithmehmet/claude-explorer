"""Full-text search across history and conversations."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Input, Static, Switch
from textual.message import Message

from ..data.parsers import parse_history, search_conversations
from ..data.models import Prompt, Session


class SearchSessionSelected(Message):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session


class SearchScreen(Container):
    """Search across prompts and conversations."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prompts: list[Prompt] = []
        self._loaded = False
        self._deep_results: list[dict] = []
        self._deep_mode = False

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  SEARCH[/] [#a6adc8]- Full-text search (Enter on result to open)[/]",
            markup=True,
        )
        with Horizontal(id="search-controls"):
            yield Input(placeholder="Type to search (min 3 chars)...", id="search-input")
            yield Static(" Deep ", markup=False, id="deep-label")
            yield Switch(value=False, id="deep-switch")
        yield Static("[#a6adc8]Search in prompts. Toggle Deep to search inside conversations.[/]", id="search-status", markup=True)
        yield DataTable(id="search-results-table")

    def on_mount(self) -> None:
        table = self.query_one("#search-results-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Date", "Project", "Who", "Content")
        # Style the controls
        controls = self.query_one("#search-controls")
        controls.styles.height = 3
        controls.styles.dock = "top"
        label = self.query_one("#deep-label")
        label.styles.width = 7
        label.styles.padding = (1, 0)
        sw = self.query_one("#deep-switch")
        sw.styles.width = 10

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._prompts = parse_history()
            self._loaded = True

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "deep-switch":
            self._deep_mode = event.value
            status = self.query_one("#search-status", Static)
            if self._deep_mode:
                status.update("[#f9e2af]Deep search: searches inside all conversations (slower)[/]")
            else:
                status.update("[#a6adc8]Prompt search: searches in user prompts only (fast)[/]")
            # Re-trigger search if there's a query
            si = self.query_one("#search-input", Input)
            if len(si.value.strip()) >= 3:
                self._do_search(si.value.strip())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return
        query = event.value.strip()
        if len(query) < 3:
            table = self.query_one("#search-results-table", DataTable)
            table.clear()
            self._deep_results = []
            status = self.query_one("#search-status", Static)
            status.update(f"[#a6adc8]Type at least 3 characters to search[/]")
            return
        self._do_search(query)

    def _do_search(self, query: str) -> None:
        status = self.query_one("#search-status", Static)
        table = self.query_one("#search-results-table", DataTable)
        table.clear()
        self._deep_results = []

        if self._deep_mode:
            # Deep search in conversations
            status.update("[#f9e2af]Searching conversations...[/]")
            results = search_conversations(query, max_results=100)
            self._deep_results = results

            for i, r in enumerate(results):
                session = r["session"]
                date_str = session.last_activity.strftime("%Y-%m-%d %H:%M") if session.last_activity else "?"
                snippet = r["snippet"][:120]
                table.add_row(
                    date_str,
                    session.project_short,
                    r["role"],
                    snippet,
                    key=str(i),
                )

            count = len(results)
            status.update(
                f"[#a6e3a1]{count} conversation matches[/]"
                if count > 0
                else "[#f38ba8]No matches in conversations[/]"
            )
        else:
            # Fast prompt search
            self._ensure_loaded()
            results = [p for p in self._prompts if query.lower() in p.text.lower()]

            for i, p in enumerate(results[:100]):
                date_str = p.timestamp.strftime("%Y-%m-%d %H:%M")
                text_preview = p.text[:120].replace("\n", " ").strip()
                table.add_row(date_str, p.project_short, "you", text_preview, key=f"p{i}")

            count = len(results)
            shown = min(count, 100)
            status.update(
                f"[#a6e3a1]{count} results[/] [#a6adc8](showing {shown})[/]"
                if count > 0
                else "[#f38ba8]No results[/]"
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Open conversation when clicking a search result."""
        row_key = event.row_key
        if not row_key:
            return

        key = row_key.value

        if self._deep_mode and key.isdigit():
            idx = int(key)
            if idx < len(self._deep_results):
                session = self._deep_results[idx]["session"]
                self.post_message(SearchSessionSelected(session))
        elif key.startswith("p"):
            # Prompt search - find the session
            idx = int(key[1:])
            self._ensure_loaded()
            if idx < len(self._prompts):
                prompt = self._prompts[idx]
                # Find the session for this prompt
                from ..data.parsers import discover_all_sessions
                sessions = discover_all_sessions()
                session = next(
                    (s for s in sessions if s.session_id == prompt.session_id),
                    None,
                )
                if session:
                    self.post_message(SearchSessionSelected(session))
