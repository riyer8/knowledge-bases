# Context

A local-first personal knowledge system — highlight what you read, keep notes, copy them onto your own site.

## Quick links

| | |
|---|---|
| **Start here** | [docs/README.md](docs/README.md) |
| **Run it** | [docs/getting-started.md](docs/getting-started.md) |
| **Current status** | [docs/status.md](docs/status.md) |
| **Architecture** | [docs/architecture.md](docs/architecture.md) |

## Clients

- **[chrome-extension/](chrome-extension/)** — Chrome side panel (highlight, notes, bookshelf JSON, chat, graph)
- **[DesktopApp/](DesktopApp/)** — macOS **Context.app** (`bash scripts/install_app.sh`)

Both share the Python backend (`python3 main.py`, port 8765) and storage (`~/.kb/`).

**Context dashboard:** [http://127.0.0.1:8765/app/](http://127.0.0.1:8765/app/) — the same notes document in a full local UI.

Primary loop: highlight on the page → notes in the side panel → Copy JSON into your site. Chat and graph stay. Life and Wiki are [archived](docs/archived.md) (still in the repo, hidden from nav).

## For AI agents

Read [docs/constitution.md](docs/constitution.md) and follow [init.md](init.md) at session start.

---

Inspired by [Andrej Karpathy's post](https://x.com/karpathy/status/2039805659525644595?lang=en).

Created by [Rebecca Joseph](https://github.com/rrebeccajoseph) & [Ramya Iyer](https://github.com/riyer8).
