import SwiftUI

struct WikiPanelView: View {
    @ObservedObject var wikiStore: WikiStore
    let panelTitleColor: Color
    let sectionBackground: Color
    @State private var askText = ""

    var body: some View {
        HSplitView {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Label("Wiki", systemImage: "book.pages")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundColor(panelTitleColor)
                    Spacer()
                    Button {
                        Task { await wikiStore.refreshAll() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .buttonStyle(.borderless)
                }
                .padding(.horizontal, 12)
                .padding(.top, 10)

                if let status = wikiStore.status {
                    Text("\(status.rawCount) raw · \(status.articleCount) articles · \(status.uncompiledCount) pending")
                        .font(.system(size: 10, design: .rounded))
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 12)
                }

                HStack(spacing: 8) {
                    Button(wikiStore.isCompiling ? "Compiling…" : "Compile") {
                        Task { await wikiStore.compile() }
                    }
                    .disabled(wikiStore.isCompiling)

                    Link("Open in browser", destination: URL(string: "http://127.0.0.1:8765/app/")!)
                        .font(.system(size: 11, design: .rounded))
                }
                .padding(.horizontal, 12)

                if wikiStore.isLoading {
                    ProgressView()
                        .controlSize(.small)
                        .padding(.horizontal, 12)
                }

                List(wikiStore.articles) { article in
                    Button {
                        Task { await wikiStore.loadArticle(slug: article.slug) }
                    } label: {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(article.title)
                                .font(.system(size: 12, weight: .semibold, design: .rounded))
                                .foregroundColor(panelTitleColor)
                                .lineLimit(2)
                            if let excerpt = article.excerpt, !excerpt.isEmpty {
                                Text(excerpt)
                                    .font(.system(size: 10, design: .rounded))
                                    .foregroundColor(.secondary)
                                    .lineLimit(2)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
                .listStyle(.plain)
            }
            .frame(minWidth: 180, idealWidth: 220, maxWidth: 280)

            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    if let article = wikiStore.selectedArticle {
                        Text(article.title)
                            .font(.system(size: 15, weight: .semibold, design: .rounded))
                            .foregroundColor(panelTitleColor)
                        Text(article.content)
                            .font(.system(size: 12, design: .rounded))
                            .foregroundColor(.primary)
                            .textSelection(.enabled)
                    } else {
                        Text("Select an article")
                            .font(.system(size: 13, design: .rounded))
                            .foregroundColor(.secondary)
                    }

                    Divider()

                    Text("Ask wiki")
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                    TextField("Your question", text: $askText, axis: .vertical)
                        .textFieldStyle(.roundedBorder)
                        .lineLimit(2...4)
                    Button(wikiStore.isAsking ? "…" : "Ask") {
                        let q = askText
                        Task { await wikiStore.ask(question: q) }
                    }
                    .disabled(wikiStore.isAsking || askText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                    if let reply = wikiStore.askReply {
                        Text(reply)
                            .font(.system(size: 12, design: .rounded))
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(RoundedRectangle(cornerRadius: 8).fill(sectionBackground))
                            .textSelection(.enabled)
                    }

                    if let msg = wikiStore.statusMessage {
                        Text(msg)
                            .font(.system(size: 10, design: .rounded))
                            .foregroundColor(.secondary)
                    }
                }
                .padding(12)
            }
            .background(sectionBackground)
        }
        .background(sectionBackground)
        .task { await wikiStore.refreshAll() }
    }
}
