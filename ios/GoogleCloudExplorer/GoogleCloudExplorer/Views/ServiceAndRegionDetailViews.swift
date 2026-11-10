import SwiftUI

// MARK: - Rich Native Service Detail View

public struct ServiceDetailNativeView: View {
    @Bindable var store: CatalogStore
    public let service: CloudService
    @State private var selectedTierIndex: Int = 0
    @State private var selectedRegionSheet: CloudRegion?

    public init(store: CatalogStore, service: CloudService) {
        self.store = store
        self.service = service
    }

    private var activeTier: SLATier? {
        guard !service.sla.tiers.isEmpty else { return nil }
        let idx = min(max(0, selectedTierIndex), service.sla.tiers.count - 1)
        return service.sla.tiers[idx]
    }

    private var isBookmarked: Bool {
        store.bookmarkedServiceSlugs.contains(service.slug)
    }

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Hero Header Card
                VStack(alignment: .leading, spacing: 12) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 6) {
                                SemanticPill(service.category, tint: CloudPalette.blue, systemImage: "square.stack.3d.up.fill")
                                SemanticPill(service.isGlobal ? "Global Edge" : "\(service.regionCount) Regions", tint: CloudPalette.emerald, systemImage: "globe")
                            }
                            Text(service.name)
                                .font(.system(size: 26, weight: .bold, design: .rounded))
                        }
                        Spacer()
                        RingGaugeView(
                            progress: service.isGlobal ? 1.0 : (service.coveragePct / 100.0),
                            label: service.isGlobal ? "100%" : "\(Int(service.coveragePct.rounded()))%",
                            tint: CloudPalette.blue,
                            size: 54
                        )
                    }

                    if !service.apiNames.isEmpty {
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 6) {
                                ForEach(service.apiNames, id: \.self) { api in
                                    Text(api)
                                        .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                                        .padding(.horizontal, 9)
                                        .padding(.vertical, 4)
                                        .background(Capsule().fill(CloudPalette.elevatedBackground))
                                }
                                if service.totalApiMethods > 0 {
                                    SemanticPill("\(service.totalApiMethods) REST Ops", tint: CloudPalette.violet, systemImage: "terminal.fill")
                                }
                            }
                        }
                    }
                }
                .padding(18)
                .background(
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .fill(CloudPalette.cardBackground)
                )

                // Interactive SLA Architecture Card
                BentoCard(accent: CloudPalette.emerald) {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Label("SLA & Uptime Architecture", systemImage: "shield.lefthalf.filled.badge.checkmark")
                                .font(.system(size: 15, weight: .bold, design: .rounded))
                                .foregroundStyle(CloudPalette.emerald)
                            Spacer()
                            if let url = URL(string: service.sla.slaUrl) {
                                Link(destination: url) {
                                    Label("Official SLA", systemImage: "arrow.up.right.square")
                                        .font(.system(size: 12, weight: .semibold))
                                }
                            }
                        }

                        if service.sla.tiers.count > 1 {
                            Picker("SLA Tier", selection: $selectedTierIndex.animation(.snappy)) {
                                ForEach(Array(service.sla.tiers.enumerated()), id: \.offset) { idx, tier in
                                    Text(tier.tierName).tag(idx)
                                }
                            }
                            .pickerStyle(.segmented)
                        }

                        if let tier = activeTier {
                            HStack(spacing: 16) {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("TARGET UPTIME")
                                        .font(.system(size: 10.5, weight: .bold))
                                        .foregroundStyle(.secondary)
                                    Text(tier.uptimeDisplay)
                                        .font(.system(size: 32, weight: .heavy, design: .rounded))
                                        .foregroundStyle(CloudPalette.emerald)
                                        .contentTransition(.numericText())
                                }
                                Divider().frame(height: 40)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("MONTHLY BUDGET")
                                        .font(.system(size: 10.5, weight: .bold))
                                        .foregroundStyle(.secondary)
                                    Text(tier.maxMonthlyDowntime)
                                        .font(.system(size: 18, weight: .bold, design: .monospaced))
                                        .contentTransition(.numericText())
                                }
                                Spacer()
                                VStack(alignment: .trailing, spacing: 2) {
                                    Text("ANNUAL")
                                        .font(.system(size: 10.5, weight: .bold))
                                        .foregroundStyle(.secondary)
                                    Text(tier.maxAnnualDowntime)
                                        .font(.system(size: 14, weight: .semibold, design: .monospaced))
                                        .foregroundStyle(.secondary)
                                }
                            }

                            Text(tier.topology)
                                .font(.system(size: 12.5, weight: .medium))
                                .foregroundStyle(.secondary)
                        } else {
                            Text("No formal monthly financial-credit SLA published (Preview, Free-only, or best-effort control plane).")
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                        }

                        if !service.sla.haRequirements.isEmpty {
                            Divider()
                            Text("HA QUALIFICATION PREREQUISITES")
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundStyle(.secondary)
                            ForEach(service.sla.haRequirements, id: \.self) { req in
                                HStack(alignment: .top, spacing: 8) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .font(.system(size: 13))
                                        .foregroundStyle(CloudPalette.emerald)
                                        .padding(.top, 2)
                                    Text(req)
                                        .font(.system(size: 12.5))
                                        .foregroundStyle(.primary)
                                }
                            }
                        }

                        if !service.sla.creditSchedule.isEmpty {
                            Divider()
                            HStack(spacing: 8) {
                                ForEach(service.sla.creditSchedule) { credit in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(credit.creditPct)
                                            .font(.system(size: 14, weight: .heavy, design: .rounded))
                                            .foregroundStyle(CloudPalette.amber)
                                        Text(credit.threshold)
                                            .font(.system(size: 10.5))
                                            .foregroundStyle(.secondary)
                                            .lineLimit(1)
                                    }
                                    .padding(8)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(
                                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                                            .fill(CloudPalette.elevatedBackground)
                                    )
                                }
                            }
                        }
                    }
                }

                // FinOps Pricing & Cost Watchouts Card
                BentoCard(accent: CloudPalette.blue) {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Label("FinOps Billing & Discount Profile", systemImage: "dollarsign.gauge.chart.lefthalf.righthalf")
                                .font(.system(size: 15, weight: .bold, design: .rounded))
                                .foregroundStyle(CloudPalette.blue)
                            Spacer()
                            if let url = URL(string: service.pricing.pricingUrl) {
                                Link(destination: url) {
                                    Label("Pricing", systemImage: "arrow.up.right.square")
                                        .font(.system(size: 12, weight: .semibold))
                                }
                            }
                        }

                        VStack(alignment: .leading, spacing: 4) {
                            Text(service.pricing.billingModel)
                                .font(.system(size: 16, weight: .bold, design: .rounded))
                            Text(service.pricing.primaryUnits)
                                .font(.system(size: 12.5, design: .monospaced))
                                .foregroundStyle(.secondary)
                        }

                        HStack(spacing: 8) {
                            SemanticPill(
                                service.pricing.hasFreeTier ? "Free Tier Eligible" : "Metered Usage",
                                tint: service.pricing.hasFreeTier ? CloudPalette.emerald : .secondary,
                                systemImage: service.pricing.hasFreeTier ? "gift.fill" : "creditcard.fill"
                            )
                            if service.pricing.spotOrBatchDiscount {
                                SemanticPill("Spot / Batch Discount", tint: CloudPalette.violet, systemImage: "bolt.fill")
                            }
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            Text("CUD / Commitment: \(service.pricing.cudSupport)")
                                .font(.system(size: 12.5, weight: .medium))
                            Text("Free Tier Note: \(service.pricing.freeTierNote)")
                                .font(.system(size: 12))
                                .foregroundStyle(.secondary)
                        }

                        if !service.pricing.costDrivers.isEmpty {
                            Divider()
                            Text("ARCHITECTURAL COST WATCHOUTS")
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundStyle(.secondary)
                            ForEach(service.pricing.costDrivers, id: \.self) { driver in
                                HStack(alignment: .top, spacing: 8) {
                                    Image(systemName: "exclamationmark.triangle.fill")
                                        .font(.system(size: 12))
                                        .foregroundStyle(CloudPalette.amber)
                                        .padding(.top, 2)
                                    Text(driver)
                                        .font(.system(size: 12.5))
                                }
                            }
                        }
                    }
                }

                // Regional Availability Chips
                BentoCard {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Label(
                                service.isGlobal ? "Global Anycast Availability" : "Available Google Cloud Regions (\(service.regions.count))",
                                systemImage: "map.fill"
                            )
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            Spacer()
                            if !service.multiRegions.isEmpty {
                                Text("Multi-Region: \(service.multiRegions.joined(separator: ", "))")
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundStyle(CloudPalette.violet)
                            }
                        }

                        if service.regions.isEmpty && service.isGlobal {
                            Text("Served globally across Google Cloud edge locations without single-region pinning.")
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                        } else {
                            LazyVGrid(columns: [GridItem(.adaptive(minimum: 135), spacing: 8)], spacing: 8) {
                                ForEach(service.regions, id: \.self) { rid in
                                    let reg = store.regionsById[rid]
                                    Button {
                                        if let reg {
                                            selectedRegionSheet = reg
                                        }
                                    } label: {
                                        HStack(spacing: 4) {
                                            VStack(alignment: .leading, spacing: 1) {
                                                Text(rid)
                                                    .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                                                    .foregroundStyle(.primary)
                                                    .lineLimit(1)
                                                if let rname = reg?.regionName {
                                                    Text(rname)
                                                        .font(.system(size: 10))
                                                        .foregroundStyle(.secondary)
                                                        .lineLimit(1)
                                                }
                                            }
                                            Spacer(minLength: 2)
                                            if reg?.isLowCo2 == true {
                                                Text("🌱").font(.system(size: 11))
                                            }
                                        }
                                        .padding(.horizontal, 9)
                                        .padding(.vertical, 7)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(
                                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                                .fill(CloudPalette.elevatedBackground)
                                        )
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }
                }

                UnofficialDisclaimerRow(syncState: store.syncState)
            }
            .padding(16)
        }
        .background(CloudPalette.canvasBackground)
        .navigationTitle(service.name)
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .sensoryFeedback(.selection, trigger: selectedTierIndex)
        .sheet(item: $selectedRegionSheet) { reg in
            RegionInspectorSheetView(store: store, region: reg)
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
        }
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    store.toggleServiceBookmark(service.slug)
                } label: {
                    Image(systemName: isBookmarked ? "bookmark.fill" : "bookmark")
                        .foregroundStyle(isBookmarked ? CloudPalette.amber : .primary)
                }
                .sensoryFeedback(.impact(weight: .medium), trigger: isBookmarked)
            }
        }
    }
}

