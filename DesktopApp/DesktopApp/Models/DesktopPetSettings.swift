import SwiftUI
import Combine

enum AppThemeMode: String, CaseIterable, Identifiable {
    case system
    case light
    case dark

    var id: String { rawValue }

    var label: String {
        switch self {
        case .system: return "System"
        case .light: return "Light"
        case .dark: return "Dark"
        }
    }
}

enum PetIconOption: String, CaseIterable, Identifiable {
    case butterfly
    case star
    case paw

    var id: String { rawValue }

    var label: String {
        switch self {
        case .butterfly: return "Butterfly"
        case .star: return "Star"
        case .paw: return "Paw"
        }
    }

    var symbolName: String {
        switch self {
        case .butterfly: return "sparkles"
        case .star: return "star.fill"
        case .paw: return "pawprint.fill"
        }
    }
}

@MainActor
final class DesktopPetSettings: ObservableObject {
    @Published var themeMode: AppThemeMode
    @Published var petIcon: PetIconOption
    @Published var proactiveIntervalMinutes: Int

    private static let themeKey = "desktopPet.themeMode"
    private static let iconKey = "desktopPet.iconOption"
    private static let proactiveKey = "desktopPet.proactiveIntervalMinutes"
    private var cancellables: Set<AnyCancellable> = []

    init() {
        let storedTheme = UserDefaults.standard.string(forKey: Self.themeKey) ?? AppThemeMode.system.rawValue
        let storedIcon = UserDefaults.standard.string(forKey: Self.iconKey) ?? PetIconOption.butterfly.rawValue
        let storedProactive = UserDefaults.standard.integer(forKey: Self.proactiveKey)
        self.themeMode = AppThemeMode(rawValue: storedTheme) ?? .system
        self.petIcon = PetIconOption(rawValue: storedIcon) ?? .butterfly
        self.proactiveIntervalMinutes = storedProactive > 0 ? storedProactive : 20
        bindPersistence()
    }

    var preferredColorScheme: ColorScheme? {
        switch themeMode {
        case .system:
            return nil
        case .light:
            return .light
        case .dark:
            return .dark
        }
    }

    private func bindPersistence() {
        $themeMode
            .dropFirst()
            .sink { value in
                UserDefaults.standard.set(value.rawValue, forKey: Self.themeKey)
            }
            .store(in: &cancellables)

        $petIcon
            .dropFirst()
            .sink { value in
                UserDefaults.standard.set(value.rawValue, forKey: Self.iconKey)
            }
            .store(in: &cancellables)

        $proactiveIntervalMinutes
            .dropFirst()
            .sink { value in
                let clamped = min(120, max(5, value))
                UserDefaults.standard.set(clamped, forKey: Self.proactiveKey)
            }
            .store(in: &cancellables)
    }
}
