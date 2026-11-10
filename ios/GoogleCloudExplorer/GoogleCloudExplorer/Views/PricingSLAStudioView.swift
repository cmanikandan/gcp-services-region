import SwiftUI
import Charts

// MARK: - Tab 4: Interactive Gen Z SLA Architecture & Regional FinOps Studio

public struct PricingSLAStudioView: View {
    @Bindable var store: CatalogStore
    @Bindable var auth: AuthManager
    @Bindable var copilot: GeminiCopilotService
    public var onOpenAuthPortal: () -> Void

    @State private var selectedSlugs: [String] = [
        "cloud-load-balancing",
        "cloud-run",
        "spanner"
    ]
    @State private var topologyMode: StackTopologyMode = .dualActiveActive
    @State private var showingAddServicePicker = false
    @State private var savedStackBanner = false
    @State private var geminiAuditTurn: GeminiChatTurn?
    @State private var isAuditingWithGemini = false
    @State private var showingFullGeminiSheet = false

    @State private var baselineMonthlySpend: Double = 15_000
    @State private var commitment: CommitmentTier = .cud1Year
    @State private var primaryRegionId: String = "us-central1"
    @State private var secondaryRegionId: String = "asia-south1"

    public init(
        store: CatalogStore,
        auth: AuthManager,
        copilot: GeminiCopilotService,
        onOpenAuthPortal: @escaping () -> Void = {}
    ) {
        self.store = store
        self.auth = auth
        self.copilot = copilot
        self.onOpenAuthPortal = onOpenAuthPortal
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
                    geminiStackAuditCard
                    regionalFinOpsScrubberCard
                    stackWrappedPreviewSection
                    regionalBenchmarkChartCard
                    UnofficialDisclaimerRow(syncState: store.syncState)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("SLA & FinOps Studio")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    AuthToolbarPillButton(
                        handle: auth.currentUser?.handle,
                        avatarEmoji: auth.currentUser?.avatarEmoji ?? "⚡",
                        isSynced: auth.isVaultSyncedLive,
                        accent: store.vibeTheme.primaryAccent,
                        action: onOpenAuthPortal
                    )
                }
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
            .sheet(isPresented: $showingFullGeminiSheet) {
                GeminiCopilotSheetView(store: store, copilot: copilot)
                    .presentationDetents([.large])
                    .presentationDragIndicator(.visible)
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
        let author = auth.currentUser.map { " • Built by @\($0.handle)" } ?? ""
        return """
        Google Cloud Stack Wrapped ⚡ (Unofficial Tool\(author))
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
                    Label("Composite SLA Simulator", systemImage: "shield.lefthalf.filled.badge.checkmark")
                        .font(.system(size: 16, weight: .heavy, design: .rounded))
                        .foregroundStyle(CloudPalette.emerald)
                    Spacer()
                    Button {
                        showingAddServicePicker = true
                    } label: {
                        Label("Edit Stack", systemImage: "plus.circle.fill")
                            .font(.system(size: 12.5, weight: .bold, design: .rounded))
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
                            .font(.system(size: 10, weight: .heavy))
                            .foregroundStyle(.secondary)
                        Text(slaResult.formattedUptime)
                            .font(.system(size: 34, weight: .black, design: .rounded))
                            .foregroundStyle(CloudPalette.emerald)
                            .contentTransition(.numericText())
                    }
                    Divider().frame(height: 44)
                    VStack(alignment: .leading, spacing: 3) {
                        Text("MONTHLY BUDGET")
                            .font(.system(size: 10, weight: .heavy))
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
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .fill(CloudPalette.emerald.opacity(0.10))
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
                                .font(.system(size: 13.5, weight: .semibold, design: .rounded))
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

                // Save Custom Stack to Cloud Vault Button
                Button {
                    saveCurrentStackToVault()
                } label: {
                    HStack {
                        Image(systemName: savedStackBanner ? "checkmark.seal.fill" : "icloud.and.arrow.up.fill")
                        Text(savedStackBanner ? "Saved to Cloud Vault ✓ (+65 XP)" : "Save Stack to Cloud Vault ⚡")
                            .font(.system(size: 13.5, weight: .heavy, design: .rounded))
                        Spacer()
                        Text(auth.currentUser != nil ? "@\(auth.currentUser!.handle)" : "Local + Sync")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .opacity(0.85)
                    }
                    .foregroundStyle(.white)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 11)
                    .background(
                        RoundedRectangle(cornerRadius: 15, style: .continuous)
                            .fill(savedStackBanner ? CloudPalette.emerald : store.vibeTheme.primaryAccent)
                    )
                }
                .buttonStyle(GenZBouncyButtonStyle())
                .sensoryFeedback(.success, trigger: savedStackBanner)
            }
        }
    }

    private func saveCurrentStackToVault() {
        let topNames = selectedServices.prefix(3).map(\.name).joined(separator: " + ")
        let newStack = CustomerStack(
            name: "\(topologyMode.shortLabel) • \(primaryRegionId)",
            subtitle: "\(slaResult.formattedUptime) Composite • \(topNames)",
            serviceSlugs: selectedSlugs,
            targetRegionIds: Array(Set([primaryRegionId, secondaryRegionId])).sorted(),
            topologyMode: topologyMode
        )
        store.addCustomerStack(newStack)
        withAnimation(.snappy) {
            savedStackBanner = true
        }
        Task {
            try? await Task.sleep(for: .seconds(2.2))
            withAnimation(.snappy) {
                savedStackBanner = false
            }
        }
    }

    // MARK: - 1b. Gemini 3.8 Live Stack & FinOps Audit Card

    private var geminiStackAuditCard: some View {
        BentoCard(accent: CloudPalette.violet) {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label("Gemini 3.8 Architecture & SLA Audit", systemImage: "sparkles")
                        .font(.system(size: 15.5, weight: .heavy, design: .rounded))
                        .foregroundStyle(CloudPalette.violet)
                    Spacer()
                    Button {
                        showingFullGeminiSheet = true
                    } label: {
                        Text("Full Chat →")
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(CloudPalette.violet)
                    }
                }

                Text("Audit your active \(topologyMode.shortLabel) stack (\(slaResult.formattedUptime) composite uptime across \(primaryRegionId) & \(secondaryRegionId)) with Gemini.")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)

                Button {
                    Task {
                        isAuditingWithGemini = true
                        let turn = await copilot.auditArchitectureStack(
                            services: selectedServices,
                            topology: topologyMode,
                            slaResult: slaResult,
                            primaryRegion: primaryRegion,
                            secondaryRegion: secondaryRegion,
                            monthlySpendUSD: baselineMonthlySpend,
                            commitment: commitment,
                            store: store
                        )
                        withAnimation(.snappy) {
                            geminiAuditTurn = turn
                            isAuditingWithGemini = false
                        }
                    }
                } label: {
                    HStack {
                        if isAuditingWithGemini {
                            ProgressView().tint(.white)
                        } else {
                            Image(systemName: "wand.and.stars")
                        }
                        Text(isAuditingWithGemini ? "Auditing Stack with Gemini 3.8…" : "Audit Active Stack with Gemini ✨")
                            .font(.system(size: 13.5, weight: .heavy, design: .rounded))
                        Spacer()
                        Text(copilot.selectedModel.rawValue)
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                            .opacity(0.88)
                    }
                    .foregroundStyle(.white)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 11)
                    .background(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [CloudPalette.violet, store.vibeTheme.primaryAccent],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                    )
                }
                .buttonStyle(GenZBouncyButtonStyle())
                .disabled(isAuditingWithGemini)

                if let turn = geminiAuditTurn {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            SemanticPill(turn.modelId ?? "gemini-3.8-flash", tint: CloudPalette.violet)
                            if let tok = turn.totalTokens {
                                SemanticPill("\(tok) tokens", tint: CloudPalette.emerald)
                            }
                            Spacer()
                        }
                        Text(LocalizedStringKey(turn.text))
                            .font(.system(size: 13, design: .rounded))
                            .foregroundStyle(.primary)
                            .textSelection(.enabled)
                    }
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(CloudPalette.elevatedBackground)
                    )
                }
            }
        }
    }

    // MARK: - 2. Regional FinOps Cost & CUD Scrubber

    private var regionalFinOpsScrubberCard: some View {
        BentoCard(accent: store.vibeTheme.primaryAccent) {
            VStack(alignment: .leading, spacing: 14) {
                Label("Regional FinOps & CUD Scrubber", systemImage: "slider.horizontal.below.square.and.square.filled")
                    .font(.system(size: 16, weight: .heavy, design: .rounded))
                    .foregroundStyle(store.vibeTheme.primaryAccent)

                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("BASELINE WORKLOAD SPEND")
                            .font(.system(size: 10.5, weight: .heavy))
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text("\(formatUSD(baselineMonthlySpend)) / mo")
                            .font(.system(size: 17, weight: .black, design: .monospaced))
                            .foregroundStyle(store.vibeTheme.primaryAccent)
                            .contentTransition(.numericText())
                    }
                    Slider(value: $baselineMonthlySpend, in: 1_000...200_000, step: 1_000)
                        .tint(store.vibeTheme.primaryAccent)
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
                            tint: store.vibeTheme.primaryAccent
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
                .font(.system(size: 16, weight: .black, design: .rounded))
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

    // MARK: - 3. Live "Google Cloud Stack Wrapped" Card Preview

    private var stackWrappedPreviewSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("SHAREABLE STACK WRAPPED CARD ✨")
                .font(.system(size: 11, weight: .black, design: .rounded))
                .foregroundStyle(.secondary)

            ScrollView(.horizontal, showsIndicators: false) {
                ArchitectureShareCardView(
                    title: "\(topologyMode.shortLabel) Production Stack",
                    topology: topologyMode,
                    slaResult: slaResult,
                    serviceNames: selectedServices.map(\.name),
                    primaryRegion: primaryRegionId,
                    monthlySpendText: "\(formatUSD(costComparison?.primaryMonthlyUSD ?? baselineMonthlySpend))/mo",
                    vibeTheme: store.vibeTheme,
                    builderHandle: auth.currentUser?.handle
                )
            }
        }
    }

    // MARK: - 4. Swift Charts Regional Multiplier Benchmark

    private var regionalBenchmarkChartCard: some View {
        BentoCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label("Global Region Spend Benchmark", systemImage: "chart.bar.fill")
                        .font(.system(size: 15, weight: .heavy, design: .rounded))
                    Spacer()
                    Text("🌱 = Low CO₂")
                        .font(.system(size: 11, weight: .bold))
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
                            ? store.vibeTheme.primaryAccent.gradient
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
                                .font(.system(size: 14.5, weight: .semibold, design: .rounded))
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
