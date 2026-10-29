import SwiftUI
import Charts

// MARK: - Tab 4: Interactive SLA Architecture & Regional FinOps Studio

public struct PricingSLAStudioView: View {
    @Bindable var store: CatalogStore

    @State private var selectedSlugs: [String] = [
        "cloud-load-balancing",
        "cloud-run",
        "spanner"
    ]
    @State private var topologyMode: StackTopologyMode = .dualActiveActive
    @State private var showingAddServicePicker = false

    @State private var baselineMonthlySpend: Double = 15_000
    @State private var commitment: CommitmentTier = .cud1Year
    @State private var primaryRegionId: String = "us-central1"
    @State private var secondaryRegionId: String = "asia-south1"
    @State private var renderedShareImage: Image?

    public init(store: CatalogStore) {
        self.store = store
    }

    private var selectedServices: [CloudService] {
        selectedSlugs.compactMap { store.servicesBySlug[$0] }
    }

    private var slaResult: CompositeSLAResult {
        SLACalculator.evaluateCompositeSLA(services: selectedServices, topology: topologyMode)
    }

    private var primaryRegion: CloudRegion? {
        store.regionsById[primaryRegionId] ?? store.catalog.regions.first
    }

    private var secondaryRegion: CloudRegion? {
        store.regionsById[secondaryRegionId] ?? store.catalog.regions.dropFirst().first ?? store.catalog.regions.first
    }

    private var costComparison: RegionalCostComparison? {
        guard let r1 = primaryRegion, let r2 = secondaryRegion else { return nil }
        return SLACalculator.compareRegionalSpend(
            baselineMonthlyUSD: baselineMonthlySpend,
            primaryRegion: r1,
            secondaryRegion: r2,
            commitment: commitment
        )
    }

