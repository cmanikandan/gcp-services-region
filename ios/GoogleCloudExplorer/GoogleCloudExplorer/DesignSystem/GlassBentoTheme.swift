import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

// MARK: - Gen Z "Neo-Bento Aura" Design System & Vibe Themes

public enum VibeTheme: String, Codable, CaseIterable, Identifiable, Sendable {
    case cyberMatcha = "cyberMatcha"
    case ultravioletPulse = "ultravioletPulse"
    case y2kChrome = "y2kChrome"
    case sunsetVapor = "sunsetVapor"

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .cyberMatcha: return "Cyber Matcha"
        case .ultravioletPulse: return "Ultraviolet"
        case .y2kChrome: return "Y2K Chrome"
        case .sunsetVapor: return "Sunset Vapor"
        }
    }

    public var emoji: String {
        switch self {
        case .cyberMatcha: return "🍵"
        case .ultravioletPulse: return "🔮"
        case .y2kChrome: return "💿"
        case .sunsetVapor: return "🌅"
        }
    }

    public var tagline: String {
        switch self {
        case .cyberMatcha: return "Acid matcha + electric cobalt"
        case .ultravioletPulse: return "Hyper violet + cyber pink"
        case .y2kChrome: return "Liquid sky + holo lavender"
        case .sunsetVapor: return "Solar coral + neon tangerine"
        }
    }

    public var primaryAccent: Color {
        switch self {
        case .cyberMatcha: return Color(red: 0.07, green: 0.80, blue: 0.49)      // #12CC7D
        case .ultravioletPulse: return Color(red: 0.62, green: 0.31, blue: 0.96) // #9E4FF5
        case .y2kChrome: return Color(red: 0.14, green: 0.63, blue: 0.98)        // #24A1FA
        case .sunsetVapor: return Color(red: 0.98, green: 0.35, blue: 0.44)      // #FA5970
        }
    }

    public var secondaryAccent: Color {
        switch self {
        case .cyberMatcha: return Color(red: 0.18, green: 0.50, blue: 0.97)
        case .ultravioletPulse: return Color(red: 0.96, green: 0.24, blue: 0.62)
        case .y2kChrome: return Color(red: 0.68, green: 0.42, blue: 0.98)
        case .sunsetVapor: return Color(red: 0.98, green: 0.62, blue: 0.12)
        }
    }

    public var heroGradientColors: [Color] {
        switch self {
        case .cyberMatcha:
            return [
                Color(red: 0.05, green: 0.22, blue: 0.20),
                Color(red: 0.06, green: 0.16, blue: 0.38),
                Color(red: 0.04, green: 0.08, blue: 0.18)
            ]
        case .ultravioletPulse:
            return [
                Color(red: 0.27, green: 0.09, blue: 0.48),
                Color(red: 0.42, green: 0.10, blue: 0.38),
                Color(red: 0.07, green: 0.06, blue: 0.19)
            ]
        case .y2kChrome:
            return [
                Color(red: 0.08, green: 0.28, blue: 0.58),
                Color(red: 0.24, green: 0.15, blue: 0.52),
                Color(red: 0.05, green: 0.10, blue: 0.24)
            ]
        case .sunsetVapor:
            return [
                Color(red: 0.48, green: 0.12, blue: 0.28),
                Color(red: 0.45, green: 0.22, blue: 0.10),
                Color(red: 0.09, green: 0.06, blue: 0.16)
            ]
        }
    }
}

public enum CloudPalette {
    public static let blue = Color(red: 0.16, green: 0.50, blue: 0.97)        // Electric Cobalt
    public static let deepSapphire = Color(red: 0.05, green: 0.11, blue: 0.26)
    public static let emerald = Color(red: 0.07, green: 0.78, blue: 0.47)     // Cyber Matcha Emerald
    public static let amber = Color(red: 0.96, green: 0.60, blue: 0.09)       // Solar Tangerine
    public static let coral = Color(red: 0.95, green: 0.28, blue: 0.36)       // Vapor Coral
    public static let violet = Color(red: 0.60, green: 0.32, blue: 0.96)      // Hyper Violet
    public static let cyan = Color(red: 0.06, green: 0.74, blue: 0.92)        // Holo Cyan
    public static let acidLime = Color(red: 0.71, green: 1.00, blue: 0.18)    // #B5FF2E
    public static let hotPink = Color(red: 0.96, green: 0.24, blue: 0.62)     // #F53D9E

    public static var canvasBackground: Color {
        #if canImport(UIKit)
        return Color(UIColor.systemGroupedBackground)
        #else
        return Color(nsColor: .windowBackgroundColor)
        #endif
    }

    public static var cardBackground: Color {
        #if canImport(UIKit)
        return Color(UIColor.secondarySystemGroupedBackground)
        #else
        return Color(nsColor: .controlBackgroundColor)
        #endif
    }

    public static var elevatedBackground: Color {
        #if canImport(UIKit)
        return Color(UIColor.tertiarySystemGroupedBackground)
        #else
        return Color(nsColor: .underPageBackgroundColor)
        #endif
    }
}

// MARK: - Tactile Gen Z Spring Button Style

