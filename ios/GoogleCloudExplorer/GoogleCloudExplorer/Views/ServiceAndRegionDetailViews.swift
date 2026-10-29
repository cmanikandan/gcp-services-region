import SwiftUI

// MARK: - Rich Native Service Detail View

public struct ServiceDetailNativeView: View {
    @Bindable var store: CatalogStore
    public let service: CloudService
    @State private var selectedTierIndex: Int = 0

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
                                    HStack(spacing: 4) {
                                        Text(rid)
                                            .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                                            .lineLimit(1)
                                        if reg?.isLowCo2 == true {
                                            Text("🌱").font(.system(size: 11))
                                        }
                                    }
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 6)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(
                                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                                            .fill(CloudPalette.elevatedBackground)
                                    )
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

// MARK: - Frosted-Glass Region Inspector Sheet

public struct RegionInspectorSheetView: View {
    @Bindable var store: CatalogStore
    public let region: CloudRegion

    public init(store: CatalogStore, region: CloudRegion) {
        self.store = store
        self.region = region
    }

    private var isBookmarked: Bool {
        store.bookmarkedRegionIds.contains(region.regionId)
    }

    private var missingRegionalServices: [CloudService] {
        store.catalog.services.filter { !$0.isGlobal && $0.regionCount > 0 && !$0.regions.contains(region.regionId) }
    }

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
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

                // Bento Metrics Row
                HStack(spacing: 10) {
                    miniMetric(title: "SERVICES", value: "\(region.serviceCount)", tint: CloudPalette.blue)
                    miniMetric(title: "AI MODELS", value: "\(region.aiModelCount)", tint: CloudPalette.violet)
                    miniMetric(title: "COMPUTE", value: String(format: "%.2fx", region.pricing.relativeComputeIndex), tint: CloudPalette.emerald)
                    miniMetric(title: "GPUS", value: region.gpus.isEmpty ? "CPU" : "\(region.gpus.count)", tint: CloudPalette.amber)
                }

                // FinOps & Hardware Card
                BentoCard {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("FinOps Tier & Zone Hardware", systemImage: "cpu.fill")
                            .font(.system(size: 14, weight: .bold, design: .rounded))
                        Text("\(region.pricing.tier) • \(region.pricing.deltaVsBaseline) • Storage \(String(format: "%.2fx", region.pricing.relativeStorageIndex))")
                            .font(.system(size: 12.5, weight: .semibold))
                        Text("Egress: \(region.pricing.interRegionEgressBand)")
                            .font(.system(size: 12, design: .monospaced))
                            .foregroundStyle(.secondary)

                        if !region.gpus.isEmpty {
                            Divider()
                            Text("GPU / AI ACCELERATORS")
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundStyle(.secondary)
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 6) {
                                    ForEach(region.gpus, id: \.self) { gpu in
                                        SemanticPill(gpu, tint: CloudPalette.violet, systemImage: "sparkles")
                                    }
                                }
                            }
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

                // Regional Gap Radar
                BentoCard(accent: missingRegionalServices.isEmpty ? CloudPalette.emerald : CloudPalette.coral) {
                    VStack(alignment: .leading, spacing: 8) {
                        Label(
                            "Service Gap Radar (\(missingRegionalServices.count) Not in \(region.regionId))",
                            systemImage: "exclamationmark.shield.fill"
                        )
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(missingRegionalServices.isEmpty ? CloudPalette.emerald : CloudPalette.coral)

                        if missingRegionalServices.isEmpty {
                            Text("All cataloged regional Google Cloud services are available in \(region.regionId).")
                                .font(.system(size: 12.5))
                                .foregroundStyle(.secondary)
                        } else {
                            Text("Verify failover/placement alternatives for these regional services:")
                                .font(.system(size: 12))
                                .foregroundStyle(.secondary)
                            LazyVGrid(columns: [GridItem(.adaptive(minimum: 145), spacing: 6)], spacing: 6) {
                                ForEach(missingRegionalServices.prefix(16)) { svc in
                                    Text(svc.name)
                                        .font(.system(size: 11, weight: .medium))
                                        .lineLimit(1)
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 5)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(
                                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                                .fill(CloudPalette.coral.opacity(0.10))
                                        )
                                }
                            }
                        }
                    }
                }
            }
            .padding(18)
        }
    }

    private func miniMetric(title: String, value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(.system(size: 9.5, weight: .bold))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(size: 17, weight: .heavy, design: .rounded))
                .foregroundStyle(tint)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(CloudPalette.cardBackground)
        )
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
                Section("Offline-First Snapshot Status") {
                    LabeledContent("Current Mode", value: store.syncState.badgeLabel)
                    LabeledContent("Snapshot Timestamp", value: store.catalog.meta.generatedAt)
                    LabeledContent("Catalog ETag", value: store.catalog.etag ?? "bundled")
                    LabeledContent("Bundled Entities", value: "\(store.catalog.services.count) Svcs • \(store.catalog.regions.count) Regions • \(store.catalog.models.count) Models")
                }

                Section {
                    TextField("Sync Endpoint URL", text: $store.syncEndpointURLString)
                        .font(.system(size: 13, design: .monospaced))
                        #if os(iOS)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        #endif
                        .autocorrectionDisabled()

                    Button {
                        Task { await store.refreshFromServer(silent: false) }
                    } label: {
                        HStack {
                            Label("Sync Delta Snapshot Now (ETag + Gzip)", systemImage: "arrow.triangle.2.circlepath.icloud.fill")
                            Spacer()
                            if store.syncState == .syncing {
                                ProgressView()
                            }
                        }
                    }
                } header: {
                    Text("Live Delta Sync Endpoint")
                } footer: {
                    Text("All searches, SLA math, 3D Globe layers, and FinOps cost scrubbers run 100% locally with zero live Google Cloud API calls. When online, tapping Sync checks ETag headers against your server.py or Cloud Run endpoint.")
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
