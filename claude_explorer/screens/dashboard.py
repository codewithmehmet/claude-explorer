"""Dashboard screen - overview of .claude activity."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static, LoadingIndicator
from textual.worker import Worker, WorkerState
from textual import work

from ..data.cache import DataCache


SPARKLINE_CHARS = " ▁▂▃▄▅▆▇█"


def make_sparkline(values: list[int], width: int = 60) -> str:
    if not values:
        return ""
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
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


class StatBox(Static):
    def __init__(self, label: str, value: str, **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value

    def compose(self) -> ComposeResult:
        yield Static(f"[bold #cba6f7]{self.value}[/]", markup=True)
        yield Static(f"[#a6adc8]{self.label}[/]", markup=True)


class DashboardScreen(Container):
    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  CLAUDE EXPLORER[/] [#a6adc8]- Your .claude at a glance[/]",
            markup=True,
            id="dashboard-title",
        )
        yield LoadingIndicator(id="dashboard-loading")
        yield Container(id="dashboard-content")

    def on_mount(self) -> None:
        self.load_data()

    @work(thread=True)
    def load_data(self) -> dict:
        return DataCache().global_stats()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            self._render_dashboard(event.worker.result)

    def _render_dashboard(self, stats: dict) -> None:
        try:
            self.query_one("#dashboard-loading").remove()
        except Exception:
            pass

        container = self.query_one("#dashboard-content")
        container.remove_children()

        daily = stats["daily_stats"]

        stats_row = Horizontal(
            StatBox("Total Messages", format_number(stats["total_messages"]), classes="stat-box"),
            StatBox("Total Sessions", format_number(stats["total_sessions"]), classes="stat-box"),
            StatBox("Tool Calls", format_number(stats["total_tools"]), classes="stat-box"),
            StatBox("User Prompts", format_number(stats["total_prompts"]), classes="stat-box"),
            StatBox("Projects", str(stats["total_projects"]), classes="stat-box"),
            StatBox("Active Days", str(stats["active_days"]), classes="stat-box"),
        )
        stats_row.styles.height = 5
        stats_row.styles.dock = "top"

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

        if daily:
            top_days = sorted(daily, key=lambda d: d.message_count, reverse=True)[:5]
            max_msg = max(dd.message_count for dd in daily)
            chart_content.append("[bold #cba6f7]Most Active Days:[/]")
            for d in top_days:
                bar_len = int(d.message_count / max_msg * 30) if max_msg else 0
                bar = "[#89b4fa]" + "█" * bar_len + "[/]"
                chart_content.append(f"  {d.date}  {bar} {d.message_count} msgs, {d.tool_call_count} tools")

            chart_content.append("")
            chart_content.append("[bold #cba6f7]Recent Activity:[/]")
            for d in daily[-7:]:
                bar_len = int(d.message_count / max_msg * 30) if max_msg else 0
                bar = "[#a6e3a1]" + "█" * bar_len + "[/]"
                chart_content.append(f"  {d.date}  {bar} {d.message_count} msgs")

        chart = Static("\n".join(chart_content), markup=True, id="activity-chart")

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
