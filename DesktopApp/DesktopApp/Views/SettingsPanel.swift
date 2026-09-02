import SwiftUI

struct SettingsPanel: View {
    @ObservedObject var settings: DesktopPetSettings
    @StateObject private var backendSettings = BackendSettingsStore()
    let clearLibraryAction: () async throws -> Void
    let deleteAllAction: () async throws -> Void

    @State private var selectedTheme: AppThemeMode
    @State private var selectedIcon: PetIconOption
    @State private var proactiveMinutes: Int
    @State private var llmProvider = "auto"
    @State private var openaiModel = ""
    @State private var chatModel = ""
    @State private var openaiKey = ""
    @State private var anthropicKey = ""
    @State private var showLibraryClearConfirm = false
    @State private var showFinalDeleteConfirm = false
    @State private var isDeleting = false
    @State private var feedbackMessage: String?

    init(
        settings: DesktopPetSettings,
        clearLibraryAction: @escaping () async throws -> Void,
        deleteAllAction: @escaping () async throws -> Void
    ) {
        self._settings = ObservedObject(wrappedValue: settings)
        self.clearLibraryAction = clearLibraryAction
        self.deleteAllAction = deleteAllAction
        self._selectedTheme = State(initialValue: settings.themeMode)
        self._selectedIcon = State(initialValue: settings.petIcon)
        self._proactiveMinutes = State(initialValue: settings.proactiveIntervalMinutes)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text("Settings")
                    .font(.system(size: 15, weight: .semibold, design: .rounded))

                VStack(alignment: .leading, spacing: 8) {
                    Text("Theme")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                    Picker("Theme", selection: $selectedTheme) {
                        ForEach(AppThemeMode.allCases) { mode in
                            Text(mode.label).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Pet Icon")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                    Picker("Pet Icon", selection: $selectedIcon) {
                        ForEach(PetIconOption.allCases) { option in
                            Label(option.label, systemImage: option.symbolName).tag(option)
                        }
                    }
                    .pickerStyle(.segmented)
                    Text("More icon styles can be added here later.")
                        .font(.system(size: 11, design: .rounded))
                        .foregroundColor(.secondary)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Proactive insights")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                    Stepper(value: $proactiveMinutes, in: 5...120, step: 5) {
                        Text("Check every \(proactiveMinutes) minutes")
                            .font(.system(size: 11, design: .rounded))
                    }
                    Text("How often Sift checks for meetings, emails, and life-balance patterns.")
                        .font(.system(size: 11, design: .rounded))
                        .foregroundColor(.secondary)
                }

                Divider()

                Link(destination: URL(string: "http://127.0.0.1:8765/app/")!) {
                    Label("Open full wiki in browser", systemImage: "book.pages")
                        .font(.system(size: 12, design: .rounded))
                }
                .padding(.bottom, 4)

                aiProviderSection

                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("Data")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                    Text("Clear saved library removes pages and quotes but keeps captured memory. Delete everything wipes all local knowledge.")
                        .font(.system(size: 11, design: .rounded))
                        .foregroundColor(.secondary)
                    Button("Clear Saved Library") {
                        showLibraryClearConfirm = true
                    }
                    .disabled(isDeleting)
                    Button(role: .destructive) {
                        showFinalDeleteConfirm = true
                    } label: {
                        if isDeleting {
                            ProgressView()
                                .controlSize(.small)
                        } else {
                            Text("Delete All Data")
                        }
                    }
                    .disabled(isDeleting)
                }

