"""Settings screen - display ~/.claude/settings.json and ~/.claude.json config."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, RichLog

from ..data.parsers import parse_settings, parse_claude_json_projects
from ..data.models import escape_markup, format_size


class SettingsScreen(Container):
    """Display Claude Code configuration and project settings."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #cba6f7]  SETTINGS[/] [#a6adc8]- Claude Code configuration[/]",
            markup=True,
        )
        yield RichLog(id="settings-log", wrap=True, markup=True)

    def on_mount(self) -> None:
        self.load_settings()

    def load_settings(self) -> None:
        log = self.query_one("#settings-log", RichLog)
        log.clear()

        # --- settings.json ---
        settings = parse_settings()
        log.write("[bold #cba6f7]~/.claude/settings.json[/]")
        log.write("[#45475a]" + "─" * 60 + "[/]")

        if settings:
            model = settings.get("model", "")
            if model:
                log.write(f"  [#a6adc8]Default model:[/]  [#cba6f7]{escape_markup(model)}[/]")

            hooks = settings.get("hooks", {})
            if hooks:
                log.write(f"  [#a6adc8]Hooks configured:[/]")
                for event, entries in hooks.items():
                    count = sum(len(h.get("hooks", [])) for h in entries if isinstance(h, dict))
                    log.write(f"    [#f9e2af]{event}[/]  {count} hook(s)")

            permissions = settings.get("permissions", {})
            if permissions:
                deny = permissions.get("deny", [])
                allow = permissions.get("allow", [])
                if deny:
                    log.write(f"  [#a6adc8]Denied tools:[/]  [#f38ba8]{', '.join(deny)}[/]")
                if allow:
                    log.write(f"  [#a6adc8]Allowed tools:[/] [#a6e3a1]{', '.join(allow)}[/]")
        else:
            log.write("  [#585b70]No settings.json found[/]")

        # --- ~/.claude.json projects ---
        log.write("")
        log.write("[bold #cba6f7]~/.claude.json — Project Settings[/]")
        log.write("[#45475a]" + "─" * 60 + "[/]")

        projects = parse_claude_json_projects()
        if not projects:
            log.write("  [#585b70]No project entries found[/]")
            return

        projects_with_data = [p for p in projects if p.last_cost > 0 or p.mcp_servers or p.allowed_tools]
        log.write(f"  [#a6adc8]{len(projects)} projects tracked, {len(projects_with_data)} with notable config[/]")
        log.write("")

        for proj in projects:
            has_info = proj.last_cost > 0 or proj.mcp_servers or proj.allowed_tools
            if not has_info:
                continue
            log.write(f"  [#89b4fa]{escape_markup(proj.display_path)}[/]")
            if proj.last_cost > 0:
                dur_s = proj.last_duration_ms // 1000
                log.write(f"    Last cost: [#f9e2af]{proj.cost_str}[/]  duration: {dur_s}s")
            if proj.mcp_servers:
                servers = ", ".join(escape_markup(s) for s in proj.mcp_servers)
                log.write(f"    MCP servers: [#cba6f7]{servers}[/]")
            if proj.allowed_tools:
                tools = ", ".join(escape_markup(t) for t in proj.allowed_tools[:5])
                extra = f" +{len(proj.allowed_tools) - 5}" if len(proj.allowed_tools) > 5 else ""
                log.write(f"    Allowed tools: [#a6e3a1]{tools}{extra}[/]")
