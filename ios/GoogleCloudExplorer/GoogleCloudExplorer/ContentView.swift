import SwiftUI
#if canImport(CoreSpotlight)
import CoreSpotlight
#endif

// MARK: - Root Adaptive Shell (iPhone TabView + iPad NavigationSplitView + Auth Vault Gate)

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
    @State private var auth = AuthManager()
    @State private var copilot = GeminiCopilotService()
    @State private var selectedSection: ExplorerSection = .pulse
    @State private var showingAuthSheet = false
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    public init() {}

    public var body: some View {
        ZStack {
            Group {
                if horizontalSizeClass == .regular {
                    iPadSplitShell
                } else {
                    iPhoneTabShell
                }
            }
            .tint(store.vibeTheme.primaryAccent)

            if case .vaultLocked(let profile) = auth.sessionState {
                BiometricVaultLockOverlay(
                    profile: profile,
                    vibeTheme: store.vibeTheme,
                    onUnlock: {
                        Task { _ = await auth.unlockVaultWithBiometrics() }
                    },
                    onGhostFallback: {
                        Task { await auth.signOut(store: store) }
                    }
                )
                .transition(.opacity)
            }
        }
        .sheet(isPresented: $showingAuthSheet) {
            AuthPortalSheetView(store: store, auth: auth)
                .presentationDetents([.large])
                .presentationDragIndicator(.visible)
        }
        .task {
            store.onVaultMutated = { [weak store, weak auth] in
                guard let store, let auth else { return }
                Task { await auth.syncVaultIfAuthenticated(with: store) }
            }
            await store.bootstrapAndSyncInBackground()
            await auth.bootstrapAuthSession(with: store)
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
            PulseBentoHomeView(
                store: store,
                auth: auth,
                copilot: copilot,
                selectedTab: $selectedSection,
                onOpenAuthPortal: { showingAuthSheet = true }
            )
            .tabItem { Label(ExplorerSection.pulse.rawValue, systemImage: ExplorerSection.pulse.systemImage) }
            .tag(ExplorerSection.pulse)

            InteractiveGlobeMapView(store: store)
                .tabItem { Label(ExplorerSection.globe.rawValue, systemImage: ExplorerSection.globe.systemImage) }
                .tag(ExplorerSection.globe)

            NativeCatalogBrowserView(store: store)
                .tabItem { Label(ExplorerSection.catalog.rawValue, systemImage: ExplorerSection.catalog.systemImage) }
                .tag(ExplorerSection.catalog)

            PricingSLAStudioView(store: store, auth: auth, copilot: copilot, onOpenAuthPortal: { showingAuthSheet = true })
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
                selection: Binding<ExplorerSection?>(
                    get: { selectedSection },
                    set: { if let newValue = $0 { selectedSection = newValue } }
                )
            ) {
                Section {
                    Button {
                        showingAuthSheet = true
                    } label: {
                        HStack(spacing: 10) {
                            Text(auth.currentUser?.avatarEmoji ?? store.vibeTheme.emoji)
                                .font(.system(size: 20))
                                .frame(width: 34, height: 34)
                                .background(Circle().fill(store.vibeTheme.primaryAccent.opacity(0.16)))
                            VStack(alignment: .leading, spacing: 2) {
                                Text(auth.currentUser != nil ? "@\(auth.currentUser!.handle)" : "Claim @Handle ✨")
                                    .font(.system(size: 14, weight: .heavy, design: .rounded))
                                Text(auth.currentUser?.builderLevel ?? "Ghost Mode • Tap for Passkey")
                                    .font(.system(size: 11))
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }

                Section("Explore Google Cloud") {
                    ForEach(ExplorerSection.allCases) { section in
                        Label(section.rawValue, systemImage: section.systemImage)
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .tag(section)
                    }
                }
            }
            .navigationTitle("Google Cloud Explorer")
        } detail: {
            switch selectedSection {
            case .pulse:
                PulseBentoHomeView(
                    store: store,
                    auth: auth,
                    copilot: copilot,
                    selectedTab: $selectedSection,
                    onOpenAuthPortal: { showingAuthSheet = true }
                )
            case .globe:
                InteractiveGlobeMapView(store: store)
            case .catalog:
                NativeCatalogBrowserView(store: store)
            case .studio:
                PricingSLAStudioView(store: store, auth: auth, copilot: copilot, onOpenAuthPortal: { showingAuthSheet = true })
            case .updates:
                ReleasePulseTimelineView(store: store)
            }
        }
    }
}
