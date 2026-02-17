# Claude Explorer

A terminal UI (TUI) to browse and explore your entire `~/.claude` directory - sessions, conversations, history, plans, stats, and more.

Built with [Textual](https://textual.textualize.io/) for a beautiful terminal experience.

## Screenshots

### Dashboard
Activity sparklines, total stats, most active days at a glance.

### Sessions Browser
All sessions across all projects, with real-time filtering.

### Conversation Viewer
Read any past conversation - user messages, Claude responses, tool calls with timestamps.

### Full-Text Search
Search across all your prompts instantly.

## Features

| Screen | Key | Description |
|--------|-----|-------------|
| Dashboard | `d` | Activity sparklines, top stats, most active days |
| Sessions | `s` | Browse all sessions with filtering by project/date |
| Conversation | *(select a session)* | Full conversation viewer with syntax highlighting |
| Search | `f` | Full-text search across all prompts |
| Projects | `p` | Browse by project with session counts and sizes |
| Plans | `l` | Read plan documents with markdown rendering |
| Stats | `t` | Bar charts and detailed daily activity table |

### Data Sources Parsed

- `history.jsonl` - All user prompts
- `projects/*/*.jsonl` - Full session transcripts
- `stats-cache.json` - Daily activity statistics
- `plans/*.md` - Plan documents
- `file-history/` - File changes per session
- `settings.json` - Configuration

## Installation

### Requirements

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed (for `~/.claude` data)

### Linux / macOS

```bash
git clone https://github.com/YOUR_USER/claude-explorer.git
cd claude-explorer
./install.sh
```

### Windows

```bash
git clone https://github.com/YOUR_USER/claude-explorer.git
cd claude-explorer
install.bat
```

### Manual Install

```bash
git clone https://github.com/YOUR_USER/claude-explorer.git
cd claude-explorer
python3 -m venv .venv
.venv/bin/pip install textual
.venv/bin/pip install -e .
.venv/bin/python -m claude_explorer
```

## Usage

```bash
claude-explorer
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `d` | Dashboard |
| `s` | Sessions |
| `f` | Search |
| `p` | Projects |
| `l` | Plans |
| `t` | Stats |
| `Esc` | Back |
| `q` | Quit |

## Tech Stack

- **Python 3.10+** with type hints
- **Textual** - Modern TUI framework
- **Catppuccin Mocha** - Color theme
- Zero external dependencies beyond Textual
- All data parsed locally from `~/.claude` files, no API calls

## License

MIT
