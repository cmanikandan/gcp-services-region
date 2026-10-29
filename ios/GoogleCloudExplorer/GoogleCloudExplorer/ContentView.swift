import SwiftUI
#if canImport(CoreSpotlight)
import CoreSpotlight
#endif

// MARK: - Root Adaptive Shell (iPhone TabView + iPad NavigationSplitView)

public enum ExplorerSection: String, CaseIterable, Identifiable, Hashable {
    case pulse = "Pulse"
    case globe = "Globe"
    case catalog = "Catalog"
    case studio = "SLA & Cost"
    case updates = "Updates"

    public var id: String { rawValue }

    public var systemImage: String {
        switch self {
        case .pulse: return "sparkles.rectangle.stack.fill"
        case .globe: return "globe.americas.fill"
        case .catalog: return "square.grid.2x2.fill"
        case .studio: return "shield.lefthalf.filled.badge.checkmark"
        case .updates: return "bolt.badge.clock.fill"
        }
    }
}

public struct ContentView: View {
    @State private var store = CatalogStore()
    @State private var selectedSection: ExplorerSection = .pulse
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    public init() {}

    public var body: some View {
        Group {
            if horizontalSizeClass == .regular {
                iPadSplitShell
            } else {
                iPhoneTabShell
            }
        }
        .tint(CloudPalette.blue)
        .task {
            await store.bootstrapAndSyncInBackground()
        }
        #if os(iOS) && canImport(CoreSpotlight)
        .onContinueUserActivity(CSSearchableItemActionType) { activity in
            if let id = activity.userInfo?[CSSearchableItemActivityIdentifier] as? String {
                store.handleSpotlightIdentifier(id)
                if id.hasPrefix("service:") {
                    selectedSection = .catalog
                } else if id.hasPrefix("region:") {
                    selectedSection = .globe
                }
            }
        }
        #endif
    }

    private var iPhoneTabShell: some View {
        TabView(selection: $selectedSection) {
            PulseBentoHomeView(store: store, selectedTab: $selectedSection)
                .tabItem { Label(ExplorerSection.pulse.rawValue, systemImage: ExplorerSection.pulse.systemImage) }
                .tag(ExplorerSection.pulse)

            InteractiveGlobeMapView(store: store)
                .tabItem { Label(ExplorerSection.globe.rawValue, systemImage: ExplorerSection.globe.systemImage) }
                .tag(ExplorerSection.globe)

            NativeCatalogBrowserView(store: store)
                .tabItem { Label(ExplorerSection.catalog.rawValue, systemImage: ExplorerSection.catalog.systemImage) }
                .tag(ExplorerSection.catalog)

            PricingSLAStudioView(store: store)
                .tabItem { Label(ExplorerSection.studio.rawValue, systemImage: ExplorerSection.studio.systemImage) }
                .tag(ExplorerSection.studio)

            ReleasePulseTimelineView(store: store)
                .tabItem { Label(ExplorerSection.updates.rawValue, systemImage: ExplorerSection.updates.systemImage) }
                .tag(ExplorerSection.updates)
        }
    }

    private var iPadSplitShell: some View {
        NavigationSplitView {
            List(
                ExplorerSection.allCases,
                selection: Binding<ExplorerSection?>(
                    get: { selectedSection },
                    set: { if let newValue = $0 { selectedSection = newValue } }
                )
            ) { section in
                Label(section.rawValue, systemImage: section.systemImage)
                    .font(.system(size: 15, weight: .semibold, design: .rounded))
                    .tag(section)
            }
            .navigationTitle("Cloud Explorer")
        } detail: {
            switch selectedSection {
            case .pulse:
                PulseBentoHomeView(store: store, selectedTab: $selectedSection)
            case .globe:
                InteractiveGlobeMapView(store: store)
            case .catalog:
                NativeCatalogBrowserView(store: store)
            case .studio:
                PricingSLAStudioView(store: store)
            case .updates:
                ReleasePulseTimelineView(store: store)
            }
        }
    }
}
