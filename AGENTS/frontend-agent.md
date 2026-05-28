# Frontend Agent

## Owns
- `DesktopApp/`

## Responsibilities
- SwiftUI macOS app
- Hotkey system (Cmd+Shift+C/G/S/W)
- Menu bar controls for recording (start, stop, flag important)
- Chat window UI
- Knowledge graph visualization
- Buckets of Life view (tree, filterable by time/activity)
- Relationship profiles UI (view, refine, edit)
- Settings panel (integrations, privacy, tone, relationship management)
- Proactive bot pop-up UI
- Hash → display name reverse rendering (UI layer only)

## Interfaces
- Calls: Python backend at `localhost:8765`
- Receives: proactive pop-up triggers from `/proactive` endpoint
- Renders: hashed names via `DesktopApp/Models/NameResolver.swift`

## Must Never
- Store any user data locally in the app (all persistence is backend)
- Expose hashed names in any UI element — always resolve to display names before rendering
- Add new backend endpoints without coordinating with infra-agent
- Use AppKit unless there is no SwiftUI equivalent

## Required Tests
- Hotkey registration doesn't conflict
- Chat sends correctly formed request and renders response
- Menu bar recording state reflects backend state
- Name resolution renders correctly from hash

## Notes
The frontend should be thin. Business logic lives in the backend. The frontend's job is
presentation and user input — nothing more. Keep view models simple.