// MARK: - Frosted-Glass Interactive Region Inspector Sheet (Services, AI Models, Hardware & Gaps)

public struct RegionInspectorSheetView: View {
    public enum InspectorTab: String, CaseIterable, Identifiable {
        case services = "Services"
        case models = "AI Models"
        case hardware = "Hardware & Cost"
        case gaps = "Missing Gaps"

        public var id: String { rawValue }
    }

    @Bindable var store: CatalogStore
    public let region: CloudRegion
    @State private var activeTab: InspectorTab = .services
    @State private var filterText: String = ""
    @State private var selectedModelFamily: String = "All"
    @Environment(\.dismiss) private var dismiss

    public init(store: CatalogStore, region: CloudRegion, initialTab: InspectorTab = .services) {
        self.store = store
        self.region = region
        self._activeTab = State(initialValue: initialTab)
    }

    private var isBookmarked: Bool {
        store.bookmarkedRegionIds.contains(region.regionId)
    }

    private var availableServices: [CloudService] {
        let regional = store.catalog.services.filter { svc in
            svc.isGlobal || svc.regions.contains(region.regionId) || region.services.contains(svc.name)
        }
        let q = filterText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return regional }
        return regional.filter {
            $0.name.lowercased().contains(q)
                || $0.category.lowercased().contains(q)
                || $0.sla.headlineDisplay.lowercased().contains(q)
        }
    }

    private var allRegionModels: [AIModel] {
        store.catalog.models.filter { m in
            m.regions.contains(region.regionId) || m.globalEndpoint
        }
    }

    private var modelFamiliesInRegion: [String] {
        let fams = Set(allRegionModels.map(\.family)).sorted()
        return ["All"] + fams
    }

    private var availableModels: [AIModel] {
        let q = filterText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return allRegionModels.filter { m in
            let matchesFam = selectedModelFamily == "All" || m.family == selectedModelFamily
            let matchesQ = q.isEmpty
                || m.modelName.lowercased().contains(q)
                || m.modelId.lowercased().contains(q)
                || m.family.lowercased().contains(q)
                || m.modality.lowercased().contains(q)
            return matchesFam && matchesQ
        }
    }

    private var missingRegionalServices: [CloudService] {
        let missing = store.catalog.services.filter { !$0.isGlobal && $0.regionCount > 0 && !$0.regions.contains(region.regionId) }
        let q = filterText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !q.isEmpty else { return missing }
        return missing.filter { $0.name.lowercased().contains(q) || $0.category.lowercased().contains(q) }
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    // Region Header
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(spacing: 6) {
                                Text(region.regionId)
                                    .font(.system(size: 13, weight: .bold, design: .monospaced))
                                    .foregroundStyle(CloudPalette.blue)
                                if region.isLowCo2 {
                                    SemanticPill("Low CO₂ 🌱", tint: CloudPalette.emerald)
                                }
                                SemanticPill(
                                    String(format: "%.2fx Cost", region.pricing.relativeComputeIndex),
                                    tint: region.pricing.relativeComputeIndex <= 1.05 ? CloudPalette.emerald : CloudPalette.amber
                                )
                            }
                            Text(region.fullLocation)
                                .font(.system(size: 22, weight: .bold, design: .rounded))
                            Text("\(region.subRegion) • Launched \(region.dateLaunched) • \(region.zoneCount) Zones (\(region.zones.joined(separator: ", ")))")
                                .font(.system(size: 12))
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button {
                            store.toggleRegionBookmark(region.regionId)
                        } label: {
                            Image(systemName: isBookmarked ? "star.fill" : "star")
                                .font(.system(size: 20))
                                .foregroundStyle(isBookmarked ? CloudPalette.amber : .secondary)
                        }
                        .buttonStyle(.plain)
                        .sensoryFeedback(.impact(weight: .light), trigger: isBookmarked)
                    }

                    // Interactive Tappable KPI Tiles (Tap any number to view full list below!)
                    HStack(spacing: 8) {
                        interactiveMetricButton(
                            tab: .services,
                            title: "SERVICES",
                            value: "\(region.serviceCount)",
                            subtitle: "Tap to list",
                            tint: CloudPalette.blue
                        )
                        interactiveMetricButton(
                            tab: .models,
                            title: "AI MODELS",
                            value: "\(allRegionModels.count)",
                            subtitle: "Tap for IDs",
                            tint: CloudPalette.violet
                        )
                        interactiveMetricButton(
                            tab: .hardware,
                            title: "GPUS & COST",
                            value: region.gpus.isEmpty ? String(format: "%.2fx", region.pricing.relativeComputeIndex) : "\(region.gpus.count) GPUs",
                            subtitle: "Zones & CUDs",
                            tint: CloudPalette.emerald
                        )
                        interactiveMetricButton(
                            tab: .gaps,
                            title: "GAPS",
                            value: "\(missingRegionalServices.count)",
                            subtitle: "Not in region",
                            tint: CloudPalette.coral
                        )
                    }

                    // Search Bar for Services / AI Models / Gaps
                    if activeTab != .hardware {
                        HStack(spacing: 8) {
                            Image(systemName: "magnifyingglass")
                                .foregroundStyle(.secondary)
                            TextField(
                                activeTab == .services
                                    ? "Filter \(region.serviceCount) services in \(region.regionName)…"
                                    : activeTab == .models
                                        ? "Filter AI models (e.g., Gemini, Claude, Veo)…"
                                        : "Filter missing services…",
                                text: $filterText
                            )
                            .font(.system(size: 13.5, design: .rounded))
                            if !filterText.isEmpty {
                                Button {
                                    filterText = ""
                                } label: {
                                    Image(systemName: "xmark.circle.fill")
                                        .foregroundStyle(.secondary)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 9)
                        .background(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .fill(CloudPalette.cardBackground)
                        )
                    }

                    // Active Tab Content
                    switch activeTab {
                    case .services:
                        servicesListSection
                    case .models:
                        modelsListSection
                    case .hardware:
                        hardwareAndFinOpsSection
                    case .gaps:
                        gapsListSection
                    }
                }
                .padding(18)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("\(region.regionName) (\(region.regionId))")
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

    private func interactiveMetricButton(
        tab: InspectorTab,
        title: String,
        value: String,
        subtitle: String,
        tint: Color
    ) -> some View {
        let isSelected = activeTab == tab
        return Button {
            withAnimation(.snappy) {
                activeTab = tab
            }
        } label: {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 9, weight: .black, design: .rounded))
                    .foregroundStyle(isSelected ? tint : .secondary)
                Text(value)
                    .font(.system(size: 17, weight: .black, design: .rounded))
                    .foregroundStyle(tint)
                Text(subtitle)
                    .font(.system(size: 9.5, weight: .semibold, design: .rounded))
                    .foregroundStyle(isSelected ? .primary : .secondary)
                    .lineLimit(1)
            }
            .padding(9)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(isSelected ? tint.opacity(0.15) : CloudPalette.cardBackground)
                    .overlay(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .strokeBorder(isSelected ? tint : Color.clear, lineWidth: 1.6)
                    )
            )
        }
        .buttonStyle(.plain)
        .sensoryFeedback(.selection, trigger: isSelected)
    }

    // MARK: 1. Available Services List (Tappable to open full SLA & API detail)

    private var servicesListSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Available Services in \(region.regionName) (\(availableServices.count))", systemImage: "square.stack.3d.up.fill")
                    .font(.system(size: 14.5, weight: .heavy, design: .rounded))
                    .foregroundStyle(CloudPalette.blue)
                Spacer()
                Text("Tap any service for SLA")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(.secondary)
            }

            ForEach(availableServices) { svc in
                NavigationLink {
                    ServiceDetailNativeView(store: store, service: svc)
                } label: {
                    BentoCard(padding: 12) {
                        HStack(spacing: 10) {
                            VStack(alignment: .leading, spacing: 3) {
                                HStack(spacing: 6) {
                                    Text(svc.name)
                                        .font(.system(size: 14.5, weight: .bold, design: .rounded))
                                        .foregroundStyle(.primary)
                                    if svc.isGlobal {
                                        SemanticPill("Global", tint: CloudPalette.cyan)
                                    }
                                    if svc.pricing.hasFreeTier {
                                        SemanticPill("Free Tier", tint: CloudPalette.emerald)
                                    }
                                }
                                Text("\(svc.category) • Max downtime \(svc.sla.maxMonthlyDowntime)/mo")
                                    .font(.system(size: 11.5))
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            SemanticPill("🛡️ \(svc.sla.headlineDisplay)", tint: CloudPalette.emerald)
                            Image(systemName: "chevron.right")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundStyle(.tertiary)
                        }
                    }
                }
                .buttonStyle(.plain)
            }
        }
    }

    // MARK: 2. Available AI & Foundation Models List (Model Name, Version/ID, Family, Modality)

    private var modelsListSection: some View {
        let directRegionalCount = availableModels.filter { $0.regions.contains(region.regionId) }.count
        return VStack(alignment: .leading, spacing: 10) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(modelFamiliesInRegion, id: \.self) { fam in
                        let sel = selectedModelFamily == fam
                        Button {
                            selectedModelFamily = fam
                        } label: {
                            Text(fam)
                                .font(.system(size: 11.5, weight: .bold, design: .rounded))
                                .foregroundStyle(sel ? .white : .primary)
                                .padding(.horizontal, 11)
                                .padding(.vertical, 6)
                                .background(
                                    Capsule().fill(sel ? CloudPalette.violet : CloudPalette.cardBackground)
                                )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            HStack {
                Label(
                    "\(availableModels.count) AI Models (\(directRegionalCount) Regional in \(region.regionId) + Global)",
                    systemImage: "sparkles"
                )
                .font(.system(size: 13.5, weight: .heavy, design: .rounded))
                .foregroundStyle(CloudPalette.violet)
                Spacer()
            }

            ForEach(availableModels) { model in
                let isRegionalHere = model.regions.contains(region.regionId)
                BentoCard(accent: isRegionalHere ? CloudPalette.violet : nil, padding: 12) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(model.modelName)
                                    .font(.system(size: 14.5, weight: .bold, design: .rounded))
                                    .foregroundStyle(.primary)
                                Text("ID / Version: \(model.modelId)")
                                    .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                                    .foregroundStyle(CloudPalette.blue)
                            }
                            Spacer()
                            if isRegionalHere {
                                SemanticPill("📍 \(region.regionId)", tint: CloudPalette.emerald)
                            } else {
                                SemanticPill("🌐 Global Endpoint", tint: CloudPalette.cyan)
                            }
                        }

                        HStack(spacing: 6) {
                            SemanticPill(model.family, tint: CloudPalette.violet)
                            SemanticPill(model.stage, tint: model.stage.uppercased() == "GA" ? CloudPalette.emerald : CloudPalette.amber)
                            Text("• \(model.modality)")
                                .font(.system(size: 11.5))
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    }
                }
            }
        }
    }

    // MARK: 3. Hardware, GPUs, CPUs & FinOps Section

    private var hardwareAndFinOpsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            BentoCard {
                VStack(alignment: .leading, spacing: 10) {
                    Label("FinOps Tier & Zone Hardware", systemImage: "cpu.fill")
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                    Text("\(region.pricing.tier) • \(region.pricing.deltaVsBaseline) • Storage \(String(format: "%.2fx", region.pricing.relativeStorageIndex))")
                        .font(.system(size: 12.5, weight: .semibold))
                    Text("CUD Discounts: 1Y (-\(region.pricing.cud1yDiscountPct)%) • 3Y (-\(region.pricing.cud3yDiscountPct)%)")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(CloudPalette.emerald)
                    Text("Egress: \(region.pricing.interRegionEgressBand)")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(.secondary)

                    if !region.gpus.isEmpty {
                        Divider()
                        Text("GPU / AI ACCELERATORS (\(region.gpus.count))")
                            .font(.system(size: 10.5, weight: .bold))
                            .foregroundStyle(.secondary)
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 130), spacing: 6)], spacing: 6) {
                            ForEach(region.gpus, id: \.self) { gpu in
                                SemanticPill(gpu, tint: CloudPalette.violet, systemImage: "sparkles")
                            }
                        }
                    }

                    if !region.cpus.isEmpty {
                        Divider()
                        Text("CPU MICROARCHITECTURES (\(region.cpus.count))")
                            .font(.system(size: 10.5, weight: .bold))
                            .foregroundStyle(.secondary)
                        Text(region.cpus.joined(separator: " • "))
                            .font(.system(size: 12))
                            .foregroundStyle(.primary)
                    }

                    if !region.machineSeries.isEmpty {
                        Divider()
                        Text("COMPUTE MACHINE SERIES (\(region.machineSeries.count))")
                            .font(.system(size: 10.5, weight: .bold))
                            .foregroundStyle(.secondary)
                        Text(region.machineSeries.joined(separator: " • "))
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundStyle(.primary)
                    }
                }
            }
        }
    }

    // MARK: 4. Missing Regional Services Gap Radar

    private var gapsListSection: some View {
        BentoCard(accent: missingRegionalServices.isEmpty ? CloudPalette.emerald : CloudPalette.coral) {
            VStack(alignment: .leading, spacing: 10) {
                Label(
                    "Service Gap Radar (\(missingRegionalServices.count) Regional Services Not in \(region.regionId))",
                    systemImage: "exclamationmark.shield.fill"
                )
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundStyle(missingRegionalServices.isEmpty ? CloudPalette.emerald : CloudPalette.coral)

                if missingRegionalServices.isEmpty {
                    Text("All cataloged regional Google Cloud services are available in \(region.regionId).")
                        .font(.system(size: 12.5))
                        .foregroundStyle(.secondary)
                } else {
                    Text("Tap any service below to see which fallback regions support it:")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                    ForEach(missingRegionalServices) { svc in
                        NavigationLink {
                            ServiceDetailNativeView(store: store, service: svc)
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(svc.name)
                                        .font(.system(size: 13.5, weight: .bold))
                                        .foregroundStyle(.primary)
                                    Text("\(svc.category) • Available in \(svc.regionCount) other regions")
                                        .font(.system(size: 11.5))
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                SemanticPill("🛡️ \(svc.sla.headlineDisplay)", tint: CloudPalette.coral)
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundStyle(.tertiary)
                            }
                            .padding(.vertical, 6)
                        }
                        .buttonStyle(.plain)
                        Divider()
                    }
                }
            }
        }
    }
}

