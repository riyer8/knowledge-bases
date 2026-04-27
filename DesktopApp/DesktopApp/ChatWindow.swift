import SwiftUI
import AppKit
import Foundation
import Combine

// MARK: - Chat Window Controller
class ChatWindowController: NSWindowController {
    static var shared: ChatWindowController?
    static let state = ChatWindowState()

    static func open(near petWindow: NSWindow, preferredPanel: ChatView.ChatPanel = .chat) {
        state.selectedPanel = preferredPanel
        if let existing = shared {
            existing.window?.makeKeyAndOrderFront(nil)
            return
        }

        let petFrame = petWindow.frame
        let chatSize = CGSize(width: 320, height: 420)
        var origin = CGPoint(
            x: petFrame.midX - chatSize.width / 2,
            y: petFrame.maxY + 8
        )
        if let screen = NSScreen.main {
            origin.x = max(8, min(origin.x, screen.frame.maxX - chatSize.width - 8))
            origin.y = max(8, min(origin.y, screen.frame.maxY - chatSize.height - 8))
        }

        let window = NSWindow(
            contentRect: NSRect(origin: origin, size: chatSize),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Chat"
        window.isReleasedWhenClosed = false
        window.level = .floating
        window.contentView = NSHostingView(rootView: ChatView(state: state, onClose: {
            shared?.window?.close()
            shared = nil
        }))

        let controller = ChatWindowController(window: window)
        shared = controller
        window.makeKeyAndOrderFront(nil)
    }

    static func closeWindow() {
        shared?.window?.close()
        shared = nil
    }
}

@MainActor
final class ChatWindowState: ObservableObject {
    @Published var selectedPanel: ChatView.ChatPanel = .chat
}

// MARK: - Chat View
struct ChatMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
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

    init(id: UUID = UUID(), kind: ManualInputKind, value: String, createdAt: Date = Date()) {
        self.id = id
        self.kind = kind
        self.value = value
        self.createdAt = createdAt
    }
}

@MainActor
final class ManualInputStore: ObservableObject {
    @Published private(set) var entries: [ManualInputEntry] = []
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?

    private let baseURL = URL(string: "http://127.0.0.1:8765")!
    private let iso8601 = ISO8601DateFormatter()

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
    }

    private struct BackendSubmitResponse: Codable {
        let ok: Bool
        let entry: BackendEntry
    }

    private struct ChatRequest: Codable {
        let prompt: String
    }

    private struct ChatResponse: Codable {
        let reply: String
    }

    init() {
        Task { await refreshEntries() }
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
            errorMessage = "Python backend unavailable. Start manual_input_server.py."
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
        return mapBackendEntry(decoded.entry) ?? ManualInputEntry(kind: kind, value: value)
    }

    func sendChat(prompt: String) async throws -> String {
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

    private func mapBackendEntry(_ input: BackendEntry) -> ManualInputEntry? {
        guard let kind = ManualInputKind(rawValue: input.kind.lowercased()) else { return nil }
        let date = iso8601.date(from: input.createdAt) ?? Date()
        let id = UUID(uuidString: input.id) ?? UUID()
        return ManualInputEntry(id: id, kind: kind, value: input.value, createdAt: date)
    }
}

struct ChatView: View {
    enum ChatPanel: String, CaseIterable, Identifiable {
        case chat = "Chat"
        case manual = "Manual Inputs"
        case graph = "Graph View"

        var id: String { rawValue }
    }

