import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

// MARK: - Modern Apple Glass & Bento Design System

public enum CloudPalette {
    public static let blue = Color(red: 0.10, green: 0.45, blue: 0.91)       // #1A73E8
    public static let deepSapphire = Color(red: 0.06, green: 0.16, blue: 0.36)
    public static let emerald = Color(red: 0.08, green: 0.62, blue: 0.33)    // #149E54
    public static let amber = Color(red: 0.89, green: 0.54, blue: 0.04)      // #E38A0A
    public static let coral = Color(red: 0.85, green: 0.22, blue: 0.18)      // #D9382E
    public static let violet = Color(red: 0.52, green: 0.28, blue: 0.92)     // #8547EB
    public static let cyan = Color(red: 0.05, green: 0.65, blue: 0.82)

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

// MARK: - Bento Card Container

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
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(CloudPalette.cardBackground)
                    .overlay(
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        (accent ?? Color.primary).opacity(accent == nil ? 0.08 : 0.28),
                                        Color.primary.opacity(0.04)
                                    ],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                ),
                                lineWidth: 1
                            )
                    )
                    .shadow(color: Color.black.opacity(0.045), radius: 10, x: 0, y: 4)
            )
    }
}

// MARK: - Semantic Pill Badge

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
                    .font(.system(size: 10, weight: .bold))
            }
            Text(text)
                .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                .lineLimit(1)
        }
        .foregroundStyle(tint)
        .padding(.horizontal, 9)
        .padding(.vertical, 4.5)
        .background(
            Capsule(style: .continuous)
                .fill(tint.opacity(0.13))
        )
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
                .stroke(tint.opacity(0.15), lineWidth: 4.5)
            Circle()
                .trim(from: 0, to: progress)
                .stroke(
                    tint.gradient,
                    style: StrokeStyle(lineWidth: 4.5, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
            Text(label)
                .font(.system(size: size * 0.25, weight: .bold, design: .rounded))
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
                        Text("• Unofficial Tool")
                            .font(.system(size: 11.5, weight: .semibold))
                            .foregroundStyle(.secondary)
                    }
                    Text("Not affiliated with Google Cloud. Verify critical SLAs & SKUs in official docs.")
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
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                            .strokeBorder(Color.primary.opacity(0.08), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Shareable Architecture Summary Card (Rendered via ImageRenderer)

public struct ArchitectureShareCardView: View {
    public let title: String
    public let topology: StackTopologyMode
    public let slaResult: CompositeSLAResult
    public let serviceNames: [String]
    public let primaryRegion: String
    public let monthlySpendText: String

    public init(
        title: String,
        topology: StackTopologyMode,
        slaResult: CompositeSLAResult,
        serviceNames: [String],
        primaryRegion: String,
        monthlySpendText: String
    ) {
        self.title = title
        self.topology = topology
        self.slaResult = slaResult
        self.serviceNames = serviceNames
        self.primaryRegion = primaryRegion
        self.monthlySpendText = monthlySpendText
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label("Google Cloud Explorer", systemImage: "cloud.fill")
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(.white.opacity(0.92))
                Spacer()
                Text("UNOFFICIAL BRIEF")
                    .font(.system(size: 10, weight: .heavy, design: .rounded))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(.white.opacity(0.18)))
                    .foregroundStyle(.white)
            }

            Text(title)
                .font(.system(size: 20, weight: .bold, design: .rounded))
                .foregroundStyle(.white)

            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("COMPOSITE SLA")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.white.opacity(0.72))
                    Text(slaResult.formattedUptime)
                        .font(.system(size: 30, weight: .heavy, design: .rounded))
                        .foregroundStyle(Color(red: 0.45, green: 0.96, blue: 0.68))
                }
                Divider()
                    .frame(height: 36)
                    .overlay(.white.opacity(0.25))
                VStack(alignment: .leading, spacing: 2) {
                    Text("ERROR BUDGET / MO")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.white.opacity(0.72))
                    Text(slaResult.formattedMonthlyDowntime)
                        .font(.system(size: 19, weight: .bold, design: .monospaced))
                        .foregroundStyle(.white)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text(primaryRegion.uppercased())
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.white.opacity(0.72))
                    Text(monthlySpendText)
                        .font(.system(size: 17, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                }
            }

            Text("\(topology.rawValue) • \(serviceNames.joined(separator: " → "))")
                .font(.system(size: 11.5, weight: .medium))
                .foregroundStyle(.white.opacity(0.85))
                .lineLimit(2)
        }
        .padding(20)
        .frame(width: 420)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 0.07, green: 0.21, blue: 0.52),
                            Color(red: 0.04, green: 0.10, blue: 0.24)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        )
    }
}
