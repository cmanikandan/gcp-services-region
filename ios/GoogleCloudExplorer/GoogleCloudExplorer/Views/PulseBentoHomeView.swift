import SwiftUI
import Charts

// MARK: - Tab 1: Pulse Bento Intelligence Hub

public struct PulseBentoHomeView: View {
    @Bindable var store: CatalogStore
    @Binding var selectedTab: ExplorerSection
    @State private var omniQuery: String = ""
    @State private var selectedRegionSheet: CloudRegion?
    @State private var selectedStackSheet: CustomerStack?
    @State private var showingSyncSheet = false

    public init(store: CatalogStore, selectedTab: Binding<ExplorerSection>) {
        self.store = store
        self._selectedTab = selectedTab
    }

    private struct SLABucket: Identifiable {
        let id = UUID()
        let label: String
        let count: Int
        let tint: Color
    }

    private var slaDistribution: [SLABucket] {
        var five9 = 0, four9 = 0, three5 = 0, three9 = 0
        for svc in store.catalog.services {
            guard let pct = svc.sla.headlineUptimePct else { continue }
            if pct >= 99.999 { five9 += 1 }
            else if pct >= 99.99 { four9 += 1 }
            else if pct >= 99.95 { three5 += 1 }
            else { three9 += 1 }
        }
        return [
            SLABucket(label: "≥99.999%", count: max(1, five9), tint: CloudPalette.emerald),
            SLABucket(label: "99.99%", count: max(1, four9), tint: CloudPalette.blue),
            SLABucket(label: "99.95%", count: max(1, three5), tint: CloudPalette.violet),
            SLABucket(label: "99.9%", count: max(1, three9), tint: CloudPalette.cyan)
        ]
    }

    private struct CostTierBucket: Identifiable {
        let id = UUID()
        let tier: String
        let count: Int
        let tint: Color
    }

    private var costTierBuckets: [CostTierBucket] {
        var t1 = 0, t2 = 0, t3 = 0
        for r in store.catalog.regions {
            let idx = r.pricing.relativeComputeIndex
            if idx <= 1.03 { t1 += 1 }
            else if idx <= 1.15 { t2 += 1 }
            else { t3 += 1 }
        }
        return [
            CostTierBucket(tier: "1.00x Base", count: t1, tint: CloudPalette.emerald),
            CostTierBucket(tier: "1.04–1.15x", count: t2, tint: CloudPalette.blue),
            CostTierBucket(tier: "1.16x+ Prem", count: t3, tint: CloudPalette.amber)
        ]
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    heroHeaderCard

                    if !omniQuery.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        omniSearchResultsSection
                    } else {
                        bentoTelemetryGrid
                        swiftChartsRow
                        customerStacksSection
                        releasePulseCarousel
                    }

