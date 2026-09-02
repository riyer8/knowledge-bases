import Combine
import Foundation

struct BucketBreakdown: Codable, Identifiable, Hashable {
    var id: String { bucket }
    let bucket: String
    let count: Int
    let percent: Double
}

struct TopLevelCategory: Codable, Identifiable, Hashable {
    var id: String { category }
    let category: String
    let count: Int
    let percent: Double
}

struct TimeSummary: Codable {
    let days: Int
    let eventCount: Int
    let breakdown: [BucketBreakdown]
    let byTopLevel: [TopLevelCategory]

    enum CodingKeys: String, CodingKey {
        case days
        case eventCount = "event_count"
        case breakdown
        case byTopLevel = "by_top_level"
    }
}

struct RelationshipProfile: Identifiable, Codable, Hashable {
    var id: String { personHash }
    let personHash: String
    let displayName: String
    let eventCount: Int
    let notes: String
    let userEdited: Bool

    enum CodingKeys: String, CodingKey {
        case personHash = "person_hash"
        case displayName = "display_name"
        case eventCount = "event_count"
        case notes
        case userEdited = "user_edited"
    }
}

@MainActor
final class LifeStore: ObservableObject {
    @Published private(set) var summary: TimeSummary?
    @Published private(set) var profiles: [RelationshipProfile] = []
    @Published var selectedProfile: RelationshipProfile?
    @Published var editNotes: String = ""
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let baseURL = URL(string: "http://127.0.0.1:8765")!

    func refreshAll() async {
        isLoading = true
        defer { isLoading = false }
        await refreshSummary()
        await refreshProfiles()
    }

    func refreshSummary(days: Int = 7) async {
        do {
            var components = URLComponents(url: baseURL.appendingPathComponent("dashboard/time"), resolvingAgainstBaseURL: false)!
            components.queryItems = [URLQueryItem(name: "days", value: String(days))]
            let (data, response) = try await URLSession.shared.data(from: components.url!)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            summary = try JSONDecoder().decode(TimeSummary.self, from: data)
        } catch {
            errorMessage = "Could not load time summary."
        }
    }

    func refreshProfiles() async {
        do {
            struct Response: Codable { let profiles: [RelationshipProfile] }
            let (data, response) = try await URLSession.shared.data(
                from: baseURL.appendingPathComponent("relationships")
            )
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            profiles = try JSONDecoder().decode(Response.self, from: data).profiles
        } catch {
            errorMessage = "Could not load relationships."
        }
    }

    func saveNotes(for profile: RelationshipProfile) async {
        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("relationships/\(profile.personHash)"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            struct Body: Codable { let notes: String }
            request.httpBody = try JSONEncoder().encode(Body(notes: editNotes))
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            await refreshProfiles()
            selectedProfile = profiles.first { $0.personHash == profile.personHash }
        } catch {
            errorMessage = "Could not save notes."
        }
    }
}
