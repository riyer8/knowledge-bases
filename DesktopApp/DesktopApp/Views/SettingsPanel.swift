import SwiftUI

struct SettingsPanel: View {
    @ObservedObject var settings: DesktopPetSettings
    let clearAction: () async throws -> Void

    @State private var selectedTheme: AppThemeMode
    @State private var selectedIcon: PetIconOption
    @State private var proactiveMinutes: Int
    @State private var showFinalDeleteConfirm = false
    @State private var isDeleting = false
    @State private var feedbackMessage: String?

    init(settings: DesktopPetSettings, clearAction: @escaping () async throws -> Void) {
        self._settings = ObservedObject(wrappedValue: settings)
        self.clearAction = clearAction
        self._selectedTheme = State(initialValue: settings.themeMode)
        self._selectedIcon = State(initialValue: settings.petIcon)
        self._proactiveMinutes = State(initialValue: settings.proactiveIntervalMinutes)
    }

    var body: some View {
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

            VStack(alignment: .leading, spacing: 8) {
                Text("Danger Zone")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                Text("Wipes all captured events, embeddings, graph edges, and bucket classifications from ~/.kb/")
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)
                Button(role: .destructive) {
                    showFinalDeleteConfirm = true
                } label: {
                    if isDeleting {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Text("Delete All Information")
                    }
                }
                .disabled(isDeleting)
            }

            if let feedbackMessage {
                Text(feedbackMessage)
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .alert("Delete everything?", isPresented: $showFinalDeleteConfirm) {
            Button("Cancel", role: .cancel) {}
            Button("Delete Everything", role: .destructive) {
                Task { await runDeleteAll() }
            }
        } message: {
            Text("This permanently removes all captured knowledge from your local store. Cannot be undone.")
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

    private func runDeleteAll() async {
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await clearAction()
            feedbackMessage = "All local information was deleted."
        } catch {
            feedbackMessage = "Failed to delete data. Ensure backend is running."
        }
    }
}
