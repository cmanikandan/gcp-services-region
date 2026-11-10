import SwiftUI
import Charts

// MARK: - Tab 1: Gen Z Pulse Neo-Bento Intelligence Hub

public struct PulseBentoHomeView: View {
    @Bindable var store: CatalogStore
    @Bindable var auth: AuthManager
    @Bindable var copilot: GeminiCopilotService
    @Binding var selectedTab: ExplorerSection
    public var onOpenAuthPortal: () -> Void

    @State private var omniQuery: String = ""
    @State private var selectedRegionSheet: CloudRegion?
    @State private var selectedModelSheet: AIModel?
    @State private var selectedStackSheet: CustomerStack?
    @State private var showingSyncSheet = false
    @State private var showingGeminiCopilotSheet = false
    @State private var pendingGeminiPrompt: String?

    public init(
        store: CatalogStore,
        auth: AuthManager,
        copilot: GeminiCopilotService,
        selectedTab: Binding<ExplorerSection>,
        onOpenAuthPortal: @escaping () -> Void = {}
    ) {
        self.store = store
        self.auth = auth
        self.copilot = copilot
        self._selectedTab = selectedTab
        self.onOpenAuthPortal = onOpenAuthPortal
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
            SLABucket(label: "99.99%", count: max(1, four9), tint: store.vibeTheme.primaryAccent),
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
            CostTierBucket(tier: "1.04–1.15x", count: t2, tint: store.vibeTheme.primaryAccent),
            CostTierBucket(tier: "1.16x+ Prem", count: t3, tint: CloudPalette.amber)
        ]
    }

    private let quickPromptChips: [(label: String, query: String)] = [
        ("🔥 99.999% Club", "99.999%"),
        ("🤖 Claude & Gemini", "Claude"),
        ("💸 Mumbai Cost", "asia-south1"),
        ("⚡ H100 GPUs", "H100"),
        ("🛡️ Spanner SLA", "Spanner SLA")
    ]

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    heroHeaderCard

                    if !omniQuery.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        omniSearchResultsSection
                    } else {
                        geminiCopilotBannerCard
                        builderPassportStripCard
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
                await auth.syncVaultIfAuthenticated(with: store)
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        ForEach(VibeTheme.allCases) { theme in
                            Button {
                                withAnimation(.spring(response: 0.3, dampingFraction: 0.75)) {
                                    store.vibeTheme = theme
                                }
                            } label: {
                                Label(
                                    "\(theme.emoji) \(theme.displayName)",
                                    systemImage: store.vibeTheme == theme ? "checkmark.circle.fill" : "circle"
                                )
                            }
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Text(store.vibeTheme.emoji)
                                .font(.system(size: 14))
                            Text("Vibe")
                                .font(.system(size: 12, weight: .bold, design: .rounded))
                        }
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(Capsule().fill(CloudPalette.cardBackground))
                    }
                    .accessibilityLabel("Switch Gen Z Vibe Theme")
                }

                ToolbarItem(placement: .primaryAction) {
                    HStack(spacing: 8) {
                        AuthToolbarPillButton(
                            handle: auth.currentUser?.handle,
                            avatarEmoji: auth.currentUser?.avatarEmoji ?? "⚡",
                            isSynced: auth.isVaultSyncedLive,
                            accent: store.vibeTheme.primaryAccent,
                            action: onOpenAuthPortal
                        )

                        Button {
                            showingSyncSheet = true
                        } label: {
                            Image(systemName: "icloud.and.arrow.down")
                                .font(.system(size: 14, weight: .bold))
                        }
                        .accessibilityLabel("Offline Sync & Settings")
                    }
                }
            }
            .sheet(item: $selectedRegionSheet) { reg in
                RegionInspectorSheetView(store: store, region: reg)
                    .presentationDetents([.large])
                    .presentationDragIndicator(.visible)
            }
            .sheet(item: $selectedModelSheet) { model in
                AIModelInspectorSheet(model: model, regionsById: store.regionsById)
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
            .sheet(isPresented: $showingGeminiCopilotSheet) {
                GeminiCopilotSheetView(
                    store: store,
                    copilot: copilot,
                    initialPrompt: pendingGeminiPrompt
                )
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
            }
        }
    }

    // MARK: - Gen Z Neo-Bento Aura Hero + Instant Omni-Search

    private var heroHeaderCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 6) {
                        StickerBadge("\(store.vibeTheme.emoji) ZERO-LATENCY OFFLINE", background: CloudPalette.acidLime, foreground: .black)
                        StickerBadge("UNOFFICIAL TOOL", background: .white.opacity(0.22), foreground: .white)
                    }
                    Text("Google Cloud Regions, SLAs & AI Vibe Check")
                        .font(.system(size: 22, weight: .black, design: .rounded))
                        .foregroundStyle(.white)
                        .padding(.top, 2)
                    Text("Unofficial independent companion • Always verify SLAs & SKUs in official Google Cloud docs (cloud.google.com/docs).")
                        .font(.system(size: 11.5, weight: .medium, design: .rounded))
                        .foregroundStyle(.white.opacity(0.84))
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer()
            }

            // Frosted Aura Omni-Search Bar
            HStack(spacing: 10) {
                Image(systemName: "sparkle.magnifyingglass")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(CloudPalette.acidLime)
                TextField("Drop a query: 'Spanner SLA', 'Mumbai', 'Claude', 'H100'…", text: $omniQuery)
                    .font(.system(size: 14, weight: .semibold, design: .rounded))
                    .foregroundStyle(.white)
                    .tint(CloudPalette.acidLime)
                if !omniQuery.isEmpty {
                    Button {
                        omniQuery = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.white.opacity(0.78))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(.white.opacity(0.14))
                    .overlay(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .strokeBorder(.white.opacity(0.26), lineWidth: 1.1)
                    )
            )

            // Trending Vibe Chips
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(quickPromptChips, id: \.label) { chip in
                        Button {
                            omniQuery = chip.query
                        } label: {
                            Text(chip.label)
                                .font(.system(size: 11.5, weight: .bold, design: .rounded))
                                .foregroundStyle(.white.opacity(0.95))
                                .padding(.horizontal, 11)
                                .padding(.vertical, 6)
                                .background(
                                    Capsule(style: .continuous)
                                        .fill(.white.opacity(0.15))
                                        .overlay(Capsule().strokeBorder(.white.opacity(0.2), lineWidth: 0.8))
                                )
                        }
                        .buttonStyle(GenZBouncyButtonStyle())
                    }
                }
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 30, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: store.vibeTheme.heroGradientColors,
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 30, style: .continuous)
                        .strokeBorder(.white.opacity(0.20), lineWidth: 1.2)
                )
                .shadow(color: store.vibeTheme.primaryAccent.opacity(0.26), radius: 16, x: 0, y: 8)
        )
    }

    // MARK: - Gemini 3.8 Cloud Architect Copilot Banner

    private var geminiCopilotBannerCard: some View {
        Button {
            pendingGeminiPrompt = nil
            showingGeminiCopilotSheet = true
        } label: {
            BentoCard(accent: CloudPalette.violet, padding: 14) {
                HStack(spacing: 12) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 20, weight: .black))
                        .foregroundStyle(.white)
                        .frame(width: 44, height: 44)
                        .background(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .fill(
                                    LinearGradient(
                                        colors: [CloudPalette.violet, store.vibeTheme.primaryAccent],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                        )

                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 6) {
                            Text("Gemini Cloud Architect ✨")
                                .font(.system(size: 14.5, weight: .black, design: .rounded))
                                .foregroundStyle(.primary)
                            SemanticPill(
                                copilot.apiKeyConfigured ? copilot.selectedModel.rawValue : "Configure Key",
                                tint: copilot.apiKeyConfigured ? CloudPalette.emerald : CloudPalette.amber
                            )
                        }
                        Text("Ask Gemini 3.8 Flash about Google Cloud SLAs, Low CO₂ regions, H100 GPUs, or FinOps CUDs.")
                            .font(.system(size: 11.5))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }

                    Spacer(minLength: 4)
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .buttonStyle(GenZBouncyButtonStyle())
    }

    // MARK: - Interactive Builder Passport / Ghost Mode Banner

    private var builderPassportStripCard: some View {
        Button(action: onOpenAuthPortal) {
            BentoCard(accent: store.vibeTheme.primaryAccent, padding: 14) {
                HStack(spacing: 12) {
                    Text(auth.currentUser?.avatarEmoji ?? "🪪")
                        .font(.system(size: 24))
                        .frame(width: 44, height: 44)
                        .background(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .fill(store.vibeTheme.primaryAccent.opacity(0.16))
                        )

                    if let profile = auth.currentUser {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 6) {
                                Text("@\(profile.handle)")
                                    .font(.system(size: 15, weight: .black, design: .rounded))
                                    .foregroundStyle(.primary)
                                SemanticPill("\(profile.xpPoints) XP", tint: store.vibeTheme.primaryAccent)
                            }
                            Text("\(profile.builderLevel) • \(store.bookmarkedServiceSlugs.count) Svcs & \(store.customerStacks.count) Stacks in Vault")
                                .font(.system(size: 11.5, weight: .medium))
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    } else {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 6) {
                                Text("Ghost Mode Active 👻")
                                    .font(.system(size: 14.5, weight: .black, design: .rounded))
                                    .foregroundStyle(.primary)
                                SemanticPill("Passkey / PKCE", tint: store.vibeTheme.primaryAccent)
                            }
                            Text("Tap to claim your @handle & sync Google Cloud SLA stacks with Apple, Google PKCE, or Passkey.")
                                .font(.system(size: 11.5))
                                .foregroundStyle(.secondary)
                                .lineLimit(2)
                        }
                    }

                    Spacer(minLength: 4)
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .buttonStyle(GenZBouncyButtonStyle())
    }

    // MARK: - Live Omni-Search Answer Cards

    private var omniSearchResultsSection: some View {
        let hits = store.omniSearch(omniQuery)
        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("INSTANT OFFLINE ANSWERS (\(hits.count))")
                    .font(.system(size: 11.5, weight: .black, design: .rounded))
                    .foregroundStyle(.secondary)
                Spacer()
                Button {
                    pendingGeminiPrompt = omniQuery
                    showingGeminiCopilotSheet = true
                } label: {
                    Label("Ask Gemini ✨", systemImage: "sparkles")
                        .font(.system(size: 11.5, weight: .heavy, design: .rounded))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(Capsule().fill(CloudPalette.violet))
                }
                .buttonStyle(GenZBouncyButtonStyle())

                Button("Clear") { omniQuery = "" }
                    .font(.system(size: 12, weight: .bold, design: .rounded))
            }

            if hits.isEmpty {
                BentoCard {
                    Text("No Google Cloud services, regions, AI models, or release notes matched '\(omniQuery)'.")
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
                                omniHitRow(hit: hit, icon: "cube.transparent.fill", tint: store.vibeTheme.primaryAccent)
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
                            if let model = store.catalog.models.first(where: { $0.modelId == hit.targetSlugOrId }) {
                                selectedModelSheet = model
                            } else {
                                store.requestedCatalogMode = "models"
                                selectedTab = .catalog
                            }
                        } label: {
                            omniHitRow(hit: hit, icon: "sparkles", tint: CloudPalette.violet)
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

    private func omniHitRow(hit: OmniSearchHit, icon: String, tint: Color) -> some View {
        BentoCard(padding: 13) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(tint)
                    .frame(width: 38, height: 38)
                    .background(Circle().fill(tint.opacity(0.14)))

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

    // MARK: - 2x2 Neo-Bento Telemetry Grid

    private var bentoTelemetryGrid: some View {
        let counts = store.catalog.meta.counts
        return LazyVGrid(columns: [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)], spacing: 12) {
            Button {
                store.requestedCatalogMode = "services"
                selectedTab = .catalog
            } label: {
                bentoStatTile(
                    icon: "square.stack.3d.up.fill",
                    tint: store.vibeTheme.primaryAccent,
                    value: "\(counts.totalServices)",
                    label: "Cloud Services",
                    caption: "\(counts.regionalServices) Regional • \(counts.globalServices) Global"
                )
            }
            .buttonStyle(GenZBouncyButtonStyle())

            Button { selectedTab = .globe } label: {
                bentoStatTile(
                    icon: "globe.americas.fill",
                    tint: CloudPalette.emerald,
                    value: "\(counts.availableRegions)",
                    label: "Active Regions",
                    caption: "\(counts.lowCo2Regions) Low CO₂ 🌱 • +\(counts.futureRegions) Next"
                )
            }
            .buttonStyle(GenZBouncyButtonStyle())

            Button {
                store.requestedCatalogMode = "models"
                selectedTab = .catalog
            } label: {
                bentoStatTile(
                    icon: "sparkles",
                    tint: CloudPalette.violet,
                    value: "\(counts.aiModels)",
                    label: "GenAI & Models",
                    caption: "\(counts.aiModelFamilies) Families • \(counts.gpuZones) GPU Zones"
                )
            }
            .buttonStyle(GenZBouncyButtonStyle())

            Button { selectedTab = .studio } label: {
                bentoStatTile(
                    icon: "shield.checkered",
                    tint: CloudPalette.amber,
                    value: "\(counts.formalSlaServices ?? 149)",
                    label: "Formal SLAs",
                    caption: "\(counts.highSla9999Services ?? 41) Services ≥ 99.99%"
                )
            }
            .buttonStyle(GenZBouncyButtonStyle())
        }
    }

    private func bentoStatTile(icon: String, tint: Color, value: String, label: String, caption: String) -> some View {
        BentoCard(accent: tint, padding: 15) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: icon)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(tint)
                        .frame(width: 34, height: 34)
                        .background(RoundedRectangle(cornerRadius: 11, style: .continuous).fill(tint.opacity(0.15)))
                    Spacer()
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 11, weight: .black))
                        .foregroundStyle(.tertiary)
                }
                Text(value)
                    .font(.system(size: 29, weight: .black, design: .rounded))
                    .foregroundStyle(.primary)
                    .contentTransition(.numericText())
                VStack(alignment: .leading, spacing: 2) {
                    Text(label)
                        .font(.system(size: 13.5, weight: .heavy, design: .rounded))
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
                    Label("Uptime Tiers", systemImage: "chart.pie.fill")
                        .font(.system(size: 13.5, weight: .heavy, design: .rounded))
                        .foregroundStyle(CloudPalette.emerald)
                    Spacer()
                    Text("99.9%–100%")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
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
                    Label("FinOps Multipliers", systemImage: "chart.bar.xaxis")
                        .font(.system(size: 13.5, weight: .heavy, design: .rounded))
                        .foregroundStyle(store.vibeTheme.primaryAccent)
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
                Text("Saved Architecture Stacks ⚡")
                    .font(.system(size: 16, weight: .black, design: .rounded))
                Spacer()
                Button {
                    selectedTab = .studio
                } label: {
                    Text("SLA Studio →")
                        .font(.system(size: 12.5, weight: .bold, design: .rounded))
                        .foregroundStyle(store.vibeTheme.primaryAccent)
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
                            BentoCard(accent: store.vibeTheme.primaryAccent, padding: 15) {
                                VStack(alignment: .leading, spacing: 10) {
                                    HStack {
                                        SemanticPill("🛡️ \(sla.formattedUptime)", tint: CloudPalette.emerald)
                                        SemanticPill(stack.topologyMode.shortLabel, tint: store.vibeTheme.primaryAccent)
                                        Spacer()
                                    }
                                    Text(stack.name)
                                        .font(.system(size: 15.5, weight: .heavy, design: .rounded))
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
                        .buttonStyle(GenZBouncyButtonStyle())
                    }
                }
            }
        }
    }

    // MARK: - Official Release Notes Horizontal Story Cards

    private var releasePulseCarousel: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Fresh Google Cloud Drops 🔥")
                    .font(.system(size: 16, weight: .black, design: .rounded))
                Spacer()
                Button {
                    selectedTab = .updates
                } label: {
                    Text("All \(store.catalog.releaseNotes.count) Notes →")
                        .font(.system(size: 12.5, weight: .bold, design: .rounded))
                        .foregroundStyle(store.vibeTheme.primaryAccent)
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
                                    .font(.system(size: 14.5, weight: .heavy, design: .rounded))
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
        return store.vibeTheme.primaryAccent
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
                                        .font(.system(size: 30, weight: .black, design: .rounded))
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
                                .font(.system(size: 15, weight: .heavy, design: .rounded))
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
                                .font(.system(size: 15, weight: .heavy, design: .rounded))
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