public struct GenZBouncyButtonStyle: ButtonStyle {
    public init() {}

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.965 : 1.0)
            .opacity(configuration.isPressed ? 0.92 : 1.0)
            .animation(.spring(response: 0.26, dampingFraction: 0.68), value: configuration.isPressed)
    }
}

// MARK: - Neo-Bento Aura Card Container

public struct BentoCard<Content: View>: View {
    private let accent: Color?
    private let padding: CGFloat
    private let content: Content

    public init(
        accent: Color? = nil,
        padding: CGFloat = 16,
        @ViewBuilder content: () -> Content
    ) {
        self.accent = accent
        self.padding = padding
        self.content = content()
    }

    public var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 26, style: .continuous)
                    .fill(CloudPalette.cardBackground)
                    .overlay(
                        RoundedRectangle(cornerRadius: 26, style: .continuous)
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        (accent ?? Color.primary).opacity(accent == nil ? 0.11 : 0.38),
                                        (accent ?? CloudPalette.violet).opacity(accent == nil ? 0.04 : 0.12),
                                        Color.primary.opacity(0.05)
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: accent == nil ? 1.0 : 1.35
                            )
                    )
                    .shadow(
                        color: (accent ?? Color.black).opacity(accent == nil ? 0.05 : 0.10),
                        radius: 14,
                        x: 0,
                        y: 6
                    )
            )
    }
}

// MARK: - Semantic Neon Pill & Gen Z Sticker Badge

public struct SemanticPill: View {
    public let text: String
    public let tint: Color
    public var systemImage: String?

    public init(_ text: String, tint: Color = CloudPalette.blue, systemImage: String? = nil) {
        self.text = text
        self.tint = tint
        self.systemImage = systemImage
    }

    public var body: some View {
        HStack(spacing: 4) {
            if let systemImage {
                Image(systemName: systemImage)
                    .font(.system(size: 10, weight: .heavy))
            }
            Text(text)
                .font(.system(size: 11.5, weight: .bold, design: .rounded))
                .lineLimit(1)
        }
        .foregroundStyle(tint)
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(
            Capsule(style: .continuous)
                .fill(tint.opacity(0.14))
                .overlay(
                    Capsule(style: .continuous)
                        .strokeBorder(tint.opacity(0.24), lineWidth: 0.8)
                )
        )
    }
}

public struct StickerBadge: View {
    public let text: String
    public let background: Color
    public let foreground: Color

    public init(_ text: String, background: Color = CloudPalette.acidLime, foreground: Color = .black) {
        self.text = text
        self.background = background
        self.foreground = foreground
    }

    public var body: some View {
        Text(text.uppercased())
            .font(.system(size: 10, weight: .black, design: .rounded))
            .tracking(0.6)
            .foregroundStyle(foreground)
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(
                Capsule(style: .continuous)
                    .fill(background)
                    .shadow(color: background.opacity(0.35), radius: 6, x: 0, y: 2)
            )
    }
}

// MARK: - Top Toolbar Avatar / Auth Passport Pill

public struct AuthToolbarPillButton: View {
    public let handle: String?
    public let avatarEmoji: String
    public let isSynced: Bool
    public let accent: Color
    public let action: () -> Void

    public init(
        handle: String?,
        avatarEmoji: String = "⚡",
        isSynced: Bool = false,
        accent: Color = CloudPalette.violet,
        action: @escaping () -> Void
    ) {
        self.handle = handle
        self.avatarEmoji = avatarEmoji
        self.isSynced = isSynced
        self.accent = accent
        self.action = action
    }

    public var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if let handle {
                    Text(avatarEmoji)
                        .font(.system(size: 13))
                    Text("@\(handle)")
                        .font(.system(size: 12, weight: .bold, design: .rounded))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                    Circle()
                        .fill(isSynced ? CloudPalette.emerald : CloudPalette.amber)
                        .frame(width: 7, height: 7)
                } else {
                    Image(systemName: "sparkles")
                        .font(.system(size: 11, weight: .black))
                        .foregroundStyle(.white)
                    Text("Sign In")
                        .font(.system(size: 12, weight: .heavy, design: .rounded))
                        .foregroundStyle(.white)
                }
            }
            .padding(.horizontal, 11)
            .padding(.vertical, 6)
            .background(
                Group {
                    if handle != nil {
                        Capsule(style: .continuous)
                            .fill(.ultraThinMaterial)
                            .overlay(
                                Capsule(style: .continuous)
                                    .strokeBorder(accent.opacity(0.45), lineWidth: 1.2)
                            )
                    } else {
                        Capsule(style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [accent, CloudPalette.violet],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                    }
                }
            )
        }
        .buttonStyle(GenZBouncyButtonStyle())
        .accessibilityLabel(handle != nil ? "Open Builder Passport for \(handle!)" : "Sign In to Cloud Vault")
    }
}

// MARK: - Circular Coverage Ring Gauge

public struct RingGaugeView: View {
    public let progress: Double // 0.0 ... 1.0
    public let label: String
    public let tint: Color
    public var size: CGFloat = 46

