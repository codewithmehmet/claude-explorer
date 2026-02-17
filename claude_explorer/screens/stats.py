"""Stats screen - detailed activity statistics."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Static, RichLog

from ..data.parsers import parse_stats


def make_bar(value: int, max_value: int, width: int = 30) -> str:
    if max_value == 0:
        return ""
    filled = int(value / max_value * width)
    return "█" * filled + "░" * (width - filled)


class StatsScreen(Container):
    """Detailed stats and activity charts."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  STATS[/] [#a6adc8]- Detailed activity statistics[/]",
            markup=True,
        )
        yield RichLog(id="stats-chart", wrap=True, markup=True)
        yield DataTable(id="stats-detail-table")

    def on_mount(self) -> None:
        self.load_stats()

    def load_stats(self) -> None:
        stats = parse_stats()

        chart = self.query_one("#stats-chart", RichLog)
        chart.clear()
        chart.styles.height = 20

        if not stats:
            chart.write("[#f38ba8]No stats data found.[/]")
            return

        max_msgs = max(s.message_count for s in stats)
        max_tools = max(s.tool_call_count for s in stats)

        chart.write("[bold #cba6f7]Messages per Day[/]")
        chart.write("")

        recent = stats[-20:]
        for day in recent:
            bar = make_bar(day.message_count, max_msgs, 40)
            chart.write(f"  {day.date}  [#89b4fa]{bar}[/] {day.message_count}")

        chart.write("")
        chart.write("[bold #cba6f7]Tool Calls per Day[/]")
        chart.write("")

        for day in recent:
            bar = make_bar(day.tool_call_count, max_tools, 40)
            chart.write(f"  {day.date}  [#a6e3a1]{bar}[/] {day.tool_call_count}")

        total_msgs = sum(s.message_count for s in stats)
        total_tools = sum(s.tool_call_count for s in stats)
        total_sessions = sum(s.session_count for s in stats)
        avg_msgs = total_msgs // len(stats) if stats else 0
        avg_tools = total_tools // len(stats) if stats else 0

        chart.write("")
        chart.write("[bold #cba6f7]Summary:[/]")
        chart.write(f"  Total messages:   [bold]{total_msgs:,}[/]")
        chart.write(f"  Total tool calls: [bold]{total_tools:,}[/]")
        chart.write(f"  Total sessions:   [bold]{total_sessions:,}[/]")
        chart.write(f"  Avg msgs/day:     [bold]{avg_msgs:,}[/]")
        chart.write(f"  Avg tools/day:    [bold]{avg_tools:,}[/]")
        chart.write(f"  Active days:      [bold]{len(stats)}[/]")

        table = self.query_one("#stats-detail-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Date", "Messages", "Sessions", "Tool Calls", "Msgs/Session")

        for day in reversed(stats):
            msgs_per_session = day.message_count // day.session_count if day.session_count else 0
            table.add_row(
                day.date,
                str(day.message_count),
                str(day.session_count),
                str(day.tool_call_count),
                str(msgs_per_session),
            )
