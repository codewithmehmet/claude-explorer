"""Main Claude Explorer TUI application."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, TabbedContent, TabPane

from .screens.dashboard import DashboardScreen
from .screens.sessions import SessionsScreen, SessionSelected
from .screens.conversation import ConversationScreen
from .screens.search import SearchScreen
from .screens.projects import ProjectsScreen
from .screens.plans import PlansScreen
from .screens.stats import StatsScreen


CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"


class ClaudeExplorer(App):
    """A revolutionary TUI for browsing .claude history."""

    TITLE = "Claude Explorer"
    SUB_TITLE = "Browse your .claude history"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "switch_tab('dashboard')", "Dashboard", show=True),
        Binding("s", "switch_tab('sessions')", "Sessions", show=True),
        Binding("f", "switch_tab('search')", "Search", show=True),
        Binding("p", "switch_tab('projects')", "Projects", show=True),
        Binding("l", "switch_tab('plans')", "Plans", show=True),
        Binding("t", "switch_tab('stats')", "Stats", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        with TabbedContent(id="main-tabs"):
            with TabPane("Dashboard", id="dashboard"):
                yield DashboardScreen()
            with TabPane("Sessions", id="sessions"):
                yield SessionsScreen()
            with TabPane("Conversation", id="conversation"):
                yield ConversationScreen()
            with TabPane("Search", id="search"):
                yield SearchScreen()
            with TabPane("Projects", id="projects"):
                yield ProjectsScreen()
            with TabPane("Plans", id="plans"):
                yield PlansScreen()
            with TabPane("Stats", id="stats"):
                yield StatsScreen()
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = tab_id

    def action_go_back(self) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        if tabs.active == "conversation":
            tabs.active = "sessions"

    def on_session_selected(self, event: SessionSelected) -> None:
        """Handle session selection - switch to conversation view."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "conversation"
        conv = self.query_one(ConversationScreen)
        conv.load_session(event.session)


def main():
    """Entry point for the CLI."""
    app = ClaudeExplorer()
    app.run()


if __name__ == "__main__":
    main()
