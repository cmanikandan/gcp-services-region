import SwiftUI

// MARK: - Tab 3: Modern Native Services & AI Models Catalog Browser

public struct NativeCatalogBrowserView: View {
    @Bindable var store: CatalogStore

    public enum CatalogMode: String, CaseIterable, Identifiable {
        case services = "Cloud Services"
        case aiModels = "GenAI & Models"
        public var id: String { rawValue }
    }

    @State private var mode: CatalogMode = .services
    @State private var searchText: String = ""
    @State private var selectedCategory: String = "All"
    @State private var bookmarkedOnly: Bool = false
    @State private var selectedModelSheet: AIModel?
    @State private var navigationPath = NavigationPath()

    public init(store: CatalogStore) {
        self.store = store
    }

    private var availableCategories: [String] {
        if mode == .services {
            let cats = Set(store.catalog.services.map(\.category)).sorted()
            return ["All"] + cats
        } else {
            let fams = Set(store.catalog.models.map(\.family)).sorted()
            return ["All"] + fams
        }
    }

    private var filteredServices: [CloudService] {
        let q = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let normQ = SLACalculator.normalizeSearchToken(q)
        return store.catalog.services.filter { svc in
            if bookmarkedOnly && !store.bookmarkedServiceSlugs.contains(svc.slug) {
                return false
            }
            if selectedCategory != "All" && svc.category != selectedCategory {
                return false
            }
            guard !q.isEmpty else { return true }
            let normName = SLACalculator.normalizeSearchToken(svc.name)
            return svc.name.lowercased().contains(q)
                || (!normQ.isEmpty && normName.contains(normQ))
                || svc.category.lowercased().contains(q)
                || svc.sla.headlineDisplay.lowercased().contains(q)
                || svc.apiNames.joined(separator: " ").lowercased().contains(q)
        }
    }

    private var filteredModels: [AIModel] {
        let q = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return store.catalog.models.filter { model in
            if selectedCategory != "All" && model.family != selectedCategory {
                return false
            }
            guard !q.isEmpty else { return true }
            return model.modelName.lowercased().contains(q)
                || model.modelId.lowercased().contains(q)
                || model.family.lowercased().contains(q)
                || model.modality.lowercased().contains(q)
                || model.regions.joined(separator: " ").lowercased().contains(q)
        }
    }

