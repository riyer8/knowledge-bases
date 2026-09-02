import SwiftUI
import AppKit

// MARK: - Speech Bubble
struct SpeechBubble: View {
    let text: String
    @Environment(\.colorScheme) private var colorScheme
    private var isDarkMode: Bool { colorScheme == .dark }
    private var bubbleBackground: Color { isDarkMode ? Color(nsColor: .controlBackgroundColor) : Color(hex: "#fff7fb") }
    private var bubbleText: Color { isDarkMode ? .primary : Color(hex: "#3d2b1f") }
    var body: some View {
        VStack(spacing: 0) {
            Text(text)
                .font(.system(size: 11, weight: .medium, design: .rounded))
                .foregroundColor(bubbleText)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(bubbleBackground)
                        .shadow(color: .black.opacity(0.12), radius: 4, y: 2)
                )
            Triangle()
                .fill(bubbleBackground)
                .frame(width: 10, height: 6)
                .offset(y: -1)
        }
    }
}

struct Triangle: Shape {
    func path(in rect: CGRect) -> Path {
        Path { p in
            p.move(to: CGPoint(x: rect.midX, y: rect.maxY))
            p.addLine(to: CGPoint(x: rect.minX, y: rect.minY))
            p.addLine(to: CGPoint(x: rect.maxX, y: rect.minY))
            p.closeSubpath()
        }
    }
}

// MARK: - Pixel Butterfly (smaller, tighter)
struct PixelButterfly: View {
    var flapUp: Bool

    var body: some View {
        Canvas { ctx, size in
            let s: CGFloat = 4
            let cx = size.width / 2
            let cy: CGFloat = 8

            func px(_ col: CGFloat, _ row: CGFloat, _ color: Color) {
                ctx.fill(Path(CGRect(x: cx + col * s, y: cy + row * s, width: s, height: s)), with: .color(color))
            }

            let pink1  = Color(hex: "#f9a8d4")
            let pink2  = Color(hex: "#ec4899")
            let pink3  = Color(hex: "#db2777")
            let purp1  = Color(hex: "#c084fc")
            let purp2  = Color(hex: "#a855f7")
            let purp3  = Color(hex: "#9333ea")
            let grn1   = Color(hex: "#4ade80")
            let grn2   = Color(hex: "#22c55e")
            let grn3   = Color(hex: "#16a34a")
            let eyeCol = Color(hex: "#1e1b4b")
            let shine  = Color(hex: "#fdf2f8")

            let fy: CGFloat = flapUp ? -1 : 0

            // MARK: - Upper left wing (pulled inward)
            for (c,r,col): (CGFloat,CGFloat,Color) in [
                (-4,2,pink1),(-5,2,pink1),(-6,2,pink2),
                (-5,3,pink2),(-6,3,pink3),(-7,3,pink2),
                (-5,4,pink1),(-6,4,pink2),(-4,3,pink1),(-4,4,pink1)
            ] { px(c, r+fy, col) }
            px(-5.5, 2.5+fy, shine.opacity(0.7))

            // MARK: - Upper right wing (pulled inward)
            for (c,r,col): (CGFloat,CGFloat,Color) in [
                (3,2,pink1),(4,2,pink1),(5,2,pink2),
                (4,3,pink2),(5,3,pink3),(6,3,pink2),
                (4,4,pink1),(5,4,pink2),(3,3,pink1),(3,4,pink1)
            ] { px(c, r+fy, col) }
            px(4.5, 2.5+fy, shine.opacity(0.7))

            // MARK: - Lower left wing
            for (c,r,col): (CGFloat,CGFloat,Color) in [
                (-4,5,purp1),(-5,5,purp2),(-6,5,purp2),
                (-4,6,purp1),(-5,6,purp3),(-6,6,purp2),
                (-4,7,purp1),(-5,7,purp2)
            ] { px(c, r, col) }
            px(-5.5, 6, shine.opacity(0.5))

            // MARK: - Lower right wing
            for (c,r,col): (CGFloat,CGFloat,Color) in [
                (3,5,purp1),(4,5,purp2),(5,5,purp2),
                (3,6,purp1),(4,6,purp3),(5,6,purp2),
                (3,7,purp1),(4,7,purp2)
            ] { px(c, r, col) }
            px(4.5, 6, shine.opacity(0.5))

            // MARK: - Body
            for (c,r,col): (CGFloat,CGFloat,Color) in [
                (-1,1,grn1),(0,1,grn1),
                (-1,2,grn2),(0,2,grn2),
                (-1,3,grn3),(0,3,grn3),
                (-1,4,grn2),(0,4,grn2),
                (-1,5,grn2),(0,5,grn2),
                (-1,6,grn3),(0,6,grn3),
                (-1,7,grn2),(0,7,grn2),
                (-1,8,grn1),(0,8,grn1)
            ] { px(c, r, col) }

            // MARK: - Wing connectors (NEW — makes it feel attached)
            px(-2, 3, pink2)
            px(1, 3, pink2)

            // MARK: - Eyes
            px(-0.5, 1.5, eyeCol)
            px(0, 1.5, eyeCol)
            px(-0.5, 1.5, shine.opacity(0.6))

            // MARK: - Antennae
            for (c,r): (CGFloat,CGFloat) in [(-1,0),(-2,-0.5),(-3,-1)] { px(c,r,grn1) }
            px(-3.5, -1.5, grn2)
            for (c,r): (CGFloat,CGFloat) in [(1,0),(2,-0.5),(3,-1)] { px(c,r,grn1) }
            px(3.5, -1.5, grn2)
        }
        .frame(width: 84, height: 60)
    }
}

