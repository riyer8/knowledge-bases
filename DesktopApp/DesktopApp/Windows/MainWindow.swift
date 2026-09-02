import SwiftUI
import AppKit
import Foundation
import Combine

enum MainPanel: String, CaseIterable, Identifiable {
    case home = "Home"
    case chat = "Chat"
    case library = "Library"
    case life = "Life"
    case manual = "Manual Inputs"
    case graph = "Graph View"
    case settings = "Settings"

    var id: String { rawValue }
}

class MainWindowController: NSWindowController, NSWindowDelegate {
    static var shared: MainWindowController?
    static let state = MainWindowState()
    static var settings = DesktopPetSettings()

    static func open(near petWindow: NSWindow, preferredPanel: MainPanel? = nil) {
        if let preferredPanel {
            state.selectedPanel = preferredPanel
        }
        if let existing = shared {
            if existing.window?.isVisible == true {
                existing.window?.makeKeyAndOrderFront(nil)
                return
            }
            shared = nil
        }

        let petFrame = petWindow.frame
        let size = CGSize(width: 520, height: 680)
        var origin = CGPoint(
            x: petFrame.midX - size.width / 2,
            y: petFrame.maxY + 8
        )
        if let screen = NSScreen.main {
            origin.x = max(8, min(origin.x, screen.frame.maxX - size.width - 8))
            origin.y = max(8, min(origin.y, screen.frame.maxY - size.height - 8))
        }

        let window = NSWindow(
            contentRect: NSRect(origin: origin, size: size),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Context"
        window.minSize = CGSize(width: 460, height: 600)
        window.isReleasedWhenClosed = false
        window.level = .normal
        window.contentView = NSHostingView(rootView: MainWindowView(state: state, settings: settings))

        let controller = MainWindowController(window: window)
        window.delegate = controller
        shared = controller
        window.makeKeyAndOrderFront(nil)
    }

    static func closeWindow() {
        shared?.window?.close()
        shared = nil
    }

    func windowWillClose(_ notification: Notification) {
        Self.shared = nil
    }
}

@MainActor
final class MainWindowState: ObservableObject {
    @Published var selectedPanel: MainPanel = .home
}

enum ManualInputKind: String, Codable {
    case file
    case url
    case text
}

struct ManualInputEntry: Identifiable, Codable {
    let id: UUID
    let kind: ManualInputKind
    let value: String
    let createdAt: Date
    let sourcePath: String?
    let text: String?
    let url: String?
}

@MainActor
final class ManualInputStore: ObservableObject {
    @Published private(set) var entries: [ManualInputEntry] = []
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published private(set) var hasFinishedInitialLoad = false

    private let baseURL = URL(string: "http://127.0.0.1:8765")!
    private let iso8601 = ISO8601DateFormatter()
    private var hasInitialLoad = false

    private struct BackendPayload: Codable {
        let kind: String
        let value: String
        let createdAt: String
    }

    private struct BackendEntry: Codable {
        let id: String
        let kind: String
        let value: String
        let createdAt: String
        let sourcePath: String?
        let text: String?
        let url: String?
    }

    private struct BackendSubmitResponse: Codable {
        let ok: Bool
        let entry: BackendEntry
    }

    func ensureInitialLoad() async {
        guard !hasInitialLoad else { return }
        hasInitialLoad = true
        await refreshEntries()
        hasFinishedInitialLoad = true
    }

    func addURL(_ rawValue: String) {
        let value = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        guard let parsed = URL(string: value), parsed.scheme != nil else {
            errorMessage = "Enter a valid URL (for example, https://example.com)."
            return
        }
        Task {
            do {
                let entry = try await submit(kind: .url, value: value)
                entries.insert(entry, at: 0)
                errorMessage = nil
            } catch {
                errorMessage = "Failed to send URL: \(error.localizedDescription)"
            }
        }
    }

    func addText(_ rawValue: String) {
        let value = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        Task {
            do {
                let entry = try await submit(kind: .text, value: value)
                entries.insert(entry, at: 0)
                errorMessage = nil
            } catch {
                errorMessage = "Failed to send text input: \(error.localizedDescription)"
            }
        }
    }

    func importFilesFromPicker() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        panel.prompt = "Upload"
        panel.title = "Upload Manual Input Files"

        guard panel.runModal() == .OK else { return }
        let urls = panel.urls
        guard !urls.isEmpty else { return }