    @ObservedObject var state: ChatWindowState
    var onClose: () -> Void
    @StateObject private var manualInputStore = ManualInputStore()
    @State private var messages: [ChatMessage] = [
        ChatMessage(text: "hi, i'm text 👋 what's on your mind?", isUser: false)
    ]
    @State private var inputText: String = ""
    @State private var manualURLInput: String = ""
    @State private var manualTextInput: String = ""

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                HStack(spacing: 8) {
                    Circle().fill(Color(hex: "#ec4899")).frame(width: 10, height: 10)
                    Text("Desktop Pet")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundColor(Color(hex: "#3d2b1f"))
                }
                Spacer()
                Button(action: onClose) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.gray.opacity(0.6))
                        .font(.system(size: 16))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color(hex: "#fdf2f8"))

            Divider()

            Picker("Panel", selection: $state.selectedPanel) {
                ForEach(ChatPanel.allCases) { panel in
                    Text(panel.rawValue).tag(panel)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color(hex: "#fff7fb"))

            if state.selectedPanel == .chat {
                ScrollViewReader { proxy in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 10) {
                            ForEach(messages) { msg in
                                HStack {
                                    if msg.isUser { Spacer(minLength: 40) }
                                    Text(msg.text)
                                        .font(.system(size: 13, design: .rounded))
                                        .foregroundColor(msg.isUser ? .white : Color(hex: "#3d2b1f"))
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 8)
                                        .background(
                                            RoundedRectangle(cornerRadius: 14)
                                                .fill(msg.isUser ? Color(hex: "#ec4899") : Color(hex: "#fdf2f8"))
                                                .shadow(color: .black.opacity(0.06), radius: 3, y: 1)
                                        )
                                    if !msg.isUser { Spacer(minLength: 40) }
                                }
                                .id(msg.id)
                            }
                        }
                        .padding(14)
                    }
                    .background(Color(hex: "#fff7fb"))
                    .onChange(of: messages.count) {
                        if let last = messages.last {
                            withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                        }
                    }
                }
            } else if state.selectedPanel == .manual {
                VStack(spacing: 10) {
                    HStack {
                        Button("Upload Files") {
                            manualInputStore.importFilesFromPicker()
                        }
                        .buttonStyle(.borderedProminent)

                        Button("Refresh") {
                            Task { await manualInputStore.refreshEntries() }
                        }
                        .buttonStyle(.bordered)

                        Spacer()

                        Text("Saved: \(manualInputStore.entries.count)")
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal, 14)
                    .padding(.top, 4)

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
                    .padding(.horizontal, 14)

                    VStack(alignment: .leading, spacing: 6) {
                        Text("Raw Text")
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .foregroundColor(Color(hex: "#3d2b1f"))
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
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(spacing: 6) {
                                Text(entry.kind.rawValue.uppercased())
                                    .font(.system(size: 10, weight: .bold, design: .rounded))
                                    .foregroundColor(Color(hex: "#ec4899"))
                                Text(entry.createdAt.formatted(date: .abbreviated, time: .shortened))
                                    .font(.system(size: 10, design: .rounded))
                                    .foregroundColor(.secondary)
                            }
                            Text(entry.value)
                                .font(.system(size: 12, design: .rounded))
                                .lineLimit(2)
                        }
                        .padding(.vertical, 2)
                    }
                    .listStyle(.plain)
                }
                .background(Color(hex: "#fff7fb"))
            } else {
                GraphWindowView()
            }

            Divider()

            HStack(spacing: 10) {
                TextField("Say something...", text: $inputText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13, design: .rounded))
                    .onSubmit { sendMessage() }
                Button(action: sendMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 22))
                        .foregroundColor(inputText.isEmpty ? .gray.opacity(0.3) : Color(hex: "#ec4899"))
                }
                .buttonStyle(.plain)
                .disabled(inputText.isEmpty)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color(hex: "#fdf2f8"))
            .opacity(state.selectedPanel == .chat ? 1 : 0.35)
            .disabled(state.selectedPanel != .chat)
        }
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespaces)
        guard !text.isEmpty else { return }
        inputText = ""
        messages.append(ChatMessage(text: text, isUser: true))
        Task {
            do {
                let reply = try await manualInputStore.sendChat(prompt: text)
                messages.append(ChatMessage(text: reply, isUser: false))
            } catch {
                messages.append(ChatMessage(text: "Backend unavailable. Start manual_input_server.py.", isUser: false))
            }
        }
    }

}
