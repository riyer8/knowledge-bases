import SwiftUI
import AppKit
import Foundation

final class PetWindow: NSWindow {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { true }
}

@main
struct ContextApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Settings { EmptyView() }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    private let settings = DesktopPetSettings()
    private var keyMonitor: Any?
    private var globalKeyMonitor: Any?
    private var toastWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        setupMainMenu()

        let size = CGSize(width: 130, height: 150)
        let screen = NSScreen.main!.frame
        let origin = CGPoint(
            x: screen.midX - size.width / 2,
            y: screen.minY + 80
        )

        window = PetWindow(
            contentRect: NSRect(origin: origin, size: size),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )

        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = false
        window.level = .normal
        window.ignoresMouseEvents = false
        window.isReleasedWhenClosed = false
        window.isMovableByWindowBackground = true
        window.collectionBehavior = []

        window.contentView = NSHostingView(rootView: PetView(settings: settings))
        window.makeKeyAndOrderFront(nil)
        MainWindowController.settings = settings

        NSApp.activate(ignoringOtherApps: true)
        registerHotkeys()
        startBackend()
    }

    private func startBackend() {
        BackendService.ensureRunning { [weak self] ok, message in
            if ok {
                return
            }
            self?.showToast(message)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }

    deinit {
        if let keyMonitor {
            NSEvent.removeMonitor(keyMonitor)
        }
        if let globalKeyMonitor {
            NSEvent.removeMonitor(globalKeyMonitor)
        }
    }

    private func setupMainMenu() {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)
        let appMenu = NSMenu(title: "Context")
        appMenuItem.submenu = appMenu

        let aboutItem = appMenu.addItem(withTitle: "About Context", action: #selector(showAbout), keyEquivalent: "")
        aboutItem.target = self
        appMenu.addItem(NSMenuItem.separator())
        let settingsItem = appMenu.addItem(withTitle: "Settings…", action: #selector(openSettings), keyEquivalent: ",")
        settingsItem.target = self
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Hide Context", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Quit Context", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")

        let windowMenuItem = NSMenuItem()
        mainMenu.addItem(windowMenuItem)
        let windowMenu = NSMenu(title: "Window")
        windowMenuItem.submenu = windowMenu
        let chatItem = windowMenu.addItem(withTitle: "Open Chat", action: #selector(openChatFromMenu), keyEquivalent: "")
        chatItem.target = self
        let graphItem = windowMenu.addItem(withTitle: "Open Graph", action: #selector(openGraphFromMenu), keyEquivalent: "")
        graphItem.target = self
        let companionItem = windowMenu.addItem(withTitle: "Show Companion", action: #selector(showCompanion), keyEquivalent: "")
        companionItem.target = self
        windowMenu.addItem(NSMenuItem.separator())
        let closeItem = windowMenu.addItem(withTitle: "Close Window", action: #selector(closeMainWindow), keyEquivalent: "")
        closeItem.target = self

        NSApp.mainMenu = mainMenu
        NSApp.windowsMenu = windowMenu
    }

    @objc private func showAbout() {
        NSApp.orderFrontStandardAboutPanel(options: [
            .applicationName: "Context",
            .applicationVersion: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0",
            .credits: NSAttributedString(string: "An AI that remembers what you've read."),
        ])
    }

    @objc private func openSettings() {
        openChat(panel: .settings)
    }

    @objc private func openChatFromMenu() {
        openChat(panel: .chat)
    }

    @objc private func openGraphFromMenu() {
        openChat(panel: .graph)
    }

    @objc private func showCompanion() {
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc private func closeMainWindow() {
        MainWindowController.closeWindow()
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
            MainWindowController.closeWindow()
            return true
        case "s":
            requestBackendScreenshot(flaggedImportant: false)
            return true
        case "i":
            requestBackendScreenshot(flaggedImportant: true)
            return true
        case "p":
            openProactiveBot()
            return true
        default:
            return false
        }
    }

    private func openChat(panel: MainPanel) {
        guard let petWindow = window else { return }
        MainWindowController.open(near: petWindow, preferredPanel: panel)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func openProactiveBot() {
        if ProactiveWindowController.shared?.window?.isVisible == true {
            ProactiveWindowController.shared?.window?.close()
            return
        }
        ProactiveWindowController.show(near: window)
    }

    private func requestBackendScreenshot(flaggedImportant: Bool = false) {
        guard let url = URL(string: "http://127.0.0.1:8765/screenshot") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        struct Body: Encodable { let flaggedImportant: Bool }
        request.httpBody = try? JSONEncoder().encode(Body(flaggedImportant: flaggedImportant))

        NotificationCenter.default.post(name: .siftCapturing, object: nil)
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

            let message = flaggedImportant
                ? "Important moment captured and flagged."
                : "Captured and added to your knowledge base."
            if let data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let _ = json["screenshot"] {
                self?.showToast(message)
            } else {
                self?.showToast(message)
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

extension Notification.Name {
    static let siftCapturing = Notification.Name("sift.capturing")
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