        Task {
            do {
                for sourceURL in urls {
                    let entry = try await submit(kind: .file, value: sourceURL.path)
                    entries.insert(entry, at: 0)
                }
                errorMessage = nil
            } catch {
                errorMessage = "Failed to send file(s): \(error.localizedDescription)"
            }
        }
    }

    func refreshEntries() async {
        isLoading = true
        defer { isLoading = false }
        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("manual-inputs"))
            request.httpMethod = "GET"
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            let backendEntries = try JSONDecoder().decode([BackendEntry].self, from: data)
            entries = backendEntries.compactMap { mapBackendEntry($0) }
            errorMessage = nil
        } catch {
            errorMessage = "Sift isn't responding. Make sure start.sh is still running."
        }
    }

    private func submit(kind: ManualInputKind, value: String) async throws -> ManualInputEntry {
        var request = URLRequest(url: baseURL.appendingPathComponent("manual-input"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let payload = BackendPayload(
            kind: kind.rawValue,
            value: value,
            createdAt: iso8601.string(from: Date())
        )
        request.httpBody = try JSONEncoder().encode(payload)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        let decoded = try JSONDecoder().decode(BackendSubmitResponse.self, from: data)
        return mapBackendEntry(decoded.entry) ?? ManualInputEntry(
            id: UUID(),
            kind: kind,
            value: value,
            createdAt: Date(),
            sourcePath: nil,
            text: nil,
            url: nil
        )
    }

    private func mapBackendEntry(_ input: BackendEntry) -> ManualInputEntry? {
        guard let kind = ManualInputKind(rawValue: input.kind.lowercased()) else { return nil }
        let date = iso8601.date(from: input.createdAt) ?? Date()
        let id = UUID(uuidString: input.id) ?? UUID()
        return ManualInputEntry(
            id: id,
            kind: kind,
            value: input.value,
            createdAt: date,
            sourcePath: input.sourcePath,
            text: input.text,
            url: input.url
        )
    }
}

struct MainWindowView: View {
    @ObservedObject var state: MainWindowState
    @ObservedObject var settings: DesktopPetSettings
    @Environment(\.colorScheme) private var colorScheme
    @StateObject private var manualInputStore = ManualInputStore()
    @StateObject private var libraryStore = LibraryStore()
    @StateObject private var lifeStore = LifeStore()
    @State private var messages: [ChatMessage] = [
        ChatMessage(text: "hi, i'm sift 👋 what's on your mind?\n\nTry: \"What did I work on this week?\"", isUser: false)
    ]
    @State private var inputText: String = ""
    @State private var manualURLInput: String = ""
    @State private var manualTextInput: String = ""

    private var isDarkMode: Bool { colorScheme == .dark }
    private var windowBackground: Color { isDarkMode ? Color(nsColor: .windowBackgroundColor) : Color(hex: "#fff7fb") }
    private var headerBackground: Color { isDarkMode ? Color(nsColor: .controlBackgroundColor) : Color(hex: "#fdf2f8") }
    private var sectionBackground: Color { isDarkMode ? Color(nsColor: .underPageBackgroundColor) : Color(hex: "#fff7fb") }
    private var panelTitleColor: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }
    private var assistantBubble: Color { isDarkMode ? Color(nsColor: .controlColor) : Color(hex: "#fdf2f8") }
    private var assistantTextColor: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }
    private var chatHintBackground: Color { isDarkMode ? Color(nsColor: .textBackgroundColor) : Color(hex: "#fff1f8") }
    private var tabBackground: Color { isDarkMode ? Color(nsColor: .windowBackgroundColor) : Color(hex: "#fdf2f8") }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                HStack(spacing: 8) {
                    Button {
                        state.selectedPanel = .home
                    } label: {
                        HStack(spacing: 8) {
                            Circle().fill(Color(hex: "#ec4899")).frame(width: 10, height: 10)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Context")
                                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                                    .foregroundColor(panelTitleColor)
                                Text("Your personal knowledge assistant")
                                    .font(.system(size: 11, design: .rounded))
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
                Spacer()
                Button {
                    state.selectedPanel = .settings
                } label: {
                    Label("Settings", systemImage: "gearshape.fill")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                }
                .buttonStyle(.bordered)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(headerBackground)

            Divider()

            CutePanelTabs(selectedPanel: $state.selectedPanel, background: tabBackground)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(sectionBackground)

            if state.selectedPanel == .home {
                LandingHomeView(
                    selectedPanel: $state.selectedPanel,
                    panelTitleColor: panelTitleColor,
                    showLoading: !manualInputStore.hasFinishedInitialLoad || manualInputStore.isLoading
                )
            } else if state.selectedPanel == .chat {
                ChatScreenView(
                    messages: $messages,
                    assistantTextColor: assistantTextColor,
                    assistantBubble: assistantBubble,
                    sectionBackground: sectionBackground,
                    chatHintBackground: chatHintBackground
                )
            } else if state.selectedPanel == .library {
                LibraryPanelView(
                    libraryStore: libraryStore,
                    panelTitleColor: panelTitleColor,
                    sectionBackground: sectionBackground
                )
            } else if state.selectedPanel == .life {
                LifePanelView(
                    lifeStore: lifeStore,
                    panelTitleColor: panelTitleColor,
                    sectionBackground: sectionBackground
                )
            } else if state.selectedPanel == .manual {
                ManualInputsPanel(
                    manualInputStore: manualInputStore,
                    manualURLInput: $manualURLInput,
                    manualTextInput: $manualTextInput,
                    panelTitleColor: panelTitleColor,
                    sectionBackground: sectionBackground,
                    onOpenSeparateWindow: {
                        let anchor = MainWindowController.shared?.window ?? NSApp.keyWindow ?? NSApp.windows.first
                        if let anchor {
                            ManualInputsWindowController.open(near: anchor)
                        }
                    }
                )
            } else if state.selectedPanel == .settings {
                SettingsPanel(
                    settings: settings,
                    clearLibraryAction: clearSavedLibrary,
                    deleteAllAction: deleteAllData
                )
            } else {
                GraphWindowView()
            }

            if state.selectedPanel == .chat {
                Divider()
                HStack(spacing: 10) {
                    TextField("Say something...", text: $inputText)
                        .textFieldStyle(.plain)
                        .font(.system(size: 14, design: .rounded))
                        .onSubmit { sendMessage() }
                    Button(action: sendMessage) {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 24))
                            .foregroundColor(inputText.isEmpty ? .gray.opacity(0.3) : Color(hex: "#ec4899"))
                    }
                    .buttonStyle(.plain)
                    .disabled(inputText.isEmpty)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(headerBackground)
            }
        }
        .background(windowBackground)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .preferredColorScheme(settings.preferredColorScheme)
        .task { await manualInputStore.ensureInitialLoad() }
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespaces)
        guard !text.isEmpty else { return }
        inputText = ""
        messages.append(ChatMessage(text: text, isUser: true))
        Task {
            do {
                let reply = try await sendChat(prompt: text)
                messages.append(ChatMessage(text: reply, isUser: false))
            } catch {
                messages.append(
                    ChatMessage(
                        text: "Sift isn't responding. Make sure start.sh is still running in your terminal.",
                        isUser: false
                    )
                )
            }
        }
    }

    private func sendChat(prompt: String) async throws -> String {
        struct ChatTurn: Codable {
            let role: String
            let content: String
        }
        struct ChatRequest: Codable {
            let prompt: String
            let history: [ChatTurn]
            let includeCalendar: Bool

            enum CodingKeys: String, CodingKey {
                case prompt, history
                case includeCalendar = "include_calendar"
            }
        }
        struct ChatResponse: Codable { let reply: String }

        let history = messages.dropFirst().map {
            ChatTurn(role: $0.isUser ? "user" : "assistant", content: $0.text)
        }

        let baseURL = URL(string: "http://127.0.0.1:8765")!
        var request = URLRequest(url: baseURL.appendingPathComponent("chat"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(
            ChatRequest(prompt: prompt, history: history, includeCalendar: true)
        )

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(ChatResponse.self, from: data).reply
    }

    private func clearSavedLibrary() async throws {
        try await DataResetService.clearLibrary()
        await libraryStore.refreshAll()
    }

    private func deleteAllData() async throws {
        try await DataResetService.deleteAll()
        await resetClientStateAfterFullDelete()
    }

    @MainActor
    private func resetClientStateAfterFullDelete() async {
        messages = [
            ChatMessage(
                text: "hi, i'm sift 👋 what's on your mind?\n\nTry: \"What did I work on this week?\"",
                isUser: false
            ),
        ]
        inputText = ""
        await manualInputStore.refreshEntries()
        await libraryStore.refreshAll()
        await lifeStore.refreshAll()
    }
}

private struct CutePanelTabs: View {
    @Binding var selectedPanel: MainPanel
    let background: Color

    var body: some View {
        HStack(spacing: 8) {
            tabButton(.chat, icon: "message.fill")
            tabButton(.library, icon: "books.vertical")
            tabButton(.life, icon: "chart.pie")
            tabButton(.manual, icon: "tray.full")
            tabButton(.graph, icon: "point.3.connected.trianglepath.dotted")
        }
        .padding(6)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(background)
        )
    }

    private func tabButton(_ panel: MainPanel, icon: String) -> some View {
        let isSelected = selectedPanel == panel
        return Button {
            selectedPanel = panel
        } label: {
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 10))
                Text(panel.rawValue)
                    .font(.system(size: 11, weight: .semibold, design: .rounded))
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 7)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 9)
                    .fill(isSelected ? Color(hex: "#ec4899").opacity(0.18) : Color.clear)
            )
            .foregroundColor(isSelected ? Color(hex: "#ec4899") : .secondary)
        }
        .buttonStyle(.plain)
    }
}

