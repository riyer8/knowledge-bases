import SwiftUI
import AppKit
import Foundation
import Combine

enum MainPanel: String, CaseIterable, Identifiable {
    case chat = "Chat"
    case manual = "Manual Inputs"
    case graph = "Graph View"

    var id: String { rawValue }
}

class MainWindowController: NSWindowController, NSWindowDelegate {
    static var shared: MainWindowController?
    static let state = MainWindowState()

    static func open(near petWindow: NSWindow, preferredPanel: MainPanel = .chat) {
        state.selectedPanel = preferredPanel
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
        window.title = "Desktop Pet"
        window.minSize = CGSize(width: 460, height: 600)
        window.isReleasedWhenClosed = false
        window.level = .floating
        window.contentView = NSHostingView(rootView: MainWindowView(state: state))

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
    @Published var selectedPanel: MainPanel = .chat
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
            errorMessage = "Python backend unavailable. Start python3 main.py."
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
    @Environment(\.colorScheme) private var colorScheme
    @StateObject private var manualInputStore = ManualInputStore()
    @State private var messages: [ChatMessage] = [
        ChatMessage(text: "hi, i'm text 👋 what's on your mind?", isUser: false)
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

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                HStack(spacing: 8) {
                    Circle().fill(Color(hex: "#ec4899")).frame(width: 10, height: 10)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Desktop Pet Assistant")
                            .font(.system(size: 14, weight: .semibold, design: .rounded))
                            .foregroundColor(panelTitleColor)
                        Text("Chat, manual inputs, and graph insights")
                            .font(.system(size: 11, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                }
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(headerBackground)

            Divider()

            Picker("Panel", selection: $state.selectedPanel) {
                ForEach(MainPanel.allCases) { panel in
                    Text(panel.rawValue).tag(panel)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(sectionBackground)

            if state.selectedPanel == .chat {
                ChatScreenView(
                    messages: $messages,
                    assistantTextColor: assistantTextColor,
                    assistantBubble: assistantBubble,
                    sectionBackground: sectionBackground,
                    chatHintBackground: chatHintBackground
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
                        text: "Chat backend unavailable. Start python3 main.py from repo root.",
                        isUser: false
                    )
                )
            }
        }
    }

    private func sendChat(prompt: String) async throws -> String {
        struct ChatRequest: Codable { let prompt: String }
        struct ChatResponse: Codable { let reply: String }
        let baseURL = URL(string: "http://127.0.0.1:8765")!
        var request = URLRequest(url: baseURL.appendingPathComponent("chat"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(ChatRequest(prompt: prompt))

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(ChatResponse.self, from: data).reply
    }
}

struct ManualInputsPanel: View {
    @ObservedObject var manualInputStore: ManualInputStore
    @Binding var manualURLInput: String
    @Binding var manualTextInput: String
    let panelTitleColor: Color
    let sectionBackground: Color
    var onOpenSeparateWindow: (() -> Void)? = nil

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

            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Label("Files", systemImage: "doc.badge.plus")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundColor(panelTitleColor)
                    Spacer()
                    Button("Add Files") { manualInputStore.importFilesFromPicker() }
                        .buttonStyle(.borderedProminent)
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

            List(manualInputStore.entries) { entry in
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
            .listStyle(.plain)
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