    public var body: some View {
        NavigationStack(path: $navigationPath) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    // Mode Switcher & Filter Pills
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 10) {
                            Picker("Catalog Mode", selection: $mode.animation(.snappy)) {
                                Text("☁️ Services (\(store.catalog.services.count))").tag(CatalogMode.services)
                                Text("🤖 AI Models (\(store.catalog.models.count))").tag(CatalogMode.aiModels)
                            }
                            .pickerStyle(.segmented)
                            .onChange(of: mode) { _, _ in
                                selectedCategory = "All"
                            }

                            if mode == .services {
                                Button {
                                    bookmarkedOnly.toggle()
                                } label: {
                                    Image(systemName: bookmarkedOnly ? "bookmark.fill" : "bookmark")
                                        .font(.system(size: 15, weight: .bold))
                                        .foregroundStyle(bookmarkedOnly ? .white : CloudPalette.amber)
                                        .frame(width: 36, height: 34)
                                        .background(
                                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                                .fill(bookmarkedOnly ? CloudPalette.amber : CloudPalette.cardBackground)
                                        )
                                }
                                .buttonStyle(.plain)
                                .accessibilityLabel("Toggle Bookmarked Services")
                            }
                        }

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(availableCategories, id: \.self) { cat in
                                    let active = selectedCategory == cat
                                    Button {
                                        withAnimation(.snappy) { selectedCategory = cat }
                                    } label: {
                                        Text(cat)
                                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                                            .foregroundStyle(active ? .white : .primary)
                                            .padding(.horizontal, 12)
                                            .padding(.vertical, 6)
                                            .background(
                                                Capsule().fill(active ? CloudPalette.blue : CloudPalette.cardBackground)
                                            )
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }

                    // Cards Feed
                    if mode == .services {
                        Text("\(filteredServices.count) Google Cloud Services")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(.secondary)

                        ForEach(filteredServices) { svc in
                            NavigationLink(value: svc) {
                                serviceBentoRow(svc)
                            }
                            .buttonStyle(.plain)
                        }
                    } else {
                        Text("\(filteredModels.count) Vertex AI & Partner Models")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(.secondary)

                        ForEach(filteredModels) { model in
                            Button {
                                selectedModelSheet = model
                            } label: {
                                modelBentoRow(model)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("Cloud Catalog")
            .searchable(
                text: $searchText,
                prompt: mode == .services
                    ? "Search 153 services, SLAs, or APIs…"
                    : "Search Gemini, Claude, Llama, Veo, region…"
            )
            .navigationDestination(for: CloudService.self) { svc in
                ServiceDetailNativeView(store: store, service: svc)
            }
            .sheet(item: $selectedModelSheet) { model in
                AIModelInspectorSheet(model: model, regionsById: store.regionsById)
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
            }
            .onChange(of: store.deepLinkedServiceSlug) { _, slug in
                if let slug, let svc = store.servicesBySlug[slug] {
                    mode = .services
                    navigationPath.append(svc)
                    store.deepLinkedServiceSlug = nil
                }
            }
        }
    }

    private func serviceBentoRow(_ svc: CloudService) -> some View {
        let pinned = store.bookmarkedServiceSlugs.contains(svc.slug)
        return BentoCard(padding: 14) {
            HStack(spacing: 14) {
                RingGaugeView(
                    progress: svc.isGlobal ? 1.0 : (svc.coveragePct / 100.0),
                    label: svc.isGlobal ? "GLB" : "\(svc.regionCount)R",
                    tint: svc.isGlobal ? CloudPalette.violet : CloudPalette.blue,
                    size: 46
                )

                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 6) {
                        Text(svc.name)
                            .font(.system(size: 16, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)
                            .lineLimit(1)
                        if pinned {
                            Image(systemName: "bookmark.fill")
                                .font(.system(size: 11))
                                .foregroundStyle(CloudPalette.amber)
                        }
                        Spacer()
                        Image(systemName: "chevron.right")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.tertiary)
                    }

                    Text(svc.category)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)

                    HStack(spacing: 6) {
                        SemanticPill(
                            "🛡️ \(svc.sla.headlineDisplay)",
                            tint: (svc.sla.headlineUptimePct ?? 0) >= 99.99 ? CloudPalette.emerald : CloudPalette.blue
                        )
                        if svc.pricing.hasFreeTier {
                            SemanticPill("Free Tier", tint: CloudPalette.emerald)
                        }
                        if svc.totalApiMethods > 0 {
                            SemanticPill("\(svc.totalApiMethods) Ops", tint: .secondary)
                        }
                    }
                }
            }
        }
    }

    private func modelBentoRow(_ model: AIModel) -> some View {
        BentoCard(accent: CloudPalette.violet, padding: 14) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(model.modelName)
                            .font(.system(size: 16, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)
                        Text(model.modelId)
                            .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                            .foregroundStyle(CloudPalette.blue)
                    }
                    Spacer()
                    SemanticPill(model.modality, tint: CloudPalette.violet)
                }

                HStack(spacing: 6) {
                    SemanticPill(model.family, tint: .secondary)
                    if model.globalEndpoint {
                        SemanticPill("🌐 Global Endpoint", tint: CloudPalette.emerald)
                    }
                    SemanticPill("\(model.regionCount) Regions", tint: CloudPalette.blue)
                }
            }
        }
    }
}

// MARK: - AI Model Native Inspector Sheet

public struct AIModelInspectorSheet: View {
    public let model: AIModel
    public let regionsById: [String: CloudRegion]
    @Environment(\.dismiss) private var dismiss

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    BentoCard(accent: CloudPalette.violet) {
                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                SemanticPill(model.family, tint: CloudPalette.violet, systemImage: "sparkles")
                                SemanticPill(model.stage, tint: CloudPalette.emerald)
                                Spacer()
                            }
                            Text(model.modelName)
                                .font(.system(size: 24, weight: .bold, design: .rounded))
                            Text(model.modelId)
                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                .foregroundStyle(CloudPalette.blue)
                            Text("Modality: \(model.modality)")
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)

                            if let url = URL(string: model.url) {
                                Link(destination: url) {
                                    Label("Official Vertex AI Model Documentation ↗", systemImage: "book.pages.fill")
                                        .font(.system(size: 13, weight: .semibold))
                                }
                                .padding(.top, 4)
                            }
                        }
                    }

                    BentoCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Endpoint Availability")
                                .font(.system(size: 15, weight: .bold, design: .rounded))
                            HStack(spacing: 8) {
                                if model.globalEndpoint {
                                    SemanticPill("🌐 global endpoint", tint: CloudPalette.emerald)
                                }
                                ForEach(model.multiRegions, id: \.self) { mr in
                                    SemanticPill("Multi-Region: \(mr)", tint: CloudPalette.violet)
                                }
                            }

                            Divider()
                            Text("REGIONAL ENDPOINTS (\(model.regions.count))")
                                .font(.system(size: 10.5, weight: .bold))
                                .foregroundStyle(.secondary)

                            LazyVGrid(columns: [GridItem(.adaptive(minimum: 135), spacing: 8)], spacing: 8) {
                                ForEach(model.regions, id: \.self) { rid in
                                    let reg = regionsById[rid]
                                    HStack(spacing: 4) {
                                        Text(rid)
                                            .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
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
                .padding(16)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("AI Model Details")
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
