"""Full-text search across history and conversations."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import DataTable, Input, Static, Switch
from textual.message import Message
from textual.timer import Timer
from textual.worker import Worker, WorkerState

from ..data.parsers import parse_history, search_conversations, discover_all_sessions
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
        self._prompt_results: list[Prompt] = []
        self._deep_mode = False
        self._debounce_timer: Timer | None = None
        self._search_worker: Worker | None = None

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
        controls = self.query_one("#search-controls")
        controls.styles.height = 3
        controls.styles.dock = "top"
        label = self.query_one("#deep-label")
        label.styles.width = 7
        label.styles.padding = (1, 0)
        sw = self.query_one("#deep-switch")
        sw.styles.width = 10

    def on_unmount(self) -> None:
        if self._debounce_timer:
            self._debounce_timer.stop()
            self._debounce_timer = None
        if self._search_worker and self._search_worker.state == WorkerState.RUNNING:
            self._search_worker.cancel()

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._prompts = parse_history()
            self._loaded = True

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "deep-switch":
            self._deep_mode = event.value
            status = self.query_one("#search-status", Static)
            if self._deep_mode:
                status.update("[#f9e2af]Deep search: searches inside all conversations. Press Enter to search.[/]")
            else:
                status.update("[#a6adc8]Prompt search: searches in user prompts only (fast)[/]")
            si = self.query_one("#search-input", Input)
            if len(si.value.strip()) >= 3 and not self._deep_mode:
                self._do_search(si.value.strip())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search-input":
            return
        query = event.value.strip()
        if len(query) < 3:
            table = self.query_one("#search-results-table", DataTable)
            table.clear()
            self._deep_results = []
            self._prompt_results = []
            status = self.query_one("#search-status", Static)
            status.update("[#a6adc8]Type at least 3 characters to search[/]")
            return

        if self._deep_mode:
            # In deep mode, only search on Enter (see on_input_submitted)
            status = self.query_one("#search-status", Static)
            status.update("[#f9e2af]Press Enter to search conversations...[/]")
        else:
            # Debounce: cancel previous timer, start new 300ms delay
            if self._debounce_timer:
                self._debounce_timer.stop()
            self._debounce_timer = self.set_timer(0.3, lambda: self._do_search(query))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key - trigger deep search."""
        if event.input.id != "search-input":
            return
        query = event.value.strip()
        if len(query) >= 3:
            self._do_search(query)

    def _do_search(self, query: str) -> None:
        status = self.query_one("#search-status", Static)
        table = self.query_one("#search-results-table", DataTable)
        table.clear()
        self._deep_results = []
        self._prompt_results = []

        if self._deep_mode:
            # Cancel any previous deep search worker
            if self._search_worker and self._search_worker.state == WorkerState.RUNNING:
                self._search_worker.cancel()

            status.update("[#f9e2af]Searching conversations...[/]")
            self._search_worker = self.run_worker(
                lambda: search_conversations(query, max_results=100),
                thread=True,
            )
        else:
            self._ensure_loaded()
            results = [p for p in self._prompts if query.lower() in p.text.lower()]
            self._prompt_results = results[:100]

            for i, p in enumerate(self._prompt_results):
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

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle deep search worker completion."""
        if event.worker is not self._search_worker:
            return
        if event.state != WorkerState.SUCCESS:
            if event.state == WorkerState.ERROR:
                status = self.query_one("#search-status", Static)
                status.update("[#f38ba8]Search failed[/]")
            return

        results = event.worker.result
        self._deep_results = results
        table = self.query_one("#search-results-table", DataTable)
        table.clear()

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
        status = self.query_one("#search-status", Static)
        status.update(
            f"[#a6e3a1]{count} conversation matches[/]"
            if count > 0
            else "[#f38ba8]No matches in conversations[/]"
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
            idx = int(key[1:])
            if idx < len(self._prompt_results):
                prompt = self._prompt_results[idx]
                sessions = discover_all_sessions()
                session = next(
                    (s for s in sessions if s.session_id == prompt.session_id),
                    None,
                )
                if session:
                    self.post_message(SearchSessionSelected(session))
