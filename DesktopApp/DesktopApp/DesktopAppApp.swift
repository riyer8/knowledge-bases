import SwiftUI
import AppKit
import Foundation

@main
struct DesktopPetApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Settings { EmptyView() }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    private var keyMonitor: Any?
    private var globalKeyMonitor: Any?
    private var toastWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let size = CGSize(width: 130, height: 150)
        let screen = NSScreen.main!.frame
        let origin = CGPoint(
            x: screen.midX - size.width / 2,
            y: screen.minY + 80
        )

        window = NSWindow(
            contentRect: NSRect(origin: origin, size: size),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )

        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = false
        window.level = .floating
        window.ignoresMouseEvents = false
        window.isReleasedWhenClosed = false
        window.isMovableByWindowBackground = true   // ← enables click-and-drag anywhere
        window.collectionBehavior = [.canJoinAllSpaces, .stationary]

        window.contentView = NSHostingView(rootView: PetView())
        window.makeKeyAndOrderFront(nil)

        NSApp.setActivationPolicy(.accessory)
        registerHotkeys()
    }

    deinit {
        if let keyMonitor {
            NSEvent.removeMonitor(keyMonitor)
        }
        if let globalKeyMonitor {
            NSEvent.removeMonitor(globalKeyMonitor)
        }
    }

    private func registerHotkeys() {
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if self?.handleHotkey(event) == true {
                return nil
            }
            return event
        }

        globalKeyMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            _ = self?.handleHotkey(event)
        }
    }

    private func handleHotkey(_ event: NSEvent) -> Bool {
        guard event.modifierFlags.intersection(.deviceIndependentFlagsMask) == [.command, .shift] else {
            return false
        }
        guard let chars = event.charactersIgnoringModifiers?.lowercased() else {
            return false
        }

        switch chars {
        case "c":
            openChat(panel: .chat)
            return true
        case "g":
            openChat(panel: .graph)
            return true
        case "w":
            ChatWindowController.closeWindow()
            return true
        case "s":
            requestBackendScreenshot()
            return true
        default:
            return false
        }
    }

    private func openChat(panel: ChatView.ChatPanel) {
        guard let petWindow = window else { return }
        ChatWindowController.open(near: petWindow, preferredPanel: panel)
    }

    private func requestBackendScreenshot() {
        guard let url = URL(string: "http://127.0.0.1:8765/screenshot") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data("{}".utf8)

        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            if let error {
                self?.showToast("Screenshot failed: \(error.localizedDescription)")
                return
            }

            guard let http = response as? HTTPURLResponse else {
                self?.showToast("Screenshot failed: No response from backend.")
                return
            }

            guard (200...299).contains(http.statusCode) else {
                self?.showToast("Screenshot failed: Backend returned \(http.statusCode).")
                return
            }

            if let data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let shot = json["screenshot"] as? [String: Any],
               let filename = shot["filename"] as? String {
                self?.showToast("Screenshot saved: \(filename)")
            } else {
                self?.showToast("Screenshot captured.")
            }
        }.resume()
    }

    private func showToast(_ message: String) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.toastWindow?.close()

            let toastView = ToastView(message: message)
            let hosting = NSHostingView(rootView: toastView)

            let size = NSSize(width: 280, height: 44)
            let origin = CGPoint(
                x: self.window.frame.midX - size.width / 2,
                y: self.window.frame.maxY + 16
            )
            let toast = NSWindow(
                contentRect: NSRect(origin: origin, size: size),
                styleMask: [.borderless],
                backing: .buffered,
                defer: false
            )
            toast.isOpaque = false
            toast.backgroundColor = .clear
            toast.level = .floating
            toast.hasShadow = true
            toast.ignoresMouseEvents = true
            toast.contentView = hosting
            toast.orderFrontRegardless()
            self.toastWindow = toast

            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { [weak self] in
                self?.toastWindow?.close()
                self?.toastWindow = nil
            }
        }
    }
}

private struct ToastView: View {
    let message: String

    var body: some View {
        Text(message)
            .font(.system(size: 12, weight: .semibold, design: .rounded))
            .foregroundColor(.white)
            .lineLimit(2)
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(.horizontal, 12)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(Color.black.opacity(0.82))
            )
    }
}
