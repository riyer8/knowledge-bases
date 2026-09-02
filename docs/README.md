# Documentation

**Context** — local-first personal knowledge system. Start here.

---

## New here?

1. [Overview](overview.md) — what it does, 5-minute mental model
2. [Getting Started](getting-started.md) — install backend, extension, macOS app
3. [Architecture](architecture.md) — how the pieces connect

**AI agents / tomorrow's session:** [constitution.md](constitution.md) → [status.md](status.md) → [init.md](../init.md)

---

## Product

| Doc | Contents |
|---|---|
| [Overview](overview.md) | Features, quick start, data locations |
| [Vision](vision.md) | Product thesis, UX principles |
| [Architecture](architecture.md) | System design, modules, API summary, dependency graph |
| [Roadmap](roadmap.md) | Shipped milestones + phased plan |
| [Status](status.md) | **Current state** — read this before every session |

---

## Development

| Doc | Contents |
|---|---|
| [Getting Started](getting-started.md) | Backend, launcher, extension, macOS app, tests |
| [Configuration](configuration.md) | All `.env` variables and config object |
| [Storage](storage.md) | `~/.kb/` layout and write rules |
| [API Reference](api.md) | HTTP endpoints for all clients |
| [Project Structure](project-structure.md) | Repo tree and hotkeys |
| [Testing](testing.md) | Unit tests + privacy eval harness |
| [Chrome Extension](../chrome-extension/README.md) | Extension setup and troubleshooting |

---

## Engineering (agents & contributors)

| Doc | Contents |
|---|---|
| [Constitution](constitution.md) | **Read first** — engineering rules and non-negotiables |
| [init.md](../init.md) | Session initialization protocol (repo root) |
| [Engineering Workflow](engineering.md) | Scope declarations, traces, postmortems |
| [Agent Ownership](agents.md) | Module boundaries and responsibilities |
| [Decisions](decisions.md) | Architectural decision log |
| [Traces](traces/) | Optional session execution logs |

---

## Specifications

| Spec | Purpose |
|---|---|
| [privacy-pipeline.md](specs/privacy-pipeline.md) | Mandatory privacy gate (auto-pause, PII, hashing) |
| [event-schema.md](specs/event-schema.md) | Raw and clean event contract |
| [name-anonymization.md](specs/name-anonymization.md) | Hash → display name mapping |
| [buckets.md](specs/buckets.md) | Life bucket taxonomy (Phase 3) |

---

## Repo map (top level)

```text
knowledge-bases/
├── core/              # Python backend
├── chrome-extension/  # Chrome side panel
├── DesktopApp/        # macOS Context.app source
├── docs/              # ← you are here
├── scripts/           # Launcher, install, build helpers
├── tests/             # pytest suite + eval fixtures
├── demo/              # Presentation seed script
├── init.md            # Session protocol (repo root)
```

Runtime data: `~/.kb/` (not in repo).