                if let feedbackMessage {
                    Text(feedbackMessage)
                        .font(.system(size: 11, design: .rounded))
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
        }
        .task { await loadBackendSettings() }
        .alert("Clear saved library?", isPresented: $showLibraryClearConfirm) {
            Button("Cancel", role: .cancel) {}
            Button("Clear Library", role: .destructive) {
                Task { await runClearLibrary() }
            }
        } message: {
            Text("Removes saved pages, quotes, and per-page chats. Captured memory, buckets, and integrations stay intact.")
        }
        .alert("Delete all data?", isPresented: $showFinalDeleteConfirm) {
            Button("Cancel", role: .cancel) {}
            Button("Delete Everything", role: .destructive) {
                Task { await runDeleteAll() }
            }
        } message: {
            Text("Permanently removes all knowledge from ~/.kb/ including events, memory, relationships, and integration tokens. Cannot be undone.")
        }
        .onChange(of: selectedTheme) {
            guard settings.themeMode != selectedTheme else { return }
            DispatchQueue.main.async {
                settings.themeMode = selectedTheme
            }
        }
        .onChange(of: selectedIcon) {
            guard settings.petIcon != selectedIcon else { return }
            DispatchQueue.main.async {
                settings.petIcon = selectedIcon
            }
        }
        .onChange(of: proactiveMinutes) {
            guard settings.proactiveIntervalMinutes != proactiveMinutes else { return }
            DispatchQueue.main.async {
                settings.proactiveIntervalMinutes = proactiveMinutes
            }
        }
        .onReceive(settings.$themeMode) { current in
            if selectedTheme != current {
                selectedTheme = current
            }
        }
        .onReceive(settings.$petIcon) { current in
            if selectedIcon != current {
                selectedIcon = current
            }
        }
        .onReceive(settings.$proactiveIntervalMinutes) { current in
            if proactiveMinutes != current {
                proactiveMinutes = current
            }
        }
    }

    @ViewBuilder
    private var aiProviderSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("AI provider")
                .font(.system(size: 12, weight: .semibold, design: .rounded))
            Text("Add an API key to use cloud models, or leave on Auto to use OpenAI when configured, otherwise local Ollama.")
                .font(.system(size: 11, design: .rounded))
                .foregroundColor(.secondary)

            if backendSettings.isLoading {
                ProgressView()
                    .controlSize(.small)
            } else if let backend = backendSettings.settings {
                Text("Active provider: \(backend.llmProvider)")
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)

                Picker("Provider", selection: $llmProvider) {
                    Text("Auto").tag("auto")
                    Text("Ollama").tag("ollama")
                    Text("OpenAI").tag("openai")
                    Text("Anthropic").tag("anthropic")
                }
                .pickerStyle(.menu)

                SecureField("OpenAI API key", text: $openaiKey)
                    .textFieldStyle(.roundedBorder)
                Text(openaiKeyHint(for: backend))
                    .font(.system(size: 10, design: .rounded))
                    .foregroundColor(.secondary)

                SecureField("Anthropic API key", text: $anthropicKey)
                    .textFieldStyle(.roundedBorder)
                Text(anthropicKeyHint(for: backend))
                    .font(.system(size: 10, design: .rounded))
                    .foregroundColor(.secondary)

                TextField("OpenAI model", text: $openaiModel)
                    .textFieldStyle(.roundedBorder)
                TextField("Ollama chat model", text: $chatModel)
                    .textFieldStyle(.roundedBorder)

                Button(backendSettings.isSaving ? "Saving…" : "Save API settings") {
                    Task { await saveBackendSettings() }
                }
                .disabled(backendSettings.isSaving)

                if let saveMessage = backendSettings.saveMessage {
                    Text(saveMessage)
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.secondary)
                }

                Text("Config file: \(backend.envPath)")
                    .font(.system(size: 10, design: .rounded))
                    .foregroundColor(.secondary)
                    .textSelection(.enabled)
            } else if let error = backendSettings.errorMessage {
                Text(error)
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)
                Button("Retry") {
                    Task { await loadBackendSettings() }
                }
            }
        }
    }

    private func openaiKeyHint(for backend: BackendSettings) -> String {
        if backend.openaiConfigured {
            return "Configured (\(backend.openaiKeyHint)) — leave blank to keep current key"
        }
        return "Not set — paste your key from platform.openai.com"
    }

    private func anthropicKeyHint(for backend: BackendSettings) -> String {
        if backend.anthropicConfigured {
            return "Configured (\(backend.anthropicKeyHint)) — leave blank to keep current key"
        }
        return "Optional — for Anthropic provider"
    }

    private func loadBackendSettings() async {
        await backendSettings.load()
        guard let backend = backendSettings.settings else { return }
        llmProvider = backend.llmProviderSetting
        openaiModel = backend.openaiModel
        chatModel = backend.chatModel
        openaiKey = ""
        anthropicKey = ""
    }

    private func saveBackendSettings() async {
        let ok = await backendSettings.save(
            llmProvider: llmProvider,
            openaiModel: openaiModel,
            chatModel: chatModel,
            openaiApiKey: openaiKey,
            anthropicApiKey: anthropicKey
        )
        if ok {
            openaiKey = ""
            anthropicKey = ""
        }
    }

    private func runClearLibrary() async {
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await clearLibraryAction()
            feedbackMessage = "Saved library cleared."
        } catch {
            feedbackMessage = "Failed to clear library. Ensure backend is running."
        }
    }

    private func runDeleteAll() async {
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await deleteAllAction()
            feedbackMessage = "All local data was deleted."
        } catch {
            feedbackMessage = "Failed to delete data. Ensure backend is running."
        }
    }
}