                    UnofficialDisclaimerRow(syncState: store.syncState) {
                        showingSyncSheet = true
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("Google Cloud Explorer")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .refreshable {
                await store.refreshFromServer(silent: false)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingSyncSheet = true
                    } label: {
                        Image(systemName: "icloud.and.arrow.down")
                    }
                    .accessibilityLabel("Offline Sync & Settings")
                }
            }
            .sheet(item: $selectedRegionSheet) { reg in
                RegionInspectorSheetView(store: store, region: reg)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
            .sheet(item: $selectedStackSheet) { stack in
                CustomerStackInspectorSheet(store: store, stack: stack)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
            .sheet(isPresented: $showingSyncSheet) {
                OfflineSyncSettingsSheet(store: store)
            }
        }
    }

    // MARK: - Sapphire Hero Header + Instant Omni-Search

    private var heroHeaderCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 3) {
                    HStack(spacing: 6) {
                        Image(systemName: "cloud.fill")
                            .foregroundStyle(.cyan)
                        Text("GOOGLE CLOUD INTELLIGENCE")
                            .font(.system(size: 11, weight: .heavy, design: .rounded))
                            .tracking(0.8)
                            .foregroundStyle(.white.opacity(0.82))
                    }
                    Text("Architecture, SLAs & Regional FinOps")
                        .font(.system(size: 22, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                }
                Spacer()
                Text("Unofficial")
                    .font(.system(size: 10.5, weight: .bold, design: .rounded))
                    .foregroundStyle(.white.opacity(0.9))
                    .padding(.horizontal, 9)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(.white.opacity(0.16)))
            }

            // Frosted Omni-Search Bar
            HStack(spacing: 10) {
                Image(systemName: "sparkle.magnifyingglass")
                    .foregroundStyle(.white.opacity(0.85))
                TextField("Ask: 'Spanner SLA', 'Mumbai cost', 'Claude', 'H100'…", text: $omniQuery)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.white)
                    .tint(.cyan)
                if !omniQuery.isEmpty {
                    Button {
                        omniQuery = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.white.opacity(0.75))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 13)
            .padding(.vertical, 11)
            .background(
                RoundedRectangle(cornerRadius: 15, style: .continuous)
                    .fill(.white.opacity(0.15))
                    .overlay(
                        RoundedRectangle(cornerRadius: 15, style: .continuous)
                            .strokeBorder(.white.opacity(0.22), lineWidth: 1)
                    )
            )

            // Quick Prompt Chips
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(["Spanner SLA", "asia-south1", "Vertex AI", "99.999%", "Claude"], id: \.self) { chip in
                        Button {
                            omniQuery = chip
                        } label: {
                            Text(chip)
                                .font(.system(size: 11.5, weight: .semibold, design: .rounded))
                                .foregroundStyle(.white.opacity(0.92))
                                .padding(.horizontal, 10)
                                .padding(.vertical, 5)
                                .background(Capsule().fill(.white.opacity(0.13)))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 26, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: [
                            Color(red: 0.08, green: 0.25, blue: 0.62),
                            Color(red: 0.04, green: 0.12, blue: 0.30)
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .shadow(color: CloudPalette.blue.opacity(0.24), radius: 14, x: 0, y: 6)
        )
    }

    // MARK: - Live Omni-Search Answer Cards

    private var omniSearchResultsSection: some View {
        let hits = store.omniSearch(omniQuery)
        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("INSTANT OFFLINE ANSWERS (\(hits.count))")
                    .font(.system(size: 11.5, weight: .bold))
                    .foregroundStyle(.secondary)
                Spacer()
                Button("Clear") { omniQuery = "" }
                    .font(.system(size: 12, weight: .semibold))
            }

            if hits.isEmpty {
                BentoCard {
                    Text("No services, regions, AI models, or release notes matched '\(omniQuery)'.")
                        .font(.system(size: 13.5))
                        .foregroundStyle(.secondary)
                }
            } else {
                ForEach(hits) { hit in
                    switch hit.kind {
                    case .service:
                        if let svc = store.servicesBySlug[hit.targetSlugOrId] {
                            NavigationLink {
                                ServiceDetailNativeView(store: store, service: svc)
                            } label: {
                                omniHitRow(hit: hit, icon: "cube.transparent.fill", tint: CloudPalette.blue)
                            }
                            .buttonStyle(.plain)
                        }
                    case .region:
                        if let reg = store.regionsById[hit.targetSlugOrId] {
                            Button {
                                selectedRegionSheet = reg
                            } label: {
                                omniHitRow(hit: hit, icon: "globe.americas.fill", tint: CloudPalette.emerald)
                            }
                            .buttonStyle(.plain)
                        }
                    case .model:
                        Button {
                            selectedTab = .catalog
                        } label: {
                            omniHitRow(hit: hit, icon: "Cpu", systemFallback: "sparkles", tint: CloudPalette.violet)
                        }
                        .buttonStyle(.plain)
                    case .update:
                        Button {
                            selectedTab = .updates
                        } label: {
                            omniHitRow(hit: hit, icon: "newspaper.fill", tint: CloudPalette.amber)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private func omniHitRow(hit: OmniSearchHit, icon: String, systemFallback: String? = nil, tint: Color) -> some View {
        BentoCard(padding: 13) {
            HStack(spacing: 12) {
                Image(systemName: systemFallback ?? icon)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(tint)
                    .frame(width: 36, height: 36)
                    .background(Circle().fill(tint.opacity(0.12)))

                VStack(alignment: .leading, spacing: 3) {
                    HStack {
                        Text(hit.title)
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)
                        Spacer()
                        SemanticPill(hit.badge, tint: tint)
                    }
                    Text(hit.subtitle)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
        }
    }

    // MARK: - 2x2 Bento Telemetry Grid

    private var bentoTelemetryGrid: some View {
        let counts = store.catalog.meta.counts
        return LazyVGrid(columns: [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)], spacing: 12) {
            Button { selectedTab = .catalog } label: {
                bentoStatTile(
                    icon: "square.stack.3d.up.fill",
                    tint: CloudPalette.blue,
                    value: "\(counts.totalServices)",
                    label: "Cloud Services",
                    caption: "\(counts.regionalServices) Regional • \(counts.globalServices) Global"
                )
            }
            .buttonStyle(.plain)

            Button { selectedTab = .globe } label: {
                bentoStatTile(
                    icon: "globe.americas.fill",
                    tint: CloudPalette.emerald,
                    value: "\(counts.availableRegions)",
                    label: "Active Regions",
                    caption: "\(counts.lowCo2Regions) Low CO₂ 🌱 • +\(counts.futureRegions) Future"
                )
            }
            .buttonStyle(.plain)

            Button { selectedTab = .catalog } label: {
                bentoStatTile(
                    icon: "sparkles",
                    tint: CloudPalette.violet,
                    value: "\(counts.aiModels)",
                    label: "GenAI & Models",
                    caption: "\(counts.aiModelFamilies) Families • \(counts.gpuZones) GPU Zones"
                )
            }
            .buttonStyle(.plain)

            Button { selectedTab = .studio } label: {
                bentoStatTile(
                    icon: "shield.checkered",
                    tint: CloudPalette.amber,
                    value: "\(counts.formalSlaServices ?? 149)",
                    label: "Formal SLAs",
                    caption: "\(counts.highSla9999Services ?? 41) Services ≥ 99.99%"
                )
            }
            .buttonStyle(.plain)
        }
    }

    private func bentoStatTile(icon: String, tint: Color, value: String, label: String, caption: String) -> some View {
        BentoCard(accent: tint, padding: 15) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: icon)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(tint)
                        .frame(width: 32, height: 32)
                        .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(tint.opacity(0.14)))
                    Spacer()
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(.tertiary)
                }
                Text(value)
                    .font(.system(size: 28, weight: .heavy, design: .rounded))
                    .foregroundStyle(.primary)
                    .contentTransition(.numericText())
                VStack(alignment: .leading, spacing: 2) {
                    Text(label)
                        .font(.system(size: 13.5, weight: .bold, design: .rounded))
                    Text(caption)
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        }
    }

    // MARK: - Swift Charts Bento Analytics Row

    private var swiftChartsRow: some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 12) {
                slaDonutCard
                finOpsBarCard
            }
            VStack(spacing: 12) {
                slaDonutCard
                finOpsBarCard
            }
        }
    }

    private var slaDonutCard: some View {
        BentoCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label("SLA Uptime Tiers", systemImage: "chart.pie.fill")
                        .font(.system(size: 13.5, weight: .bold, design: .rounded))
                        .foregroundStyle(CloudPalette.emerald)
                    Spacer()
                    Text("99.9%–100%")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.secondary)
                }

                HStack(spacing: 14) {
                    Chart(slaDistribution) { item in
                        SectorMark(
                            angle: .value("Services", item.count),
                            innerRadius: .ratio(0.62),
                            angularInset: 2
                        )
                        .cornerRadius(4)
                        .foregroundStyle(item.tint)
                    }
                    .frame(width: 96, height: 96)

                    VStack(alignment: .leading, spacing: 5) {
                        ForEach(slaDistribution) { item in
                            HStack(spacing: 6) {
                                Circle().fill(item.tint).frame(width: 8, height: 8)
                                Text(item.label)
                                    .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                                Spacer()
                                Text("\(item.count)")
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
        }
    }

    private var finOpsBarCard: some View {
        BentoCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label("Regional Cost Index", systemImage: "chart.bar.xaxis")
                        .font(.system(size: 13.5, weight: .bold, design: .rounded))
                        .foregroundStyle(CloudPalette.blue)
                    Spacer()
                    Text("vs us-central1")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.secondary)
                }

                Chart(costTierBuckets) { bucket in
                    BarMark(
                        x: .value("Regions", bucket.count),
                        y: .value("Tier", bucket.tier)
                    )
                    .cornerRadius(6)
                    .foregroundStyle(bucket.tint.gradient)
                    .annotation(position: .trailing) {
                        Text("\(bucket.count)")
                            .font(.system(size: 11, weight: .bold, design: .rounded))
                            .foregroundStyle(.secondary)
                    }
                }
                .chartXAxis(.hidden)
                .frame(height: 96)
            }
        }
    }

    // MARK: - Customer Architecture Blueprints Carousel

    private var customerStacksSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Customer Architecture Stacks", systemImage: "CPU")
                    .labelStyle(.titleOnly)
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                Spacer()
                Button {
                    selectedTab = .studio
                } label: {
                    Text("Open SLA Studio →")
                        .font(.system(size: 12.5, weight: .semibold))
                        .foregroundStyle(CloudPalette.blue)
                }
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(store.customerStacks) { stack in
                        let svcs = stack.serviceSlugs.compactMap { store.servicesBySlug[$0] }
                        let sla = SLACalculator.evaluateCompositeSLA(services: svcs, topology: stack.topologyMode)
                        let reports = SLACalculator.evaluateStackReadiness(
                            stack: stack,
                            servicesBySlug: store.servicesBySlug,
                            regionsById: store.regionsById
                        )

                        Button {
                            selectedStackSheet = stack
                        } label: {
                            BentoCard(accent: CloudPalette.blue, padding: 15) {
                                VStack(alignment: .leading, spacing: 10) {
                                    HStack {
                                        SemanticPill("🛡️ \(sla.formattedUptime)", tint: CloudPalette.emerald)
                                        SemanticPill(stack.topologyMode.shortLabel, tint: CloudPalette.blue)
                                        Spacer()
                                    }
                                    Text(stack.name)
                                        .font(.system(size: 15.5, weight: .bold, design: .rounded))
                                        .foregroundStyle(.primary)
                                        .lineLimit(1)
                                    Text(stack.subtitle)
                                        .font(.system(size: 12))
                                        .foregroundStyle(.secondary)
                                        .lineLimit(2)

                                    HStack(spacing: 6) {
                                        ForEach(reports, id: \.regionId) { rep in
                                            let full = rep.missingServiceNames.isEmpty
                                            Text("\(rep.regionId) \(full ? "✓" : "(\(rep.availableCount)/\(rep.totalCount))")")
                                                .font(.system(size: 10.5, weight: .semibold, design: .monospaced))
                                                .foregroundStyle(full ? CloudPalette.emerald : CloudPalette.amber)
                                                .padding(.horizontal, 7)
                                                .padding(.vertical, 4)
                                                .background(
                                                    Capsule().fill((full ? CloudPalette.emerald : CloudPalette.amber).opacity(0.12))
                                                )
                                        }
                                    }
                                }
                            }
                            .frame(width: 305)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    // MARK: - Official Release Notes Horizontal Story Cards

    private var releasePulseCarousel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Latest Service Updates")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                Spacer()
                Button {
                    selectedTab = .updates
                } label: {
                    Text("All \(store.catalog.releaseNotes.count) Notes →")
                        .font(.system(size: 12.5, weight: .semibold))
                        .foregroundStyle(CloudPalette.blue)
                }
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(store.catalog.releaseNotes.prefix(8)) { note in
                        BentoCard(padding: 14) {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    SemanticPill(note.releaseType, tint: releaseTint(note.releaseType))
                                    Spacer()
                                    Text(note.date)
                                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                        .foregroundStyle(.secondary)
                                }
                                Text(note.productName)
                                    .font(.system(size: 14.5, weight: .bold, design: .rounded))
                                    .lineLimit(1)
                                Text(note.summary)
                                    .font(.system(size: 12))
                                    .foregroundStyle(.secondary)
                                    .lineLimit(3)
                            }
                        }
                        .frame(width: 265)
                    }
                }
            }
        }
    }

    private func releaseTint(_ type: String) -> Color {
        let up = type.uppercased()
        if up.contains("FEATURE") || up.contains("LAUNCH") { return CloudPalette.emerald }
        if up.contains("SECURITY") || up.contains("DEPRECATED") { return CloudPalette.coral }
        if up.contains("FIX") || up.contains("CHANGE") { return CloudPalette.amber }
        return CloudPalette.blue
    }
}

