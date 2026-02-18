"""Conversation viewer screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, RichLog, Button, LoadingIndicator
from textual.message import Message
from textual.worker import Worker, WorkerState

from ..data.models import Session, SessionMessage, escape_markup
from ..data.parsers import parse_session_transcript


class ExportRequested(Message):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session


class ConversationScreen(Container):
    """View a session's conversation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_session: Session | None = None
        self._load_worker: Worker | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  CONVERSATION[/] [#a6adc8]- Select a session to view[/]",
            markup=True,
            id="conv-title",
        )
        yield Button("< Back to Sessions", id="back-to-sessions", variant="default")
        yield Button("Export as Markdown", id="export-btn", variant="primary")
        yield LoadingIndicator(id="conv-loading")
        yield RichLog(id="conversation-log", wrap=True, markup=True, highlight=True)

    def on_mount(self) -> None:
        self.query_one("#conv-loading").display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-to-sessions":
            self.app.action_go_back()
        elif event.button.id == "export-btn" and self._current_session:
            self.post_message(ExportRequested(self._current_session))

    def load_session(self, session: Session) -> None:
        # Cancel any in-progress load
        if self._load_worker and self._load_worker.state == WorkerState.RUNNING:
            self._load_worker.cancel()

        self._current_session = session

        title = self.query_one("#conv-title", Static)
        title.update(
            f"[bold #cba6f7]  CONVERSATION[/] [#a6adc8]- "
            f"{session.project_short} | {session.session_id[:10]}... | "
            f"{session.last_activity.strftime('%Y-%m-%d %H:%M') if session.last_activity else '?'}[/]"
        )

        log = self.query_one("#conversation-log", RichLog)
        log.clear()

        if not session.jsonl_path:
            log.write("[#f38ba8]No session data file found.[/]")
            return

        # Show spinner, hide log
        self.query_one("#conv-loading").display = True
        log.display = False

        self._load_worker = self.run_worker(
            lambda: parse_session_transcript(session.jsonl_path),
            thread=True,
            name="load_conversation",
        )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._load_worker:
            return

        if event.state == WorkerState.SUCCESS:
            self._render_messages(event.worker.result)
        elif event.state == WorkerState.ERROR:
            self._show_error(f"Failed to load session: {event.worker.error}")
        # CANCELLED: leave the spinner; a new worker will replace it

    def _render_messages(self, messages: list[SessionMessage]) -> None:
        self.query_one("#conv-loading").display = False
        log = self.query_one("#conversation-log", RichLog)
        log.display = True
        log.clear()

        session = self._current_session
        if session is None:
            return

        if not messages:
            log.write("[#a6adc8]No messages found in this session.[/]")
            return

        log.write(f"[bold #cba6f7]Session: {session.session_id}[/]")
        log.write(f"[#a6adc8]Project: {session.project_short} | Messages: {len(messages)} | Size: {session.size_str}[/]")
        log.write("[#45475a]" + "─" * 80 + "[/]")
        log.write("")

        for msg in messages:
            ts_str = ""
            if msg.timestamp:
                ts_str = f"[#585b70]{msg.timestamp.strftime('%H:%M:%S')}[/] "

            if msg.role == "user":
                log.write(f"{ts_str}[bold #89b4fa]YOU:[/]")
                for line in msg.content.split("\n"):
                    log.write(f"  [#cdd6f4]{escape_markup(line)}[/]")
                log.write("")
            elif msg.role == "assistant":
                log.write(f"{ts_str}[bold #a6e3a1]CLAUDE:[/]")
                for line in msg.content.split("\n"):
                    log.write(f"  [#bac2de]{escape_markup(line)}[/]")
                log.write("")
            elif msg.role == "tool":
                log.write(f"  {ts_str}[#cba6f7]{escape_markup(msg.content)}[/]")
            elif msg.role == "system":
                log.write(f"  {ts_str}[#f9e2af]{escape_markup(msg.content)}[/]")
                log.write("")

    def _show_error(self, message: str) -> None:
        self.query_one("#conv-loading").display = False
        log = self.query_one("#conversation-log", RichLog)
        log.display = True
        log.clear()
        log.write(f"[#f38ba8]{escape_markup(message)}[/]")
