import SwiftUI

struct LibraryPanelView: View {
    @ObservedObject var libraryStore: LibraryStore
    let panelTitleColor: Color
    let sectionBackground: Color
    @State private var showQuotes = false
    @State private var editingTitle: String = ""

    var body: some View {
        HSplitView {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Label("Saved Pages", systemImage: "books.vertical")
                        .font(.system(size: 13, weight: .semibold, design: .rounded))
                        .foregroundColor(panelTitleColor)
                    Spacer()
                    Button {
                        Task { await libraryStore.refreshAll() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .buttonStyle(.borderless)
                    .help("Refresh library")
                }
                .padding(.horizontal, 12)
                .padding(.top, 10)

                Picker("View", selection: $showQuotes) {
                    Text("Pages").tag(false)
                    Text("Quotes").tag(true)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal, 12)

                if libraryStore.isLoading {
                    ProgressView("Loading library...")
                        .font(.system(size: 11, design: .rounded))
                        .padding()
                }

                List {
                    if showQuotes {
                        ForEach(libraryStore.quotes) { quote in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(quote.text)
                                    .font(.system(size: 12, design: .rounded))
                                    .lineLimit(3)
                                if let title = quote.pageTitle, !title.isEmpty {
                                    Text(title)
                                        .font(.system(size: 10, design: .rounded))
                                        .foregroundColor(.secondary)
                                        .lineLimit(1)
                                }
                            }
                            .padding(.vertical, 2)
                        }
                    } else {
                        ForEach(libraryStore.pages) { page in
                            Button {
                                Task { await libraryStore.loadPageDetail(pageId: page.id) }
                            } label: {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(page.title)
                                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                                        .foregroundColor(panelTitleColor)
                                        .lineLimit(2)
                                    Text(page.url)
                                        .font(.system(size: 10, design: .rounded))
                                        .foregroundColor(.secondary)
                                        .lineLimit(1)
                                }
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .listStyle(.plain)
            }
            .frame(minWidth: 180, idealWidth: 220, maxWidth: 280)

            VStack(alignment: .leading, spacing: 10) {
                if let page = libraryStore.selectedPage {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            TextField("Title", text: $editingTitle, onCommit: {
                                Task { await saveTitle(for: page.id) }
                            })
                            .font(.system(size: 14, weight: .semibold, design: .rounded))
                            .textFieldStyle(.plain)
                            if let url = URL(string: page.url) {
                                Link(page.url, destination: url)
                                    .font(.system(size: 10, design: .rounded))
                                    .lineLimit(1)
                            }
                        }
                        Spacer()
                        Button(role: .destructive) {
                            Task { _ = await libraryStore.deletePage(pageId: page.id) }
                        } label: {
                            Label("Delete", systemImage: "trash")
                                .font(.system(size: 11, design: .rounded))
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(.horizontal, 12)
                    .padding(.top, 10)

                    if let summary = page.summary, !summary.isEmpty {
                        Text(summary)
                            .font(.system(size: 12, design: .rounded))
                            .foregroundColor(.secondary)
                            .padding(.horizontal, 12)
                    }

                    if !page.quotes.isEmpty {
                        Text("Quotes")
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .foregroundColor(panelTitleColor)
                            .padding(.horizontal, 12)
                            .padding(.top, 4)

                        ScrollView {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(page.quotes) { quote in
                                    Text("\"\(quote.text)\"")
                                        .font(.system(size: 12, design: .rounded))
                                        .padding(10)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(
                                            RoundedRectangle(cornerRadius: 8)
                                                .fill(Color(hex: "#ec4899").opacity(0.08))
                                        )
                                }
                            }
                            .padding(.horizontal, 12)
                        }
                    }
                } else {
                    VStack(spacing: 8) {
                        Image(systemName: "book.closed")
                            .font(.system(size: 28))
                            .foregroundColor(Color(hex: "#ec4899").opacity(0.5))
                        Text("Select a saved page")
                            .font(.system(size: 13, design: .rounded))
                            .foregroundColor(.secondary)
                        Text("Pages saved in the Chrome extension appear here.")
                            .font(.system(size: 11, design: .rounded))
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 24)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .background(sectionBackground)
        }
        .background(sectionBackground)
        .task { await libraryStore.refreshAll() }
        .onChange(of: libraryStore.selectedPage?.id) { _, _ in
            editingTitle = libraryStore.selectedPage?.title ?? ""
        }
        .onAppear {
            editingTitle = libraryStore.selectedPage?.title ?? ""
        }
    }

    private func saveTitle(for pageId: String) async {
        let trimmed = editingTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        _ = await libraryStore.updateTitle(pageId: pageId, title: trimmed)
    }
}
