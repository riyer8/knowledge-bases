import Combine
import Foundation

struct BackendSettings: Codable {
    let envPath: String
    let envExists: Bool
    let kbRoot: String
    let backendPort: Int
    let llmProvider: String
    let llmProviderSetting: String
    let chatModel: String
    let embedProvider: String
    let embedModel: String
    let openaiModel: String
    let proactiveIntervalMinutes: Int
    let openaiConfigured: Bool
    let openaiKeyHint: String
    let anthropicConfigured: Bool
    let anthropicKeyHint: String
    let ollamaRequired: Bool
    let setupNotes: [String]

    enum CodingKeys: String, CodingKey {
        case envPath = "env_path"
        case envExists = "env_exists"
        case kbRoot = "kb_root"
        case backendPort = "backend_port"
        case llmProvider = "llm_provider"
        case llmProviderSetting = "llm_provider_setting"
        case chatModel = "chat_model"
        case embedProvider = "embed_provider"
        case embedModel = "embed_model"
        case openaiModel = "openai_model"
        case proactiveIntervalMinutes = "proactive_interval_minutes"
        case openaiConfigured = "openai_configured"
        case openaiKeyHint = "openai_key_hint"
        case anthropicConfigured = "anthropic_configured"
        case anthropicKeyHint = "anthropic_key_hint"
        case ollamaRequired = "ollama_required"
        case setupNotes = "setup_notes"
    }
}

struct BackendSettingsUpdate: Encodable {
    var llmProvider: String
    var openaiModel: String
    var chatModel: String
    var openaiApiKey: String?
    var anthropicApiKey: String?

    enum CodingKeys: String, CodingKey {
        case llmProvider = "llm_provider"
        case openaiModel = "openai_model"
        case chatModel = "chat_model"
        case openaiApiKey = "openai_api_key"
        case anthropicApiKey = "anthropic_api_key"
    }
}

@MainActor
final class BackendSettingsStore: ObservableObject {
    @Published private(set) var settings: BackendSettings?
    @Published private(set) var isLoading = false
    @Published private(set) var isSaving = false
    @Published var errorMessage: String?
    @Published var saveMessage: String?

    private let baseURL = URL(string: "http://127.0.0.1:8765")!

    private struct SettingsResponse: Codable {
        let ok: Bool?
        let settings: BackendSettings?
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            let (data, response) = try await URLSession.shared.data(from: baseURL.appendingPathComponent("settings"))
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                throw URLError(.badServerResponse)
            }
            settings = try JSONDecoder().decode(BackendSettings.self, from: data)
        } catch {
            errorMessage = "Could not load settings. Ensure the backend is running."
        }
    }

    func save(
        llmProvider: String,
        openaiModel: String,
        chatModel: String,
        openaiApiKey: String,
        anthropicApiKey: String
    ) async -> Bool {
        isSaving = true
        saveMessage = nil
        errorMessage = nil
        defer { isSaving = false }

        var payload = BackendSettingsUpdate(
            llmProvider: llmProvider,
            openaiModel: openaiModel,
            chatModel: chatModel
        )
        if !openaiApiKey.isEmpty {
            payload.openaiApiKey = openaiApiKey
        }
        if !anthropicApiKey.isEmpty {
            payload.anthropicApiKey = anthropicApiKey
        }

        do {
            var request = URLRequest(url: baseURL.appendingPathComponent("settings"))
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(payload)

            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                if let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let detail = body["error"] as? String {
                    errorMessage = detail
                } else {
                    errorMessage = "Failed to save settings."
                }
                return false
            }

            let decoded = try JSONDecoder().decode(SettingsResponse.self, from: data)
            settings = decoded.settings
            saveMessage = "Settings saved to .env"
            return true
        } catch {
            errorMessage = "Failed to save settings."
            return false
        }
    }
}