private struct LandingHomeView: View {
    @Binding var selectedPanel: MainPanel
    let panelTitleColor: Color
    let showLoading: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if showLoading {
                HStack(spacing: 8) {
                    ProgressView()
                        .scaleEffect(0.65)
                    Text("Loading your workspace...")
                        .font(.system(size: 12, design: .rounded))
                        .foregroundColor(.secondary)
                }
                .padding(.top, 10)
            }
        
            Text("What would you like to do?")
                .font(.system(size: 14, weight: .semibold, design: .rounded))
                .foregroundColor(panelTitleColor)
                .padding(.top, 10)

            HStack(spacing: 10) {
                homeCard(title: "Chat", subtitle: "Talk with Sift", icon: "message.fill", panel: .chat)
                homeCard(title: "Library", subtitle: "Saved pages and quotes", icon: "books.vertical", panel: .library)
                homeCard(title: "Life", subtitle: "Time and relationships", icon: "chart.pie", panel: .life)
                homeCard(title: "Graph", subtitle: "Explore connections", icon: "point.3.connected.trianglepath.dotted", panel: .graph)
            }
            .padding(.top, 20)
            Spacer()
        }
        .padding(.horizontal, 14)
        .padding(.bottom, 12)
    }

    private func homeCard(title: String, subtitle: String, icon: String, panel: MainPanel) -> some View {
        Button {
            selectedPanel = panel
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "#ec4899"))
                Text(title)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                Text(subtitle)
                    .font(.system(size: 10, design: .rounded))
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(
                RoundedRectangle(cornerRadius: 11)
                    .fill(Color(hex: "#ec4899").opacity(0.08))
            )
        }
        .buttonStyle(.plain)
    }
}

