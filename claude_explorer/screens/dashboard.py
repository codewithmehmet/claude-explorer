"""Dashboard screen - overview of .claude activity."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static

from ..data.parsers import get_global_stats
from ..data.models import format_size


SPARKLINE_CHARS = " ▁▂▃▄▅▆▇█"
HOUR_LABELS = [f"{h:02d}" for h in range(24)]


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


def format_duration_ms(ms: int) -> str:
    s = ms // 1000
    if s < 60:
        return f"{s}s"
    m = s // 60
    if m < 60:
        return f"{m}m{s % 60:02d}s"
    h = m // 60
    return f"{h}h{m % 60:02d}m"


class StatBox(Static):
    def __init__(self, label: str, value: str, **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value

    def compose(self) -> ComposeResult:
        yield Static(f"[bold #cba6f7]{self.value}[/]", markup=True)
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

        gs = get_global_stats()
        daily = gs.daily_stats

        stats_row = Horizontal(
            StatBox("Total Messages", format_number(gs.total_messages), classes="stat-box"),
            StatBox("Total Sessions", format_number(gs.total_sessions), classes="stat-box"),
            StatBox("Tool Calls", format_number(gs.total_tools), classes="stat-box"),
            StatBox("User Prompts", format_number(gs.total_prompts), classes="stat-box"),
            StatBox("Projects", str(gs.total_projects), classes="stat-box"),
            StatBox("Active Days", str(gs.active_days), classes="stat-box"),
        )
        stats_row.styles.height = 5
        stats_row.styles.dock = "top"

        msg_values = [d.message_count for d in daily]
        tool_values = [d.tool_call_count for d in daily]
        session_values = [d.session_count for d in daily]

        lines = []
        lines.append(f"[bold #cba6f7]Daily Activity[/] ({gs.first_date} to {gs.last_date})")
        lines.append("")
        lines.append(f"[#89b4fa]Messages :[/] {make_sparkline(msg_values)}")
        lines.append(f"[#a6e3a1]Tools    :[/] {make_sparkline(tool_values)}")
        lines.append(f"[#f9e2af]Sessions :[/] {make_sparkline(session_values)}")
        lines.append("")

        if daily:
            max_msg = max(d.message_count for d in daily)
            top_days = sorted(daily, key=lambda d: d.message_count, reverse=True)[:5]
            lines.append("[bold #cba6f7]Most Active Days:[/]")
            for d in top_days:
                bar_len = int(d.message_count / max_msg * 30) if max_msg else 0
                bar = "[#89b4fa]" + "█" * bar_len + "[/]"
                lines.append(f"  {d.date}  {bar} {d.message_count} msgs, {d.tool_call_count} tools")

            lines.append("")
            lines.append("[bold #cba6f7]Recent Activity:[/]")
            for d in daily[-7:]:
                bar_len = int(d.message_count / max_msg * 30) if max_msg else 0
                bar = "[#a6e3a1]" + "█" * bar_len + "[/]"
                lines.append(f"  {d.date}  {bar} {d.message_count} msgs")

        # Hourly activity heatmap
        if gs.hour_counts:
            lines.append("")
            lines.append("[bold #cba6f7]Activity by Hour:[/]")
            max_h = max(gs.hour_counts.values()) if gs.hour_counts else 1
            heatmap = ""
            for h in range(24):
                count = gs.hour_counts.get(h, 0)
                intensity = int(count / max_h * 8) if max_h else 0
                char = SPARKLINE_CHARS[intensity]
                heatmap += f"[#cba6f7]{char}[/]"
            lines.append(f"  00h {''.join(heatmap)} 23h")
            peak_hour = max(gs.hour_counts, key=gs.hour_counts.get)
            lines.append(f"  Peak: [#f9e2af]{peak_hour:02d}h[/] ({gs.hour_counts[peak_hour]} sessions)")

        # Model usage breakdown
        if gs.model_usages:
            lines.append("")
            lines.append("[bold #cba6f7]Model Usage:[/]")
            for mu in gs.model_usages:
                total = mu.total_tokens
                lines.append(
                    f"  [#cba6f7]{mu.model_short:<12}[/] "
                    f"in=[#89b4fa]{format_number(mu.input_tokens)}[/] "
                    f"out=[#a6e3a1]{format_number(mu.output_tokens)}[/] "
                    f"cache=[#f9e2af]{format_number(mu.cache_read_tokens)}[/] "
                    f"total=[#cdd6f4]{format_number(total)}[/]"
                )

        # Longest session
        if gs.longest_session_id:
            dur = format_duration_ms(gs.longest_session_duration_ms)
            lines.append("")
            lines.append(
                f"[bold #cba6f7]Longest Session:[/] "
                f"[#f9e2af]{dur}[/] — "
                f"[#a6adc8]{gs.longest_session_msgs} msgs | {gs.longest_session_id[:10]}...[/]"
            )

        chart = Static("\n".join(lines), markup=True, id="activity-chart")

        data_mb = gs.total_data_bytes / 1024 / 1024
        info = Static(
            f"\n[#a6adc8]Data range: {gs.first_date} to {gs.last_date} | "
            f"Total session data: {data_mb:.1f}MB | "
            f"History prompts: {gs.total_prompts}[/]",
            markup=True,
        )

        container.mount(stats_row)
        container.mount(chart)
        container.mount(info)
