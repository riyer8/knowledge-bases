import SwiftUI
import AppKit

class ManualInputsWindowController: NSWindowController, NSWindowDelegate {
    static var shared: ManualInputsWindowController?

    static func open(near sourceWindow: NSWindow) {
        if let existing = shared {
            if existing.window?.isVisible == true {
                existing.window?.makeKeyAndOrderFront(nil)
                return
            }
            shared = nil
        }

        let sourceFrame = sourceWindow.frame
        let size = CGSize(width: 560, height: 700)
        var origin = CGPoint(
            x: sourceFrame.midX - size.width / 2,
            y: sourceFrame.midY - size.height / 2
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
        window.title = "Manual Inputs"
        window.minSize = CGSize(width: 500, height: 620)
        window.isReleasedWhenClosed = false
        window.level = .floating
        window.contentView = NSHostingView(rootView: ManualInputsWindowView())

        let controller = ManualInputsWindowController(window: window)
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

struct ManualInputsWindowView: View {
    @Environment(\.colorScheme) private var colorScheme
    @StateObject private var manualInputStore = ManualInputStore()
    @State private var manualURLInput: String = ""
    @State private var manualTextInput: String = ""

    private var isDarkMode: Bool { colorScheme == .dark }
    private var windowBackground: Color { isDarkMode ? Color(nsColor: .windowBackgroundColor) : Color(hex: "#fff7fb") }
    private var headerBackground: Color { isDarkMode ? Color(nsColor: .controlBackgroundColor) : Color(hex: "#fdf2f8") }
    private var sectionBackground: Color { isDarkMode ? Color(nsColor: .underPageBackgroundColor) : Color(hex: "#fff7fb") }
    private var panelTitleColor: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Circle().fill(Color(hex: "#ec4899")).frame(width: 10, height: 10)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Manual Inputs")
                        .font(.system(size: 14, weight: .semibold, design: .rounded))
                        .foregroundColor(panelTitleColor)
                    Text("Add files, URLs, and notes for context")
                        .font(.system(size: 11, design: .rounded))
                        .foregroundColor(.secondary)
                }
                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(headerBackground)

            Divider()

            ManualInputsPanel(
                manualInputStore: manualInputStore,
                manualURLInput: $manualURLInput,
                manualTextInput: $manualTextInput,
                panelTitleColor: panelTitleColor,
                sectionBackground: sectionBackground
            )
        }
        .background(windowBackground)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .task { await manualInputStore.ensureInitialLoad() }
    }
}