// MARK: - Customer Stack Inspector Sheet

public struct CustomerStackInspectorSheet: View {
    @Bindable var store: CatalogStore
    public let stack: CustomerStack
    @Environment(\.dismiss) private var dismiss

    public var body: some View {
        let svcs = stack.serviceSlugs.compactMap { store.servicesBySlug[$0] }
        let sla = SLACalculator.evaluateCompositeSLA(services: svcs, topology: stack.topologyMode)
        let readiness = SLACalculator.evaluateStackReadiness(
            stack: stack,
            servicesBySlug: store.servicesBySlug,
            regionsById: store.regionsById
        )

        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    BentoCard(accent: CloudPalette.emerald) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(stack.subtitle)
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                            HStack(spacing: 18) {
                                VStack(alignment: .leading) {
                                    Text("COMPOSITE SLA")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundStyle(.secondary)
                                    Text(sla.formattedUptime)
                                        .font(.system(size: 30, weight: .heavy, design: .rounded))
                                        .foregroundStyle(CloudPalette.emerald)
                                }
                                VStack(alignment: .leading) {
                                    Text("MAX DOWNTIME / MO")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundStyle(.secondary)
                                    Text(sla.formattedMonthlyDowntime)
                                        .font(.system(size: 19, weight: .bold, design: .monospaced))
                                }
                            }
                            Text(stack.topologyMode.formulaCaption)
                                .font(.system(size: 11.5, design: .monospaced))
                                .foregroundStyle(.secondary)
                        }
                    }

                    BentoCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Regional Readiness Audit")
                                .font(.system(size: 15, weight: .bold, design: .rounded))
                            ForEach(readiness, id: \.regionId) { rep in
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text("\(rep.regionName) (\(rep.regionId))")
                                            .font(.system(size: 13.5, weight: .bold))
                                        if rep.missingServiceNames.isEmpty {
                                            Text("100% of stack services available")
                                                .font(.system(size: 11.5))
                                                .foregroundStyle(CloudPalette.emerald)
                                        } else {
                                            Text("Missing: \(rep.missingServiceNames.joined(separator: ", "))")
                                                .font(.system(size: 11.5))
                                                .foregroundStyle(CloudPalette.coral)
                                        }
                                    }
                                    Spacer()
                                    RingGaugeView(
                                        progress: rep.readinessRatio,
                                        label: "\(rep.availableCount)/\(rep.totalCount)",
                                        tint: rep.missingServiceNames.isEmpty ? CloudPalette.emerald : CloudPalette.amber,
                                        size: 40
                                    )
                                }
                                Divider()
                            }
                        }
                    }

                    BentoCard {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Included Stack Services (\(svcs.count))")
                                .font(.system(size: 15, weight: .bold, design: .rounded))
                            ForEach(svcs) { svc in
                                HStack {
                                    Text(svc.name)
                                        .font(.system(size: 13.5, weight: .semibold))
                                    Spacer()
                                    SemanticPill(svc.sla.headlineDisplay, tint: CloudPalette.emerald)
                                }
                                .padding(.vertical, 3)
                            }
                        }
                    }
                }
                .padding(16)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle(stack.name)
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
