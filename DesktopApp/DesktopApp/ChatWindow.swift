import SwiftUI

struct ChatMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
}

struct ChatScreenView: View {
    @Binding var messages: [ChatMessage]
    let assistantTextColor: Color
    let assistantBubble: Color
    let sectionBackground: Color
    let chatHintBackground: Color
    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.system(size: 11))
                    .foregroundColor(Color(hex: "#ec4899"))
                Text("Tip: add files, URLs, or notes in Manual Inputs to improve responses.")
                    .font(.system(size: 11, design: .rounded))
                    .foregroundColor(.secondary)
                Spacer()
            }
            .padding(.horizontal, 14)
            .padding(.top, 10)

            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(messages) { msg in
                            HStack {
                                if msg.isUser { Spacer(minLength: 64) }
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(msg.isUser ? "You" : "Text")
                                        .font(.system(size: 10, weight: .medium, design: .rounded))
                                        .foregroundColor(.secondary)
                                    Text(msg.text)
                                        .font(.system(size: 13, design: .rounded))
                                        .foregroundColor(msg.isUser ? .white : assistantTextColor)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 8)
                                        .background(
                                            RoundedRectangle(cornerRadius: 14)
                                                .fill(msg.isUser ? Color(hex: "#ec4899") : assistantBubble)
                                                .shadow(color: .black.opacity(0.06), radius: 3, y: 1)
                                        )
                                }
                                if !msg.isUser { Spacer(minLength: 64) }
                            }
                            .id(msg.id)
                        }
                    }
                    .padding(14)
                }
                .background(sectionBackground)
                .onChange(of: messages.count) {
                    if let last = messages.last {
                        withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(chatHintBackground.opacity(0.35))
        )
        .padding(.horizontal, 14)
    }
}

