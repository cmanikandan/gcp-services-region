import Foundation
import Observation
#if canImport(CoreSpotlight)
import CoreSpotlight
#endif

// MARK: - Sync Status & Omni-Search Result Models

public enum DataSyncState: Sendable, Equatable {
    case bundledOffline(generatedAt: String)
    case cachedOnDisk(generatedAt: String)
    case syncing
    case liveSynced(generatedAt: String, etag: String)
    case offlineFallback(reason: String)

    public var badgeLabel: String {
        switch self {
        case .bundledOffline: return "Offline Ready • Bundled"
        case .cachedOnDisk: return "Offline Ready • Cached"
        case .syncing: return "Syncing Delta…"
        case .liveSynced: return "Synced • Live ETag"
        case .offlineFallback: return "Offline Mode"
        }
    }

    public var isHealthyOfflineOrSynced: Bool {
        switch self {
        case .syncing: return false
        default: return true
        }
    }
}

public struct OmniSearchHit: Identifiable, Sendable, Hashable {
    public enum Kind: String, Sendable {
        case service = "Service"
        case region = "Region"
        case model = "AI Model"
        case update = "Release Note"
    }

    public let id: String
    public let kind: Kind
    public let title: String
    public let subtitle: String
    public let badge: String
    public let targetSlugOrId: String
}

// MARK: - Background Disk & Network Sync Actor

