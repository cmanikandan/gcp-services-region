import SwiftUI

// MARK: - Tab 5: Magazine-Style Official Release Notes & Regional Snapshot Diffs

public struct ReleasePulseTimelineView: View {
    @Bindable var store: CatalogStore

    public enum FeedScope: String, CaseIterable, Identifiable {
        case releaseNotes = "Official Release Notes"
        case regionalDiffs = "Regional Launches"
        public var id: String { rawValue }
    }

    @State private var feedScope: FeedScope = .releaseNotes
    @State private var selectedType: String = "All"
    @State private var pinnedOnly: Bool = false
    @State private var searchText: String = ""
    @State private var showingSyncSheet = false

    public init(store: CatalogStore) {
        self.store = store
    }

    private var releaseTypes: [String] {
        let types = Set(store.catalog.releaseNotes.map(\.releaseType)).sorted()
        return ["All"] + types
    }

    private var filteredReleaseNotes: [ReleaseNoteItem] {
        let q = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return store.catalog.releaseNotes.filter { note in
            if pinnedOnly {
                guard let slug = note.serviceSlug, store.bookmarkedServiceSlugs.contains(slug) else {
                    return false
                }
            }
            if selectedType != "All" && note.releaseType != selectedType {
                return false
            }
            guard !q.isEmpty else { return true }
            return note.productName.lowercased().contains(q)
                || note.summary.lowercased().contains(q)
                || note.releaseType.lowercased().contains(q)
        }
    }

    private var filteredDiffs: [WhatsNewItem] {
        let q = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return store.catalog.whatsNew.filter { item in
            guard !q.isEmpty else { return true }
            return item.service.lowercased().contains(q)
                || item.regionName.lowercased().contains(q)
                || item.regionId.lowercased().contains(q)
                || item.details.lowercased().contains(q)
        }
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    Picker("Update Feed", selection: $feedScope.animation(.snappy)) {
                        ForEach(FeedScope.allCases) { scope in
                            Text(scope.rawValue).tag(scope)
                        }
                    }
                    .pickerStyle(.segmented)

                    if feedScope == .releaseNotes {
                        HStack(spacing: 8) {
                            Button {
                                pinnedOnly.toggle()
                            } label: {
                                Label("My Stack", systemImage: pinnedOnly ? "bookmark.fill" : "bookmark")
                                    .font(.system(size: 12, weight: .bold, design: .rounded))
                                    .foregroundStyle(pinnedOnly ? .white : CloudPalette.amber)
                                    .padding(.horizontal, 11)
                                    .padding(.vertical, 6)
                                    .background(
                                        Capsule().fill(pinnedOnly ? CloudPalette.amber : CloudPalette.cardBackground)
                                    )
                            }
                            .buttonStyle(.plain)

                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 6) {
                                    ForEach(releaseTypes, id: \.self) { rt in
                                        let active = selectedType == rt
                                        Button {
                                            selectedType = rt
                                        } label: {
                                            Text(rt)
                                                .font(.system(size: 12, weight: .semibold, design: .rounded))
                                                .foregroundStyle(active ? .white : .primary)
                                                .padding(.horizontal, 11)
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

                        if filteredReleaseNotes.isEmpty {
                            BentoCard {
                                Text("No cached release notes match your current filter.")
                                    .font(.system(size: 13.5))
                                    .foregroundStyle(.secondary)
                            }
                        } else {
                            ForEach(filteredReleaseNotes) { note in
                                releaseNoteCard(note)
                            }
                        }
                    } else {
                        ForEach(filteredDiffs) { diff in
                            regionalDiffCard(diff)
                        }
                    }

                    UnofficialDisclaimerRow(syncState: store.syncState) {
                        showingSyncSheet = true
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("Service Updates")
            .searchable(text: $searchText, prompt: "Filter updates, features, CVEs, or regions…")
            .refreshable {
                await store.refreshFromServer(silent: false)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showingSyncSheet = true
                    } label: {
                        Image(systemName: "arrow.triangle.2.circlepath.icloud")
                    }
                }
            }
            .sheet(isPresented: $showingSyncSheet) {
                OfflineSyncSettingsSheet(store: store)
            }
        }
    }

    private func releaseNoteCard(_ note: ReleaseNoteItem) -> some View {
        let tint = badgeTint(note.releaseType)
        return BentoCard(accent: tint, padding: 15) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    SemanticPill(note.releaseType, tint: tint)
                    Text(note.category)
                        .font(.system(size: 11.5, weight: .medium))
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(note.date)
                        .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                        .foregroundStyle(.secondary)
                }

                Text(note.productName)
                    .font(.system(size: 16.5, weight: .bold, design: .rounded))

                Text(note.summary)
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                HStack {
                    if let slug = note.serviceSlug, let svc = store.servicesBySlug[slug] {
                        NavigationLink {
                            ServiceDetailNativeView(store: store, service: svc)
                        } label: {
                            Label("Inspect \(svc.name) SLA & Regions", systemImage: "cube.transparent")
                                .font(.system(size: 12, weight: .semibold))
                        }
                    }
                    Spacer()
                    if let url = URL(string: note.url) {
                        Link(destination: url) {
                            Label("Release Note ↗", systemImage: "safari")
                                .font(.system(size: 12, weight: .semibold))
                        }
                    }
                }
                .padding(.top, 2)
            }
        }
    }

    private func regionalDiffCard(_ item: WhatsNewItem) -> some View {
        let tint: Color = item.type == "Regional Expansion" ? CloudPalette.emerald : CloudPalette.blue
        return BentoCard(padding: 14) {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    SemanticPill(item.type, tint: tint)
                    Spacer()
                    Text(item.date)
                        .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                Text(item.service)
                    .font(.system(size: 15.5, weight: .bold, design: .rounded))
                Text("\(item.regionName) (\(item.regionId)) — \(item.details)")
                    .font(.system(size: 12.5))
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func badgeTint(_ type: String) -> Color {
        let up = type.uppercased()
        if up.contains("FEATURE") || up.contains("LAUNCH") { return CloudPalette.emerald }
        if up.contains("DEPRECATED") || up.contains("SECURITY") { return CloudPalette.coral }
        if up.contains("FIX") || up.contains("CHANGE") { return CloudPalette.amber }
        return CloudPalette.blue
    }
}
