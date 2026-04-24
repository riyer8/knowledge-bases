import SwiftUI

@main
struct DesktopPetApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Settings { EmptyView() }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!

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
    }
}
