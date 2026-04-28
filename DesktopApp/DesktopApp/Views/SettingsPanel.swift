import SwiftUI

struct SettingsPanel: View {
    @ObservedObject var settings: DesktopPetSettings
    let clearAction: () async throws -> Void

    @State private var showConfirmDelete = false
    @State private var showFinalDeleteConfirm = false
    @State private var isDeleting = false
    @State private var feedbackMessage: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Settings")
                .font(.system(size: 15, weight: .semibold, design: .rounded))

            VStack(alignment: .leading, spacing: 8) {
                Text("Theme")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                Picker("Theme", selection: $settings.themeMode) {
                    ForEach(AppThemeMode.allCases) { mode in
                        Text(mode.label).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Pet Icon")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                Picker("Pet Icon", selection: $settings.petIcon) {
                    ForEach(PetIconOption.allCases) { option in
                        Label(option.label, systemImage: option.symbolName).tag(option)
                    }
                }
                .pickerStyle(.segmented)
                Text("More icon styles can be added here later.")
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)
            }

            Divider()

            VStack(alignment: .leading, spacing: 8) {
                Text("Danger Zone")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                Text("Delete manual inputs, graph dependencies, and screenshots from local storage.")
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)
                Button(role: .destructive) {
                    showConfirmDelete = true
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
        .alert("Delete all information?", isPresented: $showConfirmDelete) {
            Button("Cancel", role: .cancel) {}
            Button("Continue", role: .destructive) {
                showFinalDeleteConfirm = true
            }
        } message: {
            Text("This removes local data for manual inputs and graph links.")
        }
        .alert("This cannot be undone", isPresented: $showFinalDeleteConfirm) {
            Button("Cancel", role: .cancel) {}
            Button("Delete Everything", role: .destructive) {
                Task { await runDeleteAll() }
            }
        } message: {
            Text("Please confirm one more time to permanently clear your data.")
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
