import Combine
import Foundation

struct WikiArticleSummary: Identifiable, Codable, Hashable {
    let slug: String
    let title: String
    let excerpt: String?
    let updatedAt: String?

    var id: String { slug }

    enum CodingKeys: String, CodingKey {
        case slug, title, excerpt
        case updatedAt = "updated_at"
    }
}

struct WikiArticleDetail: Codable {
    let slug: String
    let title: String
    let content: String
}

struct WikiStatus: Codable {
    let rawCount: Int
    let articleCount: Int
    let uncompiledCount: Int

    enum CodingKeys: String, CodingKey {
        case rawCount = "raw_count"
        case articleCount = "article_count"
        case uncompiledCount = "uncompiled_count"
    }
}

@MainActor
final class WikiStore: ObservableObject {
    @Published private(set) var status: WikiStatus?
    @Published private(set) var articles: [WikiArticleSummary] = []
    @Published var selectedArticle: WikiArticleDetail?
    @Published var askReply: String?
    @Published var isLoading = false
    @Published var isCompiling = false
    @Published var isAsking = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?

    private let baseURL = URL(string: "http://127.0.0.1:8765")!

    func refreshAll() async {
        isLoading = true
        defer { isLoading = false }
        await refreshStatus()
        await refreshArticles()
    }

    func refreshStatus() async {
        do {
            let (data, response) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("wiki/status"))
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else { return }
            status = try JSONDecoder().decode(WikiStatus.self, from: data)
        } catch {
            errorMessage = "Wiki unavailable."
        }
    }

    func refreshArticles() async {
        do {
            let (data, response) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("wiki/articles"))
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else { return }
            struct Response: Codable { let articles: [WikiArticleSummary] }
            articles = try JSONDecoder().decode(Response.self, from: data).articles
        } catch {
            errorMessage = "Could not load articles."
        }
    }

    func loadArticle(slug: String) async {
        do {
            let url = baseURL.appendingPathComponent("wiki/articles/\(slug)")
            let (data, response) = try await URLSession.shared.data(from: url)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else { return }
            struct Response: Codable { let article: WikiArticleDetail }
            selectedArticle = try JSONDecoder().decode(Response.self, from: data).article
        } catch {
            errorMessage = "Could not load article."
        }
    }

    func compile() async {
        isCompiling = true
        defer { isCompiling = false }
        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("wiki/compile"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(["max_sources": 3])
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else { return }
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let message = json["message"] as? String {
                statusMessage = message
            }
            await refreshAll()
        } catch {
            errorMessage = "Compile failed."
        }
    }

    func ask(question: String) async {
        let q = question.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return }
        isAsking = true
        askReply = nil
        defer { isAsking = false }
        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("wiki/ask"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(["question": q])
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                errorMessage = "Ask failed."
                return
            }
            struct Response: Codable { let reply: String }
            askReply = try JSONDecoder().decode(Response.self, from: data).reply
        } catch {
            errorMessage = "Ask failed."
        }
    }
}
