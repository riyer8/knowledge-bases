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

    private static let themeKey = "desktopPet.themeMode"
    private static let iconKey = "desktopPet.iconOption"
    private var cancellables: Set<AnyCancellable> = []

    init() {
        let storedTheme = UserDefaults.standard.string(forKey: Self.themeKey) ?? AppThemeMode.system.rawValue
        let storedIcon = UserDefaults.standard.string(forKey: Self.iconKey) ?? PetIconOption.butterfly.rawValue
        self.themeMode = AppThemeMode(rawValue: storedTheme) ?? .system
        self.petIcon = PetIconOption(rawValue: storedIcon) ?? .butterfly
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
    }
}
