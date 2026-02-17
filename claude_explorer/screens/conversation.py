"""Conversation viewer screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, RichLog, Button
from textual.message import Message

from ..data.models import Session
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

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  CONVERSATION[/] [#a6adc8]- Select a session to view[/]",
            markup=True,
            id="conv-title",
        )
        yield Button("< Back to Sessions", id="back-to-sessions", variant="default")
        yield Button("Export as Markdown", id="export-btn", variant="primary")
        yield RichLog(id="conversation-log", wrap=True, markup=True, highlight=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-to-sessions":
            self.app.action_go_back()
        elif event.button.id == "export-btn" and self._current_session:
            self.post_message(ExportRequested(self._current_session))

    def load_session(self, session: Session) -> None:
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

        messages = parse_session_transcript(session.jsonl_path)

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
                    log.write(f"  [#cdd6f4]{_escape(line)}[/]")
                log.write("")
            elif msg.role == "assistant":
                log.write(f"{ts_str}[bold #a6e3a1]CLAUDE:[/]")
                for line in msg.content.split("\n"):
                    log.write(f"  [#bac2de]{_escape(line)}[/]")
                log.write("")
            elif msg.role == "tool":
                log.write(f"  {ts_str}[#cba6f7]{_escape(msg.content)}[/]")
            elif msg.role == "system":
                log.write(f"  {ts_str}[#f9e2af]{_escape(msg.content)}[/]")
                log.write("")


def _escape(text: str) -> str:
    return text.replace("[", "\\[").replace("]", "\\]")