    private var benchmarkChartRegions: [CloudRegion] {
        let spotlightIds = ["us-central1", "us-east4", "europe-north1", "europe-west1", "asia-south1", "asia-northeast1", "southamerica-east1"]
        var picked = spotlightIds.compactMap { store.regionsById[$0] }
        if let p = primaryRegion, !picked.contains(where: { $0.regionId == p.regionId }) {
            picked.insert(p, at: 0)
        }
        if let s = secondaryRegion, !picked.contains(where: { $0.regionId == s.regionId }) {
            picked.append(s)
        }
        return picked
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    compositeSLASimulatorCard
                    regionalFinOpsScrubberCard
                    regionalBenchmarkChartCard
                    UnofficialDisclaimerRow(syncState: store.syncState)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("SLA & FinOps Studio")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    ShareLink(
                        item: shareSummaryText,
                        preview: SharePreview("Google Cloud Architecture SLA & FinOps Brief")
                    ) {
                        Label("Share Brief", systemImage: "square.and.arrow.up")
                    }
                }
            }
            .sheet(isPresented: $showingAddServicePicker) {
                AddStackServiceSheet(
                    services: store.catalog.services.filter { $0.sla.hasFormalSla },
                    selectedSlugs: $selectedSlugs
                )
                .presentationDetents([.medium, .large])
            }
        }
    }

    private var shareSummaryText: String {
        let names = selectedServices.map { "\($0.name) (\($0.sla.headlineDisplay))" }.joined(separator: " -> ")
        let costLine: String
        if let cmp = costComparison, let r1 = primaryRegion, let r2 = secondaryRegion {
            costLine = "\(r1.regionId): \(formatUSD(cmp.primaryMonthlyUSD))/mo vs \(r2.regionId): \(formatUSD(cmp.secondaryMonthlyUSD))/mo (\(commitment.rawValue))"
        } else {
            costLine = ""
        }
        return """
        Google Cloud Architecture SLA & FinOps Brief (Unofficial Tool)
        • Topology: \(topologyMode.rawValue)
        • Composite Workload SLA: \(slaResult.formattedUptime) (Max downtime: \(slaResult.formattedMonthlyDowntime)/mo)
        • Critical Path: \(names)
        • FinOps Estimate: \(costLine)
        """
    }

    // MARK: - 1. Composite Workload SLA Simulator

    private var compositeSLASimulatorCard: some View {
        BentoCard(accent: CloudPalette.emerald) {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Label("Composite Workload SLA Simulator", systemImage: "shield.lefthalf.filled.badge.checkmark")
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundStyle(CloudPalette.emerald)
                    Spacer()
                    Button {
                        showingAddServicePicker = true
                    } label: {
                        Label("Edit Stack", systemImage: "plus.circle.fill")
                            .font(.system(size: 12.5, weight: .bold))
                    }
                }

                Picker("Topology Pattern", selection: $topologyMode.animation(.snappy)) {
                    ForEach(StackTopologyMode.allCases) { topo in
                        Text(topo.shortLabel).tag(topo)
                    }
                }
                .pickerStyle(.segmented)
                .sensoryFeedback(.selection, trigger: topologyMode)

                // Live Rolling Readout Banner
                HStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text("COMPOSITE SLA")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.secondary)
                        Text(slaResult.formattedUptime)
                            .font(.system(size: 34, weight: .heavy, design: .rounded))
                            .foregroundStyle(CloudPalette.emerald)
                            .contentTransition(.numericText())
                    }
                    Divider().frame(height: 44)
                    VStack(alignment: .leading, spacing: 3) {
                        Text("MONTHLY BUDGET")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.secondary)
                        Text(slaResult.formattedMonthlyDowntime)
                            .font(.system(size: 20, weight: .bold, design: .monospaced))
                            .contentTransition(.numericText())
                        Text("\(slaResult.formattedAnnualDowntime) / year")
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(CloudPalette.emerald.opacity(0.09))
                )

                Text(topologyMode.formulaCaption)
                    .font(.system(size: 11.5, design: .monospaced))
                    .foregroundStyle(.secondary)

                // Active Stack Service Chips
                VStack(spacing: 8) {
                    ForEach(selectedServices) { svc in
                        HStack {
                            Image(systemName: "arrow.turn.down.right")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(.secondary)
                            Text(svc.name)
                                .font(.system(size: 13.5, weight: .semibold))
                            if slaResult.weakestServiceName == svc.name && selectedServices.count > 1 {
                                SemanticPill("Bottleneck", tint: CloudPalette.amber)
                            }
                            Spacer()
                            Text(svc.sla.headlineDisplay)
                                .font(.system(size: 12.5, weight: .bold, design: .monospaced))
                                .foregroundStyle(CloudPalette.emerald)
                            if selectedSlugs.count > 1 {
                                Button {
                                    withAnimation(.snappy) {
                                        selectedSlugs.removeAll { $0 == svc.slug }
                                    }
                                } label: {
                                    Image(systemName: "minus.circle.fill")
                                        .foregroundStyle(.secondary)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .fill(CloudPalette.elevatedBackground)
                        )
                    }
                }
            }
        }
    }

    // MARK: - 2. Regional FinOps Cost & CUD Scrubber

    private var regionalFinOpsScrubberCard: some View {
        BentoCard(accent: CloudPalette.blue) {
            VStack(alignment: .leading, spacing: 14) {
                Label("Regional FinOps Spend & CUD Scrubber", systemImage: "slider.horizontal.below.square.and.square.filled")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundStyle(CloudPalette.blue)

                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("BASELINE WORKLOAD SPEND")
                            .font(.system(size: 10.5, weight: .bold))
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text("\(formatUSD(baselineMonthlySpend)) / mo")
                            .font(.system(size: 16, weight: .heavy, design: .monospaced))
                            .foregroundStyle(CloudPalette.blue)
                            .contentTransition(.numericText())
                    }
                    Slider(value: $baselineMonthlySpend, in: 1_000...200_000, step: 1_000)
                        .tint(CloudPalette.blue)
                }

                Picker("Commitment Tier", selection: $commitment.animation(.snappy)) {
                    ForEach(CommitmentTier.allCases) { tier in
                        Text(tier.rawValue).tag(tier)
                    }
                }
                .pickerStyle(.segmented)
                .sensoryFeedback(.selection, trigger: commitment)

                HStack(spacing: 10) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("PRIMARY REGION")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.secondary)
                        Picker("Primary Region", selection: $primaryRegionId) {
                            ForEach(store.catalog.regions) { reg in
                                Text("\(reg.regionId) (\(String(format: "%.2fx", reg.pricing.relativeComputeIndex)))").tag(reg.regionId)
                            }
                        }
                        .labelsHidden()
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("TARGET / DR REGION")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(.secondary)
                        Picker("Target Region", selection: $secondaryRegionId) {
                            ForEach(store.catalog.regions) { reg in
                                Text("\(reg.regionId) (\(String(format: "%.2fx", reg.pricing.relativeComputeIndex)))").tag(reg.regionId)
                            }
                        }
                        .labelsHidden()
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                if let cmp = costComparison, let r1 = primaryRegion, let r2 = secondaryRegion {
                    HStack(spacing: 10) {
                        finOpsMetricBox(
                            label: r1.regionId,
                            value: formatUSD(cmp.primaryMonthlyUSD),
                            sub: String(format: "%.2fx Compute", r1.pricing.relativeComputeIndex),
                            tint: CloudPalette.blue
                        )
                        finOpsMetricBox(
                            label: r2.regionId,
                            value: formatUSD(cmp.secondaryMonthlyUSD),
                            sub: String(format: "%.2fx Compute", r2.pricing.relativeComputeIndex),
                            tint: .primary
                        )
                        finOpsMetricBox(
                            label: "ANNUAL DELTA",
                            value: (cmp.annualDeltaUSD >= 0 ? "+" : "−") + formatUSD(abs(cmp.annualDeltaUSD)),
                            sub: cmp.cudAnnualSavingsUSD > 0 ? "CUD saves \(formatUSD(cmp.cudAnnualSavingsUSD))/yr" : "On-Demand rate",
                            tint: cmp.annualDeltaUSD <= 0 ? CloudPalette.emerald : CloudPalette.amber
                        )
                    }
                }
            }
        }
    }

    private func finOpsMetricBox(label: String, value: String, sub: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label)
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundStyle(.secondary)
                .lineLimit(1)
            Text(value)
                .font(.system(size: 16, weight: .heavy, design: .rounded))
                .foregroundStyle(tint)
                .contentTransition(.numericText())
                .minimumScaleFactor(0.75)
                .lineLimit(1)
            Text(sub)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(CloudPalette.elevatedBackground)
        )
    }

    // MARK: - 3. Swift Charts Regional Multiplier Benchmark

    private var regionalBenchmarkChartCard: some View {
        BentoCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label("Global Region Spend Benchmark", systemImage: "chart.bar.fill")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                    Spacer()
                    Text("🌱 = Low CO₂")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(CloudPalette.emerald)
                }

                Chart(benchmarkChartRegions) { reg in
                    let estMonthly = baselineMonthlySpend * reg.pricing.relativeComputeIndex * commitment.discountMultiplier
                    BarMark(
                        x: .value("Monthly USD", estMonthly),
                        y: .value("Region", "\(reg.regionId)\(reg.isLowCo2 ? " 🌱" : "")")
                    )
                    .cornerRadius(6)
                    .foregroundStyle(
                        reg.regionId == primaryRegionId
                            ? CloudPalette.blue.gradient
                            : (reg.regionId == secondaryRegionId ? CloudPalette.amber.gradient : CloudPalette.emerald.opacity(0.65).gradient)
                    )
                    .annotation(position: .trailing) {
                        Text(formatUSD(estMonthly))
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                }
                .chartXAxis(.hidden)
                .frame(height: CGFloat(benchmarkChartRegions.count * 34))
            }
        }
    }

    private func formatUSD(_ amount: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: amount)) ?? "$\(Int(amount))"
    }
}

