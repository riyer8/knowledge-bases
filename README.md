# Context

A local-first personal knowledge system — an AI that remembers what you've read and understands
what you're looking at right now.

## Quick links

| | |
|---|---|
| **Start here** | [docs/README.md](docs/README.md) |
| **Run it** | [docs/getting-started.md](docs/getting-started.md) |
| **Current status** | [docs/status.md](docs/status.md) |
| **Architecture** | [docs/architecture.md](docs/architecture.md) |

## Clients

- **[chrome-extension/](chrome-extension/)** — Chrome side panel (reading, quotes, chat, graph)
- **[DesktopApp/](DesktopApp/)** — macOS **Context.app** (`bash scripts/install_app.sh`)

Both share the Python backend (`python3 main.py`, port 8765) and storage (`~/.kb/`).

## For AI agents

Read [docs/constitution.md](docs/constitution.md) and follow [init.md](init.md) at session start.

---

Inspired by [Andrej Karpathy's post](https://x.com/karpathy/status/2039805659525644595?lang=en).

Created by [Rebecca Joseph](https://github.com/rrebeccajjoseph) & [Ramya Iyer](https://github.com/riyer8).
