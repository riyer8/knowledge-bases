import SwiftUI
import AppKit

// MARK: - Data model

struct ProactiveInsight: Codable, Identifiable {
    var id: String { type + title }
    let type: String
    let title: String
    let body: String
    let actionLabel: String
    let actionUrl: String
    let urgency: Int

    enum CodingKeys: String, CodingKey {
        case type, title, body, urgency
        case actionLabel = "action_label"
        case actionUrl = "action_url"
    }
}

private struct ProactiveResponse: Codable {
    let insights: [ProactiveInsight]
}

// MARK: - Window controller

final class ProactiveWindowController: NSWindowController, NSWindowDelegate {
    static var shared: ProactiveWindowController?

    static func show(near petWindow: NSWindow?) {
        shared?.window?.close()
        shared = nil

        let size = CGSize(width: 320, height: 200)
        let screen = NSScreen.main?.frame ?? .zero
        let origin = CGPoint(
            x: petWindow.map { $0.frame.midX - size.width / 2 } ?? (screen.midX - size.width / 2),
            y: petWindow.map { $0.frame.maxY + 12 } ?? (screen.midY)
        )

        let window = NSWindow(
            contentRect: NSRect(origin: origin, size: size),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = true
        window.level = .floating
        window.ignoresMouseEvents = false
        window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: ProactivePopupView {
            shared?.window?.close()
            shared = nil
        })

        let controller = ProactiveWindowController(window: window)
        window.delegate = controller
        shared = controller
        window.orderFrontRegardless()
        NSApp.activate(ignoringOtherApps: true)
    }

    func windowWillClose(_ notification: Notification) {
        Self.shared = nil
    }
}

// MARK: - Popup view

struct ProactivePopupView: View {
    let onDismiss: () -> Void
    @Environment(\.colorScheme) private var colorScheme
    @State private var insights: [ProactiveInsight] = []
    @State private var isLoading = true
    @State private var appeared = false
    @State private var flapUp = false
    @State private var currentIndex = 0

    private var isDark: Bool { colorScheme == .dark }
    private var bg: Color { isDark ? Color(nsColor: .windowBackgroundColor) : Color(hex: "#fff7fb") }
    private var titleColor: Color { isDark ? .primary : Color(hex: "#3d2b1f") }
    private var cardBg: Color { isDark ? Color(nsColor: .controlBackgroundColor) : Color(hex: "#fdf2f8") }

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 18)
                .fill(bg)
                .shadow(color: .black.opacity(0.18), radius: 16, y: 6)

            VStack(spacing: 0) {
                // Header row — butterfly + title + dismiss
                HStack(spacing: 10) {
                    PixelButterfly(flapUp: flapUp)
                        .scaleEffect(0.7)
                        .frame(width: 50, height: 38)

                    Text("What's up")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundColor(titleColor)

                    Spacer()

                    Button {
                        onDismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 16))
                            .foregroundColor(.secondary.opacity(0.6))
                    }
                    .buttonStyle(.plain)
                    .help("Dismiss (⌘⇧P)")
                }
                .padding(.horizontal, 14)
                .padding(.top, 12)
                .padding(.bottom, 8)

                Divider()

                // Content
                if isLoading {
                    HStack(spacing: 8) {
                        ProgressView().scaleEffect(0.7)
                        Text("Checking in on things...")
                            .font(.system(size: 12, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if insights.isEmpty {
                    VStack(spacing: 6) {
                        Text("✓")
                            .font(.system(size: 28))
                        Text("You're all caught up!")
                            .font(.system(size: 12, weight: .medium, design: .rounded))
                            .foregroundColor(titleColor)
                        Text("No pending items right now.")
                            .font(.system(size: 11, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    insightCard(insights[currentIndex])
                        .padding(.horizontal, 14)
                        .padding(.vertical, 10)
                }

                // Pagination dots + nav (when multiple insights)
                if insights.count > 1 {
                    HStack(spacing: 6) {
                        Button {
                            if currentIndex > 0 { currentIndex -= 1 }
                        } label: {
                            Image(systemName: "chevron.left")
                                .font(.system(size: 10, weight: .semibold))
                        }
                        .buttonStyle(.plain)
                        .disabled(currentIndex == 0)

                        ForEach(0..<insights.count, id: \.self) { i in
                            Circle()
                                .fill(i == currentIndex ? Color(hex: "#ec4899") : Color.secondary.opacity(0.3))
                                .frame(width: 5, height: 5)
                        }

                        Button {
                            if currentIndex < insights.count - 1 { currentIndex += 1 }
                        } label: {
                            Image(systemName: "chevron.right")
                                .font(.system(size: 10, weight: .semibold))
                        }
                        .buttonStyle(.plain)
                        .disabled(currentIndex == insights.count - 1)

                        Spacer()
                        Text("\(currentIndex + 1) of \(insights.count)")
                            .font(.system(size: 10, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal, 14)
                    .padding(.bottom, 10)
                }
            }
        }
        .scaleEffect(appeared ? 1 : 0.88)
        .opacity(appeared ? 1 : 0)
        .onAppear {
            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) { appeared = true }
            Timer.scheduledTimer(withTimeInterval: 0.35, repeats: true) { _ in
                withAnimation(.easeInOut(duration: 0.28)) { flapUp.toggle() }
            }
            Task { await fetchInsights() }
            // Auto-dismiss after 12 seconds
            DispatchQueue.main.asyncAfter(deadline: .now() + 12) { onDismiss() }
        }
    }

    @ViewBuilder
    private func insightCard(_ insight: ProactiveInsight) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: iconName(for: insight.type))
                    .font(.system(size: 11))
                    .foregroundColor(Color(hex: "#ec4899"))
                Text(insight.title)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundColor(titleColor)
                Spacer()
            }
            Text(insight.body)
                .font(.system(size: 11, design: .rounded))
                .foregroundColor(.secondary)
                .lineLimit(2)
                .fixedSize(horizontal: false, vertical: true)

            if !insight.actionLabel.isEmpty {
                Button {
                    handleAction(insight)
                } label: {
                    Text(insight.actionLabel)
                        .font(.system(size: 11, weight: .semibold, design: .rounded))
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 5)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color(hex: "#ec4899"))
                        )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12).fill(cardBg))
    }

    private func iconName(for type: String) -> String {
        switch type {
        case "meeting":    return "calendar.badge.clock"
        case "email":      return "envelope.badge"
        case "relationship": return "person.2"
        default:           return "sparkles"
        }
    }

    private func handleAction(_ insight: ProactiveInsight) {
        if !insight.actionUrl.isEmpty, let url = URL(string: insight.actionUrl) {
            NSWorkspace.shared.open(url)
        } else if insight.actionLabel == "Open Chat" {
            let petWindow = NSApp.windows.first { $0.styleMask == .borderless }
            if let w = petWindow { MainWindowController.open(near: w, preferredPanel: .chat) }
        }
        onDismiss()
    }

    private func fetchInsights() async {
        guard let url = URL(string: "http://127.0.0.1:8765/proactive") else { return }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            let response = try JSONDecoder().decode(ProactiveResponse.self, from: data)
            await MainActor.run {
                insights = response.insights
                isLoading = false
            }
        } catch {
            await MainActor.run { isLoading = false }
        }
    }
}
