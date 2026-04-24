import SwiftUI
import AppKit

// MARK: - Chat Window Controller
class ChatWindowController: NSWindowController {
    static var shared: ChatWindowController?

    static func open(near petWindow: NSWindow) {
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
        window.contentView = NSHostingView(rootView: ChatView(onClose: {
            shared?.window?.close()
            shared = nil
        }))

        let controller = ChatWindowController(window: window)
        shared = controller
        window.makeKeyAndOrderFront(nil)
    }
}

// MARK: - Chat View
struct ChatMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
}

struct ChatView: View {
    var onClose: () -> Void
    @State private var messages: [ChatMessage] = [
        ChatMessage(text: "hi, i'm text 👋 what's on your mind?", isUser: false)
    ]
    @State private var inputText: String = ""

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
        }
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespaces)
        guard !text.isEmpty else { return }
        inputText = ""
        messages.append(ChatMessage(text: text, isUser: true))
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            messages.append(ChatMessage(text: "i'm just text for now! 🦋", isUser: false))
        }
    }
}

// MARK: - Speech Bubble
struct SpeechBubble: View {
    let text: String
    var body: some View {
        VStack(spacing: 0) {
            Text(text)
                .font(.system(size: 11, weight: .medium, design: .rounded))
                .foregroundColor(Color(hex: "#3d2b1f"))
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color(hex: "#fff7fb"))
                        .shadow(color: .black.opacity(0.12), radius: 4, y: 2)
                )
            Triangle()
                .fill(Color(hex: "#fff7fb"))
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
    @State private var bobOffset: CGFloat = 0
    @State private var flapUp: Bool = false
    @State private var isHovered: Bool = false

    var body: some View {
        VStack(spacing: 2) {
            SpeechBubble(text: "hi, i'm text 🦋")

            PixelButterfly(flapUp: flapUp)
                .offset(y: bobOffset)
                .scaleEffect(isHovered ? 1.08 : 1.0)
                .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: bobOffset)
                .animation(.spring(response: 0.2), value: isHovered)
                .onHover { isHovered = $0 }
                .onTapGesture { openChat() }
                .help("Click to chat")
        }
        .padding(8)
        .onAppear {
            bobOffset = -3
            Timer.scheduledTimer(withTimeInterval: 0.35, repeats: true) { _ in
                withAnimation(.easeInOut(duration: 0.3)) { flapUp.toggle() }
            }
        }
    }

    func openChat() {
        guard let w = NSApp.windows.first(where: { $0.styleMask == .borderless }) else { return }
        ChatWindowController.open(near: w)
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

#Preview {
    PetView()
        .frame(width: 130, height: 150)
        .background(Color.gray.opacity(0.2))
}
