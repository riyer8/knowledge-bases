import Foundation

enum DataResetService {
    private static let baseURL = URL(string: "http://127.0.0.1:8765")!

    enum ResetError: Error {
        case badResponse
    }

    /// Clears saved pages, quotes, and per-page chats only.
    static func clearLibrary() async throws {
        try await post(path: "library/clear")
    }

    /// Wipes all runtime data under ~/.kb/ (events, memory, integrations, relationships).
    static func deleteAll() async throws {
        try await post(path: "delete-all")
    }

    private static func post(path: String) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data("{}".utf8)
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw ResetError.badResponse
        }
    }
}