struct ManualInputsPanel: View {
    @ObservedObject var manualInputStore: ManualInputStore
    @Binding var manualURLInput: String
    @Binding var manualTextInput: String
    let panelTitleColor: Color
    let sectionBackground: Color
    var onOpenSeparateWindow: (() -> Void)? = nil
    @State private var showLogsPanel = true
    private let logsBottomID = "manual-logs-bottom"
    private var logEntries: [ManualInputEntry] {
        manualInputStore.entries.reversed()
    }

    var body: some View {
        VStack(spacing: 10) {
            HStack {
                Button("Refresh") {
                    Task { await manualInputStore.refreshEntries() }
                }
                .buttonStyle(.bordered)

                if let onOpenSeparateWindow {
                    Button("Open Separate Window", action: onOpenSeparateWindow)
                        .buttonStyle(.bordered)
                }

                Spacer()

                Text("Saved: \(manualInputStore.entries.count)")
                    .font(.system(size: 11, weight: .medium, design: .rounded))
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 14)
            .padding(.top, 4)

            HStack {
                Text("Add Context")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundColor(panelTitleColor)
                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.top, 2)

            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Label("Files", systemImage: "doc.badge.plus")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundColor(panelTitleColor)
                    Spacer()
                    Button("Add Files") { manualInputStore.importFilesFromPicker() }
                        .buttonStyle(.bordered)
                }
                Text("Choose one or more files from your computer.")
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(RoundedRectangle(cornerRadius: 10).fill(sectionBackground))
            .padding(.horizontal, 14)

            VStack(alignment: .leading, spacing: 6) {
                Label("URL", systemImage: "link")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundColor(panelTitleColor)
                HStack(spacing: 8) {
                    TextField("Paste URL (https://...)", text: $manualURLInput)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(size: 12, design: .rounded))
                    Button("Add URL") {
                        manualInputStore.addURL(manualURLInput)
                        manualURLInput = ""
                    }
                    .buttonStyle(.bordered)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(RoundedRectangle(cornerRadius: 10).fill(sectionBackground))
            .padding(.horizontal, 14)

            VStack(alignment: .leading, spacing: 6) {
                Label("Raw Text", systemImage: "text.alignleft")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundColor(panelTitleColor)
                TextEditor(text: $manualTextInput)
                    .font(.system(size: 12, design: .rounded))
                    .frame(minHeight: 70, maxHeight: 90)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.gray.opacity(0.18), lineWidth: 1)
                    )
                HStack {
                    Spacer()
                    Button("Add Text") {
                        manualInputStore.addText(manualTextInput)
                        manualTextInput = ""
                    }
                    .buttonStyle(.bordered)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(RoundedRectangle(cornerRadius: 10).fill(sectionBackground))
            .padding(.horizontal, 14)

            if let error = manualInputStore.errorMessage {
                Text(error)
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.red.opacity(0.85))
                    .padding(.horizontal, 14)
            }

            if manualInputStore.isLoading {
                ProgressView("Loading manual inputs...")
                    .font(.system(size: 11, design: .rounded))
                    .padding(.horizontal, 14)
            }

            HStack {
                Text("Recent Log")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundColor(panelTitleColor)
                Spacer()
                Button {
                    showLogsPanel.toggle()
                } label: {
                    Label(showLogsPanel ? "Hide" : "Show", systemImage: "list.bullet.rectangle")
                        .font(.system(size: 10, design: .rounded))
                }
                .buttonStyle(.bordered)
                .help("Show or hide the log list")
            }
            .padding(.horizontal, 14)
            .padding(.top, 4)

            if showLogsPanel {
                ScrollViewReader { proxy in
                    List {
                        ForEach(logEntries) { entry in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack(alignment: .top, spacing: 8) {
                                    Text(kindBadgeLabel(for: entry))
                                        .font(.system(size: 10, weight: .bold, design: .rounded))
                                        .foregroundColor(Color(hex: "#ec4899"))
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 3)
                                        .background(Color(hex: "#ec4899").opacity(0.12))
                                        .clipShape(Capsule())

                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(manualEntryTitle(entry))
                                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                                            .lineLimit(1)
                                        Text(manualEntryDetail(entry))
                                            .font(.system(size: 11, design: .rounded))
                                            .foregroundColor(.secondary)
                                            .lineLimit(2)
                                    }
                                    Spacer(minLength: 8)
                                    Text(entry.createdAt.formatted(date: .abbreviated, time: .shortened))
                                        .font(.system(size: 10, design: .rounded))
                                        .foregroundColor(.secondary)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                        Color.clear
                            .frame(height: 1)
                            .id(logsBottomID)
                    }
                    .listStyle(.plain)
                    .onAppear {
                        proxy.scrollTo(logsBottomID, anchor: .bottom)
                    }
                    .onChange(of: manualInputStore.entries.count) {
                        withAnimation(.easeOut(duration: 0.18)) {
                            proxy.scrollTo(logsBottomID, anchor: .bottom)
                        }
                    }
                }
            } else {
                // Keep layout height stable when logs are hidden.
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.clear)
                    .frame(minHeight: 220)
                    .padding(.horizontal, 14)
            }
        }
        .background(sectionBackground)
    }

    private func kindBadgeLabel(for entry: ManualInputEntry) -> String {
        switch entry.kind {
        case .file:
            return "FILE"
        case .url:
            return "URL"
        case .text:
            return "TEXT"
        }
    }

    private func manualEntryTitle(_ entry: ManualInputEntry) -> String {
        switch entry.kind {
        case .file:
            let path = entry.sourcePath ?? entry.value
            return URL(fileURLWithPath: path).lastPathComponent
        case .url:
            let raw = entry.url ?? entry.value
            if let parsed = URL(string: raw), let host = parsed.host, !host.isEmpty {
                return host
            }
            return raw
        case .text:
            let raw = (entry.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            if raw.isEmpty { return "Text note" }
            return String(raw.prefix(70))
        }
    }

    private func manualEntryDetail(_ entry: ManualInputEntry) -> String {
        switch entry.kind {
        case .file:
            return entry.sourcePath ?? entry.value
        case .url:
            return entry.url ?? entry.value
        case .text:
            let raw = (entry.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            if raw.isEmpty { return entry.value }
            return String(raw.prefix(160))
        }
    }
}
