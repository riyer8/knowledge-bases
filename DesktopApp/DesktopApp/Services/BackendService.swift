import Foundation

enum BackendLocator {
    private static let supportDirName = "Context"
    private static let repoPathFileName = "repo_path"

    /// Repository root containing `main.py` and `scripts/start_backend.sh`.
    static func repoRoot() -> URL? {
        if let env = ProcessInfo.processInfo.environment["CONTEXT_REPO_ROOT"],
           !env.isEmpty,
           FileManager.default.fileExists(atPath: URL(fileURLWithPath: env).appendingPathComponent("main.py").path) {
            return URL(fileURLWithPath: env, isDirectory: true)
        }

        if let configured = configuredRepoRoot(),
           FileManager.default.fileExists(atPath: configured.appendingPathComponent("main.py").path) {
            return configured
        }

        let candidates = [
            FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Documents/GitHub/knowledge-bases", isDirectory: true),
            FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Projects/knowledge-bases", isDirectory: true),
            FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("knowledge-bases", isDirectory: true),
        ]

        return candidates.first {
            FileManager.default.fileExists(atPath: $0.appendingPathComponent("main.py").path)
        }
    }

    static func configuredRepoRoot() -> URL? {
        let path = supportDirectory()
            .appendingPathComponent(repoPathFileName)
            .path
        guard let raw = try? String(contentsOfFile: path, encoding: .utf8) else {
            return nil
        }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(fileURLWithPath: trimmed, isDirectory: true)
    }

    static func supportDirectory() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return base.appendingPathComponent(supportDirName, isDirectory: true)
    }
}

enum BackendService {
    private static let port = 8765

    static func ensureRunning(completion: @escaping (Bool, String) -> Void) {
        if backendHealthy() {
            completion(true, "Backend already running.")
            return
        }

        guard let repo = BackendLocator.repoRoot() else {
            completion(false, "Backend not configured. Run: bash scripts/install_app.sh")
            return
        }

        let script = repo.appendingPathComponent("scripts/start_backend.sh")
        guard FileManager.default.isExecutableFile(atPath: script.path) else {
            completion(false, "Missing start script at \(script.path)")
            return
        }

        DispatchQueue.global(qos: .userInitiated).async {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/bin/bash")
            process.arguments = [script.path]
            var env = ProcessInfo.processInfo.environment
            env["PYTHON"] = env["PYTHON"] ?? "/usr/bin/python3"
            process.environment = env
            process.currentDirectoryURL = repo

            let pipe = Pipe()
            process.standardOutput = pipe
            process.standardError = pipe

            do {
                try process.run()
                process.waitUntilExit()
            } catch {
                DispatchQueue.main.async {
                    completion(false, "Could not start backend: \(error.localizedDescription)")
                }
                return
            }

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8) ?? ""

            for _ in 0..<20 {
                if backendHealthy() {
                    DispatchQueue.main.async {
                        completion(true, "Backend started.")
                    }
                    return
                }
                Thread.sleep(forTimeInterval: 0.25)
            }

            DispatchQueue.main.async {
                let detail = output.trimmingCharacters(in: .whitespacesAndNewlines)
                completion(false, detail.isEmpty ? "Backend did not respond on port \(port)." : detail)
            }
        }
    }

    private static func backendHealthy() -> Bool {
        guard let url = URL(string: "http://127.0.0.1:\(port)/health") else { return false }
        let semaphore = DispatchSemaphore(value: 0)
        var ok = false
        URLSession.shared.dataTask(with: url) { data, response, _ in
            defer { semaphore.signal() }
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode),
                  let data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return
            }
            ok = (json["api_version"] as? Int) == 2 || json["ok"] as? Bool == true
        }.resume()
        _ = semaphore.wait(timeout: .now() + 1.5)
        return ok
    }
}
