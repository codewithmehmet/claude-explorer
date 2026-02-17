"""Dashboard screen - overview of .claude activity."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Label, RichLog
from textual.widget import Widget

from ..data.parsers import get_global_stats, parse_stats


SPARKLINE_CHARS = " ▁▂▃▄▅▆▇█"


def make_sparkline(values: list[int], width: int = 60) -> str:
    """Create a sparkline string from values."""
    if not values:
        return ""
    # Sample if too many values
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values

    max_val = max(sampled) if sampled else 1
    if max_val == 0:
        return SPARKLINE_CHARS[0] * len(sampled)

    return "".join(
        SPARKLINE_CHARS[min(int(v / max_val * 8), 8)]
        for v in sampled
    )


def format_number(n: int) -> str:
    """Format a number with separator."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


class StatBox(Static):
    """A stat display box."""

    def __init__(self, label: str, value: str, icon: str = "", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.icon = icon

    def compose(self) -> ComposeResult:
        yield Static(f"{self.icon} [bold #cba6f7]{self.value}[/]", markup=True)
        yield Static(f"[#a6adc8]{self.label}[/]", markup=True)


class DashboardScreen(Container):
    """Main dashboard with stats overview."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  CLAUDE EXPLORER[/] [#a6adc8]- Your .claude at a glance[/]",
            markup=True,
            id="dashboard-title",
        )
        yield Container(id="dashboard-content")

    def on_mount(self) -> None:
        self.load_dashboard()

    def load_dashboard(self) -> None:
        container = self.query_one("#dashboard-content")
        container.remove_children()

        stats = get_global_stats()
        daily = stats["daily_stats"]

        # Top stats row
        stats_row = Horizontal(
            StatBox("Total Messages", format_number(stats["total_messages"]), "", classes="stat-box"),
            StatBox("Total Sessions", format_number(stats["total_sessions"]), "", classes="stat-box"),
            StatBox("Tool Calls", format_number(stats["total_tools"]), "", classes="stat-box"),
            StatBox("User Prompts", format_number(stats["total_prompts"]), "", classes="stat-box"),
            StatBox("Projects", str(stats["total_projects"]), "", classes="stat-box"),
            StatBox("Active Days", str(stats["active_days"]), "", classes="stat-box"),
        )
        stats_row.styles.height = 5
        stats_row.styles.dock = "top"

        # Activity chart
        msg_values = [d.message_count for d in daily]
        tool_values = [d.tool_call_count for d in daily]
        session_values = [d.session_count for d in daily]

        chart_content = []
        chart_content.append(f"[bold #cba6f7]Daily Activity[/] ({stats['first_date']} to {stats['last_date']})")
        chart_content.append("")
        chart_content.append(f"[#89b4fa]Messages :[/] {make_sparkline(msg_values)}")
        chart_content.append(f"[#a6e3a1]Tools    :[/] {make_sparkline(tool_values)}")
        chart_content.append(f"[#f9e2af]Sessions :[/] {make_sparkline(session_values)}")
        chart_content.append("")

        # Top days
        if daily:
            top_days = sorted(daily, key=lambda d: d.message_count, reverse=True)[:5]
            chart_content.append("[bold #cba6f7]Most Active Days:[/]")
            for d in top_days:
                bar_len = int(d.message_count / max(dd.message_count for dd in daily) * 30) if daily else 0
                bar = "[#89b4fa]" + "█" * bar_len + "[/]"
                chart_content.append(f"  {d.date}  {bar} {d.message_count} msgs, {d.tool_call_count} tools")

        # Recent days
        chart_content.append("")
        chart_content.append("[bold #cba6f7]Recent Activity:[/]")
        for d in daily[-7:]:
            bar_len = int(d.message_count / max(dd.message_count for dd in daily) * 30) if daily else 0
            bar = "[#a6e3a1]" + "█" * bar_len + "[/]"
            chart_content.append(f"  {d.date}  {bar} {d.message_count} msgs")

        chart = Static("\n".join(chart_content), markup=True, id="activity-chart")

        # Data size info
        data_mb = stats["total_data_bytes"] / 1024 / 1024
        info = Static(
            f"\n[#a6adc8]Data range: {stats['first_date']} to {stats['last_date']} | "
            f"Total session data: {data_mb:.1f}MB | "
            f"History prompts: {stats['total_prompts']}[/]",
            markup=True,
        )

        container.mount(stats_row)
        container.mount(chart)
        container.mount(info)