actor CatalogSyncActor {
    private let cacheFilename = "mobile_catalog_cached.json"

    private var cacheFileURL: URL? {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?
            .appendingPathComponent("GoogleCloudExplorer", isDirectory: true)
            .appendingPathComponent(cacheFilename)
    }

    func loadCachedDiskCatalog() -> MobileCatalog? {
        guard let url = cacheFileURL,
              FileManager.default.fileExists(atPath: url.path),
              let data = try? Data(contentsOf: url) else {
            return nil
        }
        return try? JSONDecoder().decode(MobileCatalog.self, from: data)
    }

    func saveDiskCatalog(_ data: Data) {
        guard let url = cacheFileURL else { return }
        let dir = url.deletingLastPathComponent()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try? data.write(to: url, options: .atomic)
    }

    func fetchRemoteCatalog(endpoint: URL, currentETag: String?) async throws -> (MobileCatalog?, String?) {
        var request = URLRequest(url: endpoint)
        request.timeoutInterval = 6.0
        request.setValue("gzip, deflate", forHTTPHeaderField: "Accept-Encoding")
        if let etag = currentETag, !etag.isEmpty {
            request.setValue("\"\(etag)\"", forHTTPHeaderField: "If-None-Match")
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        if http.statusCode == 304 {
            return (nil, currentETag)
        }
        guard (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }

        let decoded = try JSONDecoder().decode(MobileCatalog.self, from: data)
        saveDiskCatalog(data)
        let headerETag = http.value(forHTTPHeaderField: "ETag")?.trimmingCharacters(in: CharacterSet(charactersIn: "\""))
        return (decoded, decoded.etag ?? headerETag)
    }
}

// MARK: - Main-Actor Observable Store

@Observable
@MainActor
public final class CatalogStore {
    public private(set) var catalog: MobileCatalog
    public private(set) var syncState: DataSyncState
    public var syncEndpointURLString: String {
        didSet { UserDefaults.standard.set(syncEndpointURLString, forKey: Self.endpointKey) }
    }
    public var bookmarkedServiceSlugs: Set<String> {
        didSet { saveBookmarks() }
    }
    public var bookmarkedRegionIds: Set<String> {
        didSet { saveBookmarks() }
    }
    public var customerStacks: [CustomerStack] {
        didSet { saveCustomerStacks() }
    }
    public var deepLinkedServiceSlug: String?
    public var deepLinkedRegionId: String?

    public private(set) var servicesBySlug: [String: CloudService] = [:]
    public private(set) var servicesByName: [String: CloudService] = [:]
    public private(set) var regionsById: [String: CloudRegion] = [:]

    private let syncActor = CatalogSyncActor()
    private static let endpointKey = "gce.syncEndpoint"
    private static let svcBookmarksKey = "gce.bookmarkedServices"
    private static let regBookmarksKey = "gce.bookmarkedRegions"
    private static let stacksKey = "gce.customerStacks"

    public init(initialCatalog: MobileCatalog? = nil) {
        let loaded = initialCatalog ?? Self.loadBundledCatalog()
        self.catalog = loaded
        self.syncState = .bundledOffline(generatedAt: loaded.meta.generatedAt)
        self.syncEndpointURLString = UserDefaults.standard.string(forKey: Self.endpointKey)
            ?? "http://127.0.0.1:8080/api/mobile-catalog"

        let savedSvcs = UserDefaults.standard.stringArray(forKey: Self.svcBookmarksKey)
            ?? ["spanner", "cloud-run", "vertex-ai", "bigquery", "alloydb"]
        self.bookmarkedServiceSlugs = Set(savedSvcs)

        let savedRegs = UserDefaults.standard.stringArray(forKey: Self.regBookmarksKey)
            ?? ["us-central1", "europe-west4", "asia-south1"]
        self.bookmarkedRegionIds = Set(savedRegs)

        if let stackData = UserDefaults.standard.data(forKey: Self.stacksKey),
           let decodedStacks = try? JSONDecoder().decode([CustomerStack].self, from: stackData),
           !decodedStacks.isEmpty {
            self.customerStacks = decodedStacks
        } else {
            self.customerStacks = Self.defaultReferenceStacks()
        }

        rebuildLookupCaches()
    }

    public static func loadBundledCatalog() -> MobileCatalog {
        if let url = Bundle.main.url(forResource: "mobile_catalog", withExtension: "json"),
           let data = try? Data(contentsOf: url),
           let decoded = try? JSONDecoder().decode(MobileCatalog.self, from: data) {
            return decoded
        }
        return Self.emptyFallbackCatalog()
    }

    public func bootstrapAndSyncInBackground() async {
        if let diskCatalog = await syncActor.loadCachedDiskCatalog(),
           diskCatalog.meta.generatedEpoch >= catalog.meta.generatedEpoch {
            applyCatalog(diskCatalog, state: .cachedOnDisk(generatedAt: diskCatalog.meta.generatedAt))
        }
        indexCoreSpotlight()
        await refreshFromServer(silent: true)
    }

    public func refreshFromServer(silent: Bool = false) async {
        guard let url = URL(string: syncEndpointURLString.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            if !silent {
                syncState = .offlineFallback(reason: "Invalid sync endpoint URL")
            }
            return
        }
        if !silent {
            syncState = .syncing
        }
        do {
            let (updated, etag) = try await syncActor.fetchRemoteCatalog(
                endpoint: url,
                currentETag: catalog.etag
            )
            if let updated {
                applyCatalog(
                    updated,
                    state: .liveSynced(
                        generatedAt: updated.meta.generatedAt,
                        etag: etag ?? (updated.etag ?? "200")
                    )
                )
                indexCoreSpotlight()
            } else {
                syncState = .liveSynced(
                    generatedAt: catalog.meta.generatedAt,
                    etag: etag ?? (catalog.etag ?? "304")
                )
            }
        } catch {
            syncState = .bundledOffline(generatedAt: catalog.meta.generatedAt)
        }
    }

    public func toggleServiceBookmark(_ slug: String) {
        if bookmarkedServiceSlugs.contains(slug) {
            bookmarkedServiceSlugs.remove(slug)
        } else {
            bookmarkedServiceSlugs.insert(slug)
        }
    }

    public func toggleRegionBookmark(_ regionId: String) {
        if bookmarkedRegionIds.contains(regionId) {
            bookmarkedRegionIds.remove(regionId)
        } else {
            bookmarkedRegionIds.insert(regionId)
        }
    }

    public func addCustomerStack(_ stack: CustomerStack) {
        customerStacks.insert(stack, at: 0)
    }

    public func deleteCustomerStack(id: UUID) {
        customerStacks.removeAll { $0.id == id }
    }

    // MARK: - Smart Omni-Search Across Services, SLAs, Regions, AI Models & Updates

    public func omniSearch(_ rawQuery: String, limit: Int = 18) -> [OmniSearchHit] {
        let trimmed = rawQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return [] }
        let qLower = trimmed.lowercased()
        let normQ = SLACalculator.normalizeSearchToken(
            qLower
                .replacingOccurrences(of: "sla", with: "")
                .replacingOccurrences(of: "pricing", with: "")
                .replacingOccurrences(of: "cost", with: "")
        )

        var hits: [OmniSearchHit] = []

        // 1. Match Cloud Services
        for svc in catalog.services {
            let normName = SLACalculator.normalizeSearchToken(svc.name)
            let matchesName = svc.name.lowercased().contains(qLower)
                || (!normQ.isEmpty && (normName.contains(normQ) || normQ.contains(normName)))
                || svc.category.lowercased().contains(qLower)
                || svc.sla.headlineDisplay.lowercased().contains(qLower)
            if matchesName {
                hits.append(
                    OmniSearchHit(
                        id: "svc-\(svc.slug)",
                        kind: .service,
                        title: svc.name,
                        subtitle: "\(svc.category) • \(svc.isGlobal ? "Global" : "\(svc.regionCount) Regions") • \(svc.pricing.billingModel)",
                        badge: "🛡️ \(svc.sla.headlineDisplay)",
                        targetSlugOrId: svc.slug
                    )
                )
            }
        }

        // 2. Match Regions & GPU/Machine Capabilities
        for reg in catalog.regions {
            let hay = "\(reg.regionId) \(reg.regionName) \(reg.fullLocation) \(reg.subRegion) \(reg.gpus.joined(separator: " ")) \(reg.machineSeries.joined(separator: " "))".lowercased()
            if hay.contains(qLower) || (!normQ.isEmpty && hay.contains(normQ)) {
                hits.append(
                    OmniSearchHit(
                        id: "reg-\(reg.regionId)",
                        kind: .region,
                        title: "\(reg.regionName) (\(reg.regionId))",
                        subtitle: "\(reg.serviceCount) Services • \(reg.aiModelCount) AI Models • \(reg.pricing.tier)",
                        badge: String(format: "💰 %.2fx%@", reg.pricing.relativeComputeIndex, reg.isLowCo2 ? " 🌱" : ""),
                        targetSlugOrId: reg.regionId
                    )
                )
            }
        }

        // 3. Match AI & Foundation Models
        for model in catalog.models {
            let hay = "\(model.modelName) \(model.modelId) \(model.family) \(model.modality)".lowercased()
            if hay.contains(qLower) || (!normQ.isEmpty && hay.contains(normQ)) {
                hits.append(
                    OmniSearchHit(
                        id: "mod-\(model.modelId)",
                        kind: .model,
                        title: model.modelName,
                        subtitle: "\(model.family) • \(model.modality)",
                        badge: model.globalEndpoint ? "🌐 Global + \(model.regionCount)R" : "\(model.regionCount) Regions",
                        targetSlugOrId: model.modelId
                    )
                )
            }
        }

        // 4. Match Official Release Notes
        for note in catalog.releaseNotes {
            let hay = "\(note.productName) \(note.releaseType) \(note.summary)".lowercased()
            if hay.contains(qLower) {
                hits.append(
                    OmniSearchHit(
                        id: "rn-\(note.id)",
                        kind: .update,
                        title: "\(note.productName) — \(note.releaseType)",
                        subtitle: note.summary,
                        badge: note.date,
                        targetSlugOrId: note.serviceSlug ?? note.id
                    )
                )
            }
        }

        return Array(hits.prefix(limit))
    }

    public func handleSpotlightIdentifier(_ identifier: String) {
        if identifier.hasPrefix("service:") {
            deepLinkedServiceSlug = String(identifier.dropFirst("service:".count))
        } else if identifier.hasPrefix("region:") {
            deepLinkedRegionId = String(identifier.dropFirst("region:".count))
        }
    }

    // MARK: - Private Helpers

    private func applyCatalog(_ updated: MobileCatalog, state: DataSyncState) {
        self.catalog = updated
        self.syncState = state
        rebuildLookupCaches()
    }

    private func rebuildLookupCaches() {
        servicesBySlug = Dictionary(uniqueKeysWithValues: catalog.services.map { ($0.slug, $0) })
        servicesByName = Dictionary(uniqueKeysWithValues: catalog.services.map { ($0.name, $0) })
        regionsById = Dictionary(uniqueKeysWithValues: catalog.regions.map { ($0.regionId, $0) })
    }

    private func saveBookmarks() {
        UserDefaults.standard.set(Array(bookmarkedServiceSlugs), forKey: Self.svcBookmarksKey)
        UserDefaults.standard.set(Array(bookmarkedRegionIds), forKey: Self.regBookmarksKey)
    }

    private func saveCustomerStacks() {
        if let data = try? JSONEncoder().encode(customerStacks) {
            UserDefaults.standard.set(data, forKey: Self.stacksKey)
        }
    }

    private func indexCoreSpotlight() {
        #if os(iOS) && canImport(CoreSpotlight)
        guard CSSearchableIndex.isIndexingAvailable() else { return }
        var items: [CSSearchableItem] = []

        for svc in catalog.services.prefix(160) {
            let attrs = CSSearchableItemAttributeSet(contentType: .text)
            attrs.title = "\(svc.name) — SLA \(svc.sla.headlineDisplay)"
            attrs.contentDescription = "\(svc.category) • \(svc.isGlobal ? "Global" : "\(svc.regionCount) Google Cloud Regions") • Max downtime \(svc.sla.maxMonthlyDowntime) • \(svc.pricing.billingModel)"
            attrs.keywords = [svc.name, "Google Cloud", svc.category, "SLA", "Pricing", svc.slug]
            items.append(
                CSSearchableItem(
                    uniqueIdentifier: "service:\(svc.slug)",
                    domainIdentifier: "com.unofficial.googlecloudexplorer.services",
                    attributeSet: attrs
                )
            )
        }

        for reg in catalog.regions {
            let attrs = CSSearchableItemAttributeSet(contentType: .text)
            attrs.title = "\(reg.regionName) (\(reg.regionId)) — Google Cloud Region"
            attrs.contentDescription = String(
                format: "%d Services • %d AI Models • %.2fx Compute Cost Index%@",
                reg.serviceCount,
                reg.aiModelCount,
                reg.pricing.relativeComputeIndex,
                reg.isLowCo2 ? " • Low CO2" : ""
            )
            attrs.keywords = [reg.regionId, reg.regionName, reg.subRegion, "Google Cloud Region"]
            items.append(
                CSSearchableItem(
                    uniqueIdentifier: "region:\(reg.regionId)",
                    domainIdentifier: "com.unofficial.googlecloudexplorer.regions",
                    attributeSet: attrs
                )
            )
        }

        CSSearchableIndex.default().indexSearchableItems(items) { _ in }
        #endif
    }

    public static func defaultReferenceStacks() -> [CustomerStack] {
        [
            CustomerStack(
                name: "Global Mission-Critical FinTech Core",
                subtitle: "99.999% Multi-Region Active-Active Ledger + Serverless Edge",
                serviceSlugs: ["cloud-load-balancing", "cloud-armor", "cloud-run", "spanner", "cloud-kms"],
                targetRegionIds: ["us-central1", "us-east4", "europe-west1"],
                topologyMode: .dualActiveActive
            ),
            CustomerStack(
                name: "Enterprise GenAI & Agentic RAG Stack",
                subtitle: "Vertex AI Multimodal + AlloyDB ScaNN Vector + BigQuery Lakehouse",
                serviceSlugs: ["vertex-ai", "alloydb", "bigquery", "cloud-storage", "pub-sub"],
                targetRegionIds: ["us-central1", "europe-west4", "asia-south1"],
                topologyMode: .singleRegionSerial
            )
        ]
    }

    private static func emptyFallbackCatalog() -> MobileCatalog {
        MobileCatalog(
            meta: CatalogMeta(
                generatedAt: "Offline Bundle",
                generatedEpoch: 0,
                ttlSeconds: 86400,
                refreshPolicy: "Daily 24h Cache",
                counts: CatalogCounts(
                    totalServices: 0, regionalServices: 0, multiRegionServices: 0, globalServices: 0,
                    formalSlaServices: 0, highSla9999Services: 0, freeTierServices: 0,
                    availableRegions: 0, futureRegions: 0, totalZones: 0, gpuZones: 0,
                    lowCo2Regions: 0, aiModels: 0, aiModelFamilies: 0, discoveryApis: 0,
                    totalApiMethods: 0, edgePops: 0, cloudCdnPops: 0, mediaCdnPops: 0, releaseNotes: 0
                )
            ),
            regions: [],
            futureRegions: [],
            services: [],
            models: [],
            pops: PoPCatalog(edgePops: [], cloudCdnPops: [], mediaCdnPops: []),
            whatsNew: [],
            releaseNotes: [],
            etag: nil
        )
    }
}