    public init(progress: Double, label: String, tint: Color = CloudPalette.blue, size: CGFloat = 46) {
        self.progress = min(1.0, max(0.0, progress))
        self.label = label
        self.tint = tint
        self.size = size
    }

    public var body: some View {
        ZStack {
            Circle()
                .stroke(tint.opacity(0.16), lineWidth: 4.8)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(
                    AngularGradient(
                        colors: [tint, tint.opacity(0.75), tint],
                        center: .center
                    ),
                    style: StrokeStyle(lineWidth: 4.8, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
            Text(label)
                .font(.system(size: size * 0.24, weight: .heavy, design: .rounded))
                .foregroundStyle(.primary)
        }
        .frame(width: size, height: size)
    }
}

// MARK: - Unofficial Google Cloud Notice Banner

public struct UnofficialDisclaimerRow: View {
    public let syncState: DataSyncState
    public var onTapDetails: (() -> Void)?

    public init(syncState: DataSyncState, onTapDetails: (() -> Void)? = nil) {
        self.syncState = syncState
        self.onTapDetails = onTapDetails
    }

    public var body: some View {
        Button {
            onTapDetails?()
        } label: {
            HStack(spacing: 10) {
                Image(systemName: "checkmark.icloud.fill")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(CloudPalette.emerald)
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(syncState.badgeLabel)
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)
                        Text("• Unofficial Google Cloud Tool")
                            .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                            .foregroundStyle(.secondary)
                    }
                    Text("Independent companion app. Always verify SLAs & SKUs in official Google Cloud docs.")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                Spacer(minLength: 4)
                Image(systemName: "chevron.right")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(.tertiary)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 11)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .strokeBorder(Color.primary.opacity(0.09), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Gen Z "Stack Wrapped" Shareable Architecture Card (ImageRenderer Ready)

public struct ArchitectureShareCardView: View {
    public let title: String
    public let topology: StackTopologyMode
    public let slaResult: CompositeSLAResult
    public let serviceNames: [String]
    public let primaryRegion: String
    public let monthlySpendText: String
    public var vibeTheme: VibeTheme
    public var builderHandle: String?

    public init(
        title: String,
        topology: StackTopologyMode,
        slaResult: CompositeSLAResult,
        serviceNames: [String],
        primaryRegion: String,
        monthlySpendText: String,
        vibeTheme: VibeTheme = .cyberMatcha,
        builderHandle: String? = nil
    ) {
        self.title = title
        self.topology = topology
        self.slaResult = slaResult
        self.serviceNames = serviceNames
        self.primaryRegion = primaryRegion
        self.monthlySpendText = monthlySpendText
        self.vibeTheme = vibeTheme
        self.builderHandle = builderHandle
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                HStack(spacing: 6) {
                    Text(vibeTheme.emoji)
                    Text("GOOGLE CLOUD STACK WRAPPED")
                        .font(.system(size: 11, weight: .black, design: .rounded))
                        .tracking(0.8)
                        .foregroundStyle(.white.opacity(0.92))
                }
                Spacer()
                Text("UNOFFICIAL BRIEF")
                    .font(.system(size: 9.5, weight: .heavy, design: .rounded))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3.5)
                    .background(Capsule().fill(.white.opacity(0.18)))
                    .foregroundStyle(.white)
            }

            HStack(alignment: .firstTextBaseline) {
                Text(title)
                    .font(.system(size: 21, weight: .black, design: .rounded))
                    .foregroundStyle(.white)
                Spacer()
                if let builderHandle {
                    Text("@\(builderHandle)")
                        .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                        .foregroundStyle(CloudPalette.acidLime)
                }
            }

            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("COMPOSITE UPTIME")
                        .font(.system(size: 9.5, weight: .heavy))
                        .foregroundStyle(.white.opacity(0.72))
                    Text(slaResult.formattedUptime)
                        .font(.system(size: 30, weight: .black, design: .rounded))
                        .foregroundStyle(CloudPalette.acidLime)
                }
                Divider()
                    .frame(height: 36)
                    .overlay(.white.opacity(0.25))
                VStack(alignment: .leading, spacing: 2) {
                    Text("DOWNTIME BUDGET / MO")
                        .font(.system(size: 9.5, weight: .heavy))
                        .foregroundStyle(.white.opacity(0.72))
                    Text(slaResult.formattedMonthlyDowntime)
                        .font(.system(size: 18, weight: .bold, design: .monospaced))
                        .foregroundStyle(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text(primaryRegion.uppercased())
                        .font(.system(size: 10, weight: .heavy, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.75))
                    Text(monthlySpendText)
                        .font(.system(size: 17, weight: .heavy, design: .rounded))
                        .foregroundStyle(.white)
                }
            }

            Text("\(topology.shortLabel) • \(serviceNames.joined(separator: " → "))")
                .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                .foregroundStyle(.white.opacity(0.88))
                .lineLimit(2)
        }
        .padding(20)
        .frame(width: 420)
        .background(
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: vibeTheme.heroGradientColors,
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .strokeBorder(.white.opacity(0.22), lineWidth: 1.2)
                )
        )
    }
}