// MARK: - Main Pet View
struct PetView: View {
    @ObservedObject var settings: DesktopPetSettings
    @State private var bobOffset: CGFloat = 0
    @State private var flapUp: Bool = false
    @State private var isHovered: Bool = false
    @State private var showIntroBubble: Bool = true
    @State private var proactiveTimer: Timer?
    @State private var isCapturing: Bool = false

    private var hoverHint: String {
        isHovered ? "tap · chat\nlong press · what's up" : ""
    }

    var body: some View {
        ZStack(alignment: .top) {
            if showIntroBubble || isHovered {
                SpeechBubble(text: isHovered ? "tap · chat  ⌘⇧C\nlong press · what's up  ⌘⇧P" : "hi, i'm here 🦋")
                    .transition(.opacity)
                    .zIndex(1)
            }

            ZStack(alignment: .topTrailing) {
                PetAvatarView(icon: settings.petIcon, flapUp: flapUp, isHovered: isHovered)
                    .onHover { isHovered = $0 }
                    .gesture(
                        LongPressGesture(minimumDuration: 0.5)
                            .onEnded { _ in openProactive() }
                            .simultaneously(with:
                                TapGesture().onEnded { openChat() }
                            )
                    )
                    .help("Tap to chat · Long press for what's up (⌘⇧P)")

                if isCapturing {
                    Circle()
                        .fill(Color.red)
                        .frame(width: 10, height: 10)
                        .overlay(Circle().stroke(Color.white, lineWidth: 1.5))
                        .shadow(color: .red.opacity(0.6), radius: 4)
                        .transition(.scale.combined(with: .opacity))
                        .offset(x: 4, y: -4)
                }
            }
            .padding(.top, 38)
            .offset(y: bobOffset)
            .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: bobOffset)
        }
        .frame(width: 112, height: 112, alignment: .top)
        .padding(8)
        .onReceive(NotificationCenter.default.publisher(for: .siftCapturing)) { _ in
            withAnimation(.spring(response: 0.2, dampingFraction: 0.5)) { isCapturing = true }
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                withAnimation { isCapturing = false }
            }
        }
        .onAppear {
            bobOffset = -3
            showIntroBubble = true
            Timer.scheduledTimer(withTimeInterval: 0.35, repeats: true) { _ in
                withAnimation(.easeInOut(duration: 0.3)) { flapUp.toggle() }
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                withAnimation(.easeOut(duration: 0.2)) { showIntroBubble = false }
            }
            scheduleProactiveTimer()
        }
        .onChange(of: settings.proactiveIntervalMinutes) { _, _ in
            scheduleProactiveTimer()
        }
    }

    private func scheduleProactiveTimer() {
        proactiveTimer?.invalidate()
        let interval = TimeInterval(settings.proactiveIntervalMinutes * 60)
        proactiveTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { _ in
            autoCheckInsights()
        }
    }

    func openChat() {
        guard let w = NSApp.windows.first(where: { $0.styleMask == .borderless }) else { return }
        MainWindowController.open(near: w)
    }

    func openProactive() {
        guard let w = NSApp.windows.first(where: { $0.styleMask == .borderless }) else { return }
        ProactiveWindowController.show(near: w)
    }

    private func autoCheckInsights() {
        Task {
            guard let url = URL(string: "http://127.0.0.1:8765/proactive") else { return }
            guard let (data, _) = try? await URLSession.shared.data(from: url),
                  let json = try? JSONDecoder().decode([String: [ProactiveInsight]].self, from: data),
                  let insights = json["insights"],
                  !insights.isEmpty else { return }
            await MainActor.run {
                // Butterfly bounces to signal there's something to see
                withAnimation(.spring(response: 0.2, dampingFraction: 0.4).repeatCount(3)) {
                    bobOffset = -10
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { bobOffset = -3 }
            }
        }
    }
}

// MARK: - Color Helper
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xff) / 255
        let g = Double((int >> 8) & 0xff) / 255
        let b = Double(int & 0xff) / 255
        self.init(red: r, green: g, blue: b)
    }
}

#if DEBUG
#Preview {
    PetView(settings: DesktopPetSettings())
        .frame(width: 130, height: 150)
        .background(Color.gray.opacity(0.2))
}
#endif

private struct PetAvatarView: View {
    let icon: PetIconOption
    let flapUp: Bool
    let isHovered: Bool

    var body: some View {
        Group {
            switch icon {
            case .butterfly:
                PixelButterfly(flapUp: flapUp)
            case .star:
                Image(systemName: "star.fill")
                    .font(.system(size: 42))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(hex: "#f472b6"), Color(hex: "#ec4899"), Color(hex: "#c084fc")],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .shadow(color: .black.opacity(0.16), radius: 6, y: 2)
                    .frame(width: 84, height: 60)
            case .paw:
                Image(systemName: "pawprint.fill")
                    .font(.system(size: 40))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [Color(hex: "#22c55e"), Color(hex: "#16a34a")],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .shadow(color: .black.opacity(0.16), radius: 6, y: 2)
                    .frame(width: 84, height: 60)
            }
        }
        .scaleEffect(isHovered ? 1.08 : 1.0)
        .animation(.spring(response: 0.2), value: isHovered)
    }
}
