import Foundation

// MARK: - Deterministic SLA & Regional FinOps Calculation Engine

public enum CommitmentTier: String, CaseIterable, Identifiable, Sendable {
    case onDemand = "On-Demand"
    case cud1Year = "1Y CUD (-37%)"
    case cud3Year = "3Y CUD (-55%)"

    public var id: String { rawValue }

    public var discountMultiplier: Double {
        switch self {
        case .onDemand: return 1.00
        case .cud1Year: return 0.63
        case .cud3Year: return 0.45
        }
    }

    public var savingsLabel: String {
        switch self {
        case .onDemand: return "Pay-As-You-Go (0% Lock-in)"
        case .cud1Year: return "1-Year Committed Use (~37% Off Compute)"
        case .cud3Year: return "3-Year Committed Use (~55% Off Compute)"
        }
    }
}

public struct CompositeSLAResult: Sendable, Equatable {
    public let compositeUptimePct: Double
    public let formattedUptime: String
    public let maxMonthlyDowntimeSeconds: Double
    public let maxAnnualDowntimeSeconds: Double
    public let formattedMonthlyDowntime: String
    public let formattedAnnualDowntime: String
    public let weakestServiceName: String?
}

public struct RegionalCostComparison: Sendable, Equatable {
    public let primaryMonthlyUSD: Double
    public let secondaryMonthlyUSD: Double
    public let monthlyDeltaUSD: Double
    public let annualDeltaUSD: Double
    public let cudAnnualSavingsUSD: Double
}

public struct StackReadinessReport: Sendable, Equatable {
    public let regionId: String
    public let regionName: String
    public let availableCount: Int
    public let totalCount: Int
    public let missingServiceNames: [String]
    public var readinessRatio: Double {
        guard totalCount > 0 else { return 1.0 }
        return Double(availableCount) / Double(totalCount)
    }
}

public enum SLACalculator {
    public static let secondsPerMonth: Double = 43_830.0 * 60.0 // 365.25 / 12 days
    public static let secondsPerYear: Double = 365.25 * 86_400.0

    public static func evaluateCompositeSLA(
        services: [CloudService],
        topology: StackTopologyMode
    ) -> CompositeSLAResult {
        let valid = services.compactMap { svc -> (String, Double)? in
            guard let pct = svc.sla.headlineUptimePct, pct > 0 else { return nil }
            return (svc.name, min(pct, 100.0))
        }

        guard !valid.isEmpty else {
            return CompositeSLAResult(
                compositeUptimePct: 99.9,
                formattedUptime: "99.900%",
                maxMonthlyDowntimeSeconds: 2630,
                maxAnnualDowntimeSeconds: 31558,
                formattedMonthlyDowntime: "43m 50s",
                formattedAnnualDowntime: "8h 46m",
                weakestServiceName: nil
            )
        }

        let serialAvailability = valid.reduce(1.0) { acc, item in
            acc * (item.1 / 100.0)
        }

        let finalAvailability: Double
        switch topology {
        case .singleRegionSerial:
            finalAvailability = serialAvailability
        case .dualActiveActive:
            finalAvailability = 1.0 - pow(1.0 - serialAvailability, 2.0)
        case .triRegionQuorum:
            finalAvailability = 1.0 - pow(1.0 - serialAvailability, 3.0)
        }

        let clampedAvailability = min(0.999999, max(0.0, finalAvailability))
        let pct = clampedAvailability * 100.0
        let monthlyDown = (1.0 - clampedAvailability) * secondsPerMonth
        let annualDown = (1.0 - clampedAvailability) * secondsPerYear
        let weakest = valid.min(by: { $0.1 < $1.1 })?.0

        let decimals = pct >= 99.995 ? 4 : 3
        let formattedPct = String(format: "%.\(decimals)f%%", pct)

        return CompositeSLAResult(
            compositeUptimePct: pct,
            formattedUptime: formattedPct,
            maxMonthlyDowntimeSeconds: monthlyDown,
            maxAnnualDowntimeSeconds: annualDown,
            formattedMonthlyDowntime: formatDuration(seconds: monthlyDown),
            formattedAnnualDowntime: formatDuration(seconds: annualDown),
            weakestServiceName: weakest
        )
    }

    public static func compareRegionalSpend(
        baselineMonthlyUSD: Double,
        primaryRegion: CloudRegion,
        secondaryRegion: CloudRegion,
        commitment: CommitmentTier
    ) -> RegionalCostComparison {
        let onDemandPrimary = baselineMonthlyUSD * primaryRegion.pricing.relativeComputeIndex
        let primaryMonthly = onDemandPrimary * commitment.discountMultiplier
        let secondaryMonthly = baselineMonthlyUSD * secondaryRegion.pricing.relativeComputeIndex * commitment.discountMultiplier
        let delta = secondaryMonthly - primaryMonthly
        let cudAnnualSaved = (onDemandPrimary - primaryMonthly) * 12.0

        return RegionalCostComparison(
            primaryMonthlyUSD: primaryMonthly,
            secondaryMonthlyUSD: secondaryMonthly,
            monthlyDeltaUSD: delta,
            annualDeltaUSD: delta * 12.0,
            cudAnnualSavingsUSD: cudAnnualSaved
        )
    }

    public static func evaluateStackReadiness(
        stack: CustomerStack,
        servicesBySlug: [String: CloudService],
        regionsById: [String: CloudRegion]
    ) -> [StackReadinessReport] {
        let pickedServices = stack.serviceSlugs.compactMap { servicesBySlug[$0] }
        return stack.targetRegionIds.compactMap { rid in
            guard let region = regionsById[rid] else { return nil }
            let missing = pickedServices.filter { svc in
                !svc.isGlobal && !svc.regions.contains(rid)
            }.map(\.name)
            return StackReadinessReport(
                regionId: rid,
                regionName: region.regionName,
                availableCount: pickedServices.count - missing.count,
                totalCount: pickedServices.count,
                missingServiceNames: missing
            )
        }
    }

    public static func formatDuration(seconds: Double) -> String {
        if seconds < 1.0 {
            return String(format: "%.1fs", max(0.1, seconds))
        }
        let rounded = Int(seconds.rounded())
        if rounded < 60 {
            return "\(rounded)s"
        }
        let mins = rounded / 60
        let remSec = rounded % 60
        if mins < 60 {
            return remSec > 0 ? "\(mins)m \(remSec)s" : "\(mins)m"
        }
        let hours = mins / 60
        let remMin = mins % 60
        return remMin > 0 ? "\(hours)h \(remMin)m" : "\(hours)h"
    }

    /// Normalizes product queries so "Cloud Spanner", "Google Cloud Spanner", and "Spanner" match identically.
    public static func normalizeSearchToken(_ text: String) -> String {
        let lowered = text.lowercased()
        let cleaned = lowered.replacingOccurrences(
            of: "[^a-z0-9\\s-]",
            with: " ",
            options: .regularExpression
        )
        let stopWords: Set<String> = ["google", "cloud"]
        let tokens = cleaned
            .split(whereSeparator: \.isWhitespace)
            .map(String.init)
            .filter { !stopWords.contains($0) }
        return tokens.isEmpty ? lowered.trimmingCharacters(in: .whitespacesAndNewlines) : tokens.joined(separator: " ")
    }
}
