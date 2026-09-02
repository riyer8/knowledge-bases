import Combine
import Foundation

struct SavedPageSummary: Identifiable, Codable, Hashable {
    let id: String
    let title: String
    let url: String
    let summary: String?
    let savedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, title, url, summary
        case savedAt = "saved_at"
    }
}

struct SavedQuote: Identifiable, Codable, Hashable {
    let id: String
    let text: String
    let pageId: String?
    let pageUrl: String?
    let pageTitle: String?
    let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case id, text
        case pageId = "page_id"
        case pageUrl = "page_url"
        case pageTitle = "page_title"
        case createdAt = "created_at"
    }
}

struct SavedPageDetail: Codable {
    let id: String
    let title: String
    let url: String
    let summary: String?
    let quotes: [SavedQuote]
    let chatHistory: [[String: String]]?

    enum CodingKeys: String, CodingKey {
        case id, title, url, summary, quotes
        case chatHistory = "chat_history"
    }
}

@MainActor
final class LibraryStore: ObservableObject {
    @Published private(set) var pages: [SavedPageSummary] = []
    @Published private(set) var quotes: [SavedQuote] = []
    @Published var selectedPage: SavedPageDetail?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let baseURL = URL(string: "http://127.0.0.1:8765")!

    private struct PagesResponse: Codable {
        let pages: [SavedPageSummary]
    }

    private struct QuotesResponse: Codable {
        let quotes: [SavedQuote]
    }

    private struct PageResponse: Codable {
        let page: SavedPageDetail?
    }

    func refreshAll() async {
        isLoading = true
        defer { isLoading = false }
        await refreshPages()
        await refreshQuotes()
    }

    func refreshPages() async {
        do {
            let request = URLRequest(url: baseURL.appendingPathComponent("library/pages"))
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            let decoded = try JSONDecoder().decode(PagesResponse.self, from: data)
            pages = decoded.pages
            errorMessage = nil
        } catch {
            errorMessage = "Could not load saved pages. Is the backend running?"
        }
    }

    func refreshQuotes() async {
        do {
            let request = URLRequest(url: baseURL.appendingPathComponent("library/quotes"))
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            let decoded = try JSONDecoder().decode(QuotesResponse.self, from: data)
            quotes = decoded.quotes
            errorMessage = nil
        } catch {
            errorMessage = "Could not load quotes."
        }
    }

    func loadPageDetail(pageId: String) async {
        do {
            let request = URLRequest(url: baseURL.appendingPathComponent("library/pages/\(pageId)"))
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            selectedPage = try JSONDecoder().decode(PageResponse.self, from: data).page
            errorMessage = nil
        } catch {
            errorMessage = "Could not load page details."
            selectedPage = nil
        }
    }

    func deletePage(pageId: String) async -> Bool {
        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("library/pages/\(pageId)"))
            request.httpMethod = "DELETE"
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            if selectedPage?.id == pageId {
                selectedPage = nil
            }
            await refreshAll()
            return true
        } catch {
            errorMessage = "Could not delete page."
            return false
        }
    }

    func updateTitle(pageId: String, title: String) async -> Bool {
        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("library/pages/\(pageId)"))
            request.httpMethod = "PATCH"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            struct Body: Codable { let title: String }
            request.httpBody = try JSONEncoder().encode(Body(title: title))
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            struct PageResponse: Codable { let page: SavedPageDetail? }
            if let updated = try? JSONDecoder().decode(PageResponse.self, from: data).page {
                selectedPage = updated
            }
            await refreshPages()
            return true
        } catch {
            errorMessage = "Could not update title."
            return false
        }
    }
}
