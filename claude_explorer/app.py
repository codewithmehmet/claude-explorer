"""Main Claude Explorer TUI application."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, TabbedContent, TabPane

from .screens.dashboard import DashboardScreen
from .screens.sessions import SessionsScreen, SessionSelected
from .screens.conversation import ConversationScreen, ExportRequested
from .screens.search import SearchScreen, SearchSessionSelected
from .screens.projects import ProjectsScreen, ProjectSelected
from .screens.plans import PlansScreen
from .screens.stats import StatsScreen
from .screens.file_history import FileHistoryScreen


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
        Binding("h", "switch_tab('file-history')", "Files", show=True),
        Binding("r", "refresh", "Refresh", show=True),
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
            with TabPane("File History", id="file-history"):
                yield FileHistoryScreen()
        yield Footer()

    def on_mount(self) -> None:
        # Hide conversation tab initially
        tabs = self.query_one("#main-tabs", TabbedContent)
        conv_tab = tabs.get_tab("conversation")
        conv_tab.display = False

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        # Show conversation tab if switching to it
        if tab_id == "conversation":
            tabs.get_tab("conversation").display = True
        tabs.active = tab_id

    def action_go_back(self) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        if tabs.active == "conversation":
            tabs.active = "sessions"

    def action_refresh(self) -> None:
        """Refresh all data."""
        from .data.parsers import refresh_data
        refresh_data()
        self.notify("Data refreshed", title="Claude Explorer")
        # Reload current screen
        tabs = self.query_one("#main-tabs", TabbedContent)
        active = tabs.active
        if active == "dashboard":
            self.query_one(DashboardScreen).load_dashboard()
        elif active == "sessions":
            self.query_one(SessionsScreen).load_sessions()
        elif active == "projects":
            self.query_one(ProjectsScreen).load_projects()
        elif active == "stats":
            self.query_one(StatsScreen).load_stats()
        elif active == "file-history":
            self.query_one(FileHistoryScreen).load_data()

    def _open_session(self, session) -> None:
        """Open a session in the conversation viewer."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.get_tab("conversation").display = True
        tabs.active = "conversation"
        self.query_one(ConversationScreen).load_session(session)

    def on_session_selected(self, event: SessionSelected) -> None:
        self._open_session(event.session)

    def on_search_session_selected(self, event: SearchSessionSelected) -> None:
        self._open_session(event.session)

    def on_project_selected(self, event: ProjectSelected) -> None:
        """Navigate to sessions filtered by project."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "sessions"
        sessions_screen = self.query_one(SessionsScreen)
        sessions_screen.filter_by_project(event.project_name)

    def on_export_requested(self, event: ExportRequested) -> None:
        """Export conversation to markdown file."""
        from .data.parsers import export_conversation_markdown
        content = export_conversation_markdown(event.session)
        if content:
            export_dir = Path.home() / "claude-exports"
            export_dir.mkdir(exist_ok=True)
            date_str = event.session.last_activity.strftime("%Y%m%d-%H%M") if event.session.last_activity else "unknown"
            filename = f"{event.session.project_short}-{date_str}.md".replace("/", "-").replace(" ", "-")
            export_path = export_dir / filename
            export_path.write_text(content, encoding="utf-8")
            self.notify(f"Exported to {export_path}", title="Export")


def main():
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Claude Explorer - Browse your .claude history")
    parser.add_argument("--path", type=str, help="Path to .claude directory (default: ~/.claude)")
    args = parser.parse_args()

    if args.path:
        import claude_explorer.data.parsers as parsers_mod
        parsers_mod.CLAUDE_DIR = Path(args.path)

    app = ClaudeExplorer()
    app.run()


if __name__ == "__main__":
    main()