// MARK: - Stack Service Picker Sheet

private struct AddStackServiceSheet: View {
    let services: [CloudService]
    @Binding var selectedSlugs: [String]
    @State private var filterText: String = ""
    @Environment(\.dismiss) private var dismiss

    private var filtered: [CloudService] {
        guard !filterText.isEmpty else { return services }
        let q = filterText.lowercased()
        return services.filter { $0.name.lowercased().contains(q) || $0.category.lowercased().contains(q) }
    }

    var body: some View {
        NavigationStack {
            List(filtered) { svc in
                let isSelected = selectedSlugs.contains(svc.slug)
                Button {
                    if isSelected {
                        if selectedSlugs.count > 1 {
                            selectedSlugs.removeAll { $0 == svc.slug }
                        }
                    } else if selectedSlugs.count < 6 {
                        selectedSlugs.append(svc.slug)
                    }
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(svc.name)
                                .font(.system(size: 14.5, weight: .semibold))
                                .foregroundStyle(.primary)
                            Text("\(svc.category) • Max \(svc.sla.maxMonthlyDowntime)")
                                .font(.system(size: 11.5))
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        SemanticPill(svc.sla.headlineDisplay, tint: CloudPalette.emerald)
                        Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(isSelected ? CloudPalette.blue : .secondary)
                    }
                }
            }
            .searchable(text: $filterText, prompt: "Add service to SLA stack (max 6)…")
            .navigationTitle("Configure SLA Stack")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