// MARK: - Offline Sync & Legal Notice Sheet

public struct OfflineSyncSettingsSheet: View {
    @Bindable var store: CatalogStore
    @Environment(\.dismiss) private var dismiss

    public init(store: CatalogStore) {
        self.store = store
    }

    public var body: some View {
        NavigationStack {
            Form {
                Section("Offline-First & 24h Auto-Refresh Status") {
                    LabeledContent("Current Mode", value: store.syncState.badgeLabel)
                    LabeledContent("Snapshot Timestamp", value: store.catalog.meta.generatedAt)
                    LabeledContent("24h Auto-Refresh", value: store.lastAutoSyncDateString)
                    LabeledContent("Catalog ETag", value: store.catalog.etag ?? "bundled")
                    LabeledContent("Bundled Entities", value: "\(store.catalog.services.count) Svcs • \(store.catalog.regions.count) Regions • \(store.catalog.models.count) Models")

                    Button {
                        Task { await store.refreshFromServer(silent: false) }
                    } label: {
                        HStack {
                            Label("Sync Latest Online Catalog Now", systemImage: "arrow.triangle.2.circlepath.icloud.fill")
                                .fontWeight(.bold)
                            Spacer()
                            if store.syncState == .syncing {
                                ProgressView()
                            }
                        }
                    }

                    Button {
                        Task { await store.refreshViaGeminiAPI() }
                    } label: {
                        HStack {
                            Label("Enrich Live Updates via Gemini API ✨", systemImage: "sparkles")
                                .fontWeight(.semibold)
                            Spacer()
                            if store.syncState == .syncing {
                                ProgressView()
                            }
                        }
                    }

                    Button("Reload Bundled Offline Catalog (153 Svcs / 43 Regions)") {
                        store.resetToBundledCatalog()
                    }
                }

                Section {
                    TextField("Sync Endpoint URL", text: $store.syncEndpointURLString)
                        .font(.system(size: 12, design: .monospaced))
                        #if os(iOS)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        #endif
                        .autocorrectionDisabled()

                    Button("Use Online GitHub 24h Cloud Feed (Anywhere)") {
                        store.syncEndpointURLString = CatalogStore.githubOnlineCatalogURL
                        Task { await store.refreshFromServer(silent: false) }
                    }

                    Button("Use Local Mac Wi-Fi Server (192.168.0.157:8080)") {
                        store.syncEndpointURLString = CatalogStore.localMacCatalogURL
                        Task { await store.refreshFromServer(silent: false) }
                    }
                } header: {
                    Text("Online & Wi-Fi Sync Sources")
                } footer: {
                    Text("Configured for automatic 24-hour refresh via GitHub Actions (raw.githubusercontent.com) with automatic fallback to your Mac's local Wi-Fi server and Gemini API.")
                }

                Section("Unofficial Tool Disclaimer & Authoritative Docs") {
                    Text("This application is an unofficial community & architecture reference tool. It is not affiliated with, endorsed by, or sponsored by Google LLC or Google Cloud.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)

                    if let docsURL = URL(string: "https://cloud.google.com/docs"),
                       let slaURL = URL(string: "https://cloud.google.com/terms/sla"),
                       let pricingURL = URL(string: "https://cloud.google.com/pricing") {
                        Link("Official Google Cloud Documentation ↗", destination: docsURL)
                        Link("Official Google Cloud SLA Agreements ↗", destination: slaURL)
                        Link("Official Google Cloud Pricing & Calculator ↗", destination: pricingURL)
                    }
                }
            }
            .navigationTitle("Offline Sync & About")
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
