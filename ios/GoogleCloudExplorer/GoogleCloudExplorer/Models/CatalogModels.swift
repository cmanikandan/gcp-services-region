import Foundation
import CoreLocation

// MARK: - Root Mobile Catalog Payload

public struct MobileCatalog: Codable, Sendable {
    public let meta: CatalogMeta
    public let regions: [CloudRegion]
    public let futureRegions: [FutureRegion]
    public let services: [CloudService]
    public let models: [AIModel]
    public let pops: PoPCatalog
    public let whatsNew: [WhatsNewItem]
    public let releaseNotes: [ReleaseNoteItem]
    public let etag: String?

    enum CodingKeys: String, CodingKey {
        case meta
        case regions
        case futureRegions = "future_regions"
        case services
        case models
        case pops
        case whatsNew = "whats_new"
        case releaseNotes = "release_notes"
        case etag
    }
}

public struct CatalogMeta: Codable, Sendable, Hashable {
    public let generatedAt: String
    public let generatedEpoch: Int
    public let ttlSeconds: Int
    public let refreshPolicy: String
    public let counts: CatalogCounts

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case generatedEpoch = "generated_epoch"
        case ttlSeconds = "ttl_seconds"
        case refreshPolicy = "refresh_policy"
        case counts
    }
}

public struct CatalogCounts: Codable, Sendable, Hashable {
    public let totalServices: Int
    public let regionalServices: Int
    public let multiRegionServices: Int
    public let globalServices: Int
    public let formalSlaServices: Int?
    public let highSla9999Services: Int?
    public let freeTierServices: Int?
    public let availableRegions: Int
    public let futureRegions: Int
    public let totalZones: Int
    public let gpuZones: Int
    public let lowCo2Regions: Int
    public let aiModels: Int
    public let aiModelFamilies: Int
    public let discoveryApis: Int
    public let totalApiMethods: Int
    public let edgePops: Int
    public let cloudCdnPops: Int
    public let mediaCdnPops: Int
    public let releaseNotes: Int?

    enum CodingKeys: String, CodingKey {
        case totalServices = "total_services"
        case regionalServices = "regional_services"
        case multiRegionServices = "multi_region_services"
        case globalServices = "global_services"
        case formalSlaServices = "formal_sla_services"
        case highSla9999Services = "high_sla_9999_services"
        case freeTierServices = "free_tier_services"
        case availableRegions = "available_regions"
        case futureRegions = "future_regions"
        case totalZones = "total_zones"
        case gpuZones = "gpu_zones"
        case lowCo2Regions = "low_co2_regions"
        case aiModels = "ai_models"
        case aiModelFamilies = "ai_model_families"
        case discoveryApis = "discovery_apis"
        case totalApiMethods = "total_api_methods"
        case edgePops = "edge_pops"
        case cloudCdnPops = "cloud_cdn_pops"
        case mediaCdnPops = "media_cdn_pops"
        case releaseNotes = "release_notes"
    }

    public var totalEdgeLocations: Int {
        edgePops + cloudCdnPops + mediaCdnPops
    }
}

// MARK: - Cloud Services, SLA & Service Pricing

public struct CloudService: Codable, Sendable, Identifiable, Hashable {
    public var id: String { slug }
    public let name: String
    public let slug: String
    public let category: String
    public let url: String
    public let scope: String
    public let isGlobal: Bool
    public let regions: [String]
    public let regionCount: Int
    public let coveragePct: Double
    public let multiRegions: [String]
    public let apiNames: [String]
    public let totalApiMethods: Int
    public let sla: ServiceSLA
    public let pricing: ServicePricing

    enum CodingKeys: String, CodingKey {
        case name, slug, category, url, scope, regions, sla, pricing
        case isGlobal = "is_global"
        case regionCount = "region_count"
        case coveragePct = "coverage_pct"
        case multiRegions = "multi_regions"
        case apiNames = "api_names"
        case totalApiMethods = "total_api_methods"
    }
}

public struct ServiceSLA: Codable, Sendable, Hashable {
    public let hasFormalSla: Bool
    public let headlineUptimePct: Double?
    public let headlineDisplay: String
    public let maxMonthlyDowntime: String
    public let slaUrl: String
    public let tiers: [SLATier]
    public let creditSchedule: [CreditTier]
    public let haRequirements: [String]

    enum CodingKeys: String, CodingKey {
        case hasFormalSla = "has_formal_sla"
        case headlineUptimePct = "headline_uptime_pct"
        case headlineDisplay = "headline_display"
        case maxMonthlyDowntime = "max_monthly_downtime"
        case slaUrl = "sla_url"
        case tiers
        case creditSchedule = "credit_schedule"
        case haRequirements = "ha_requirements"
    }
}

public struct SLATier: Codable, Sendable, Identifiable, Hashable {
    public var id: String { "\(tierName)-\(uptimeDisplay)" }
    public let tierName: String
    public let uptimePct: Double
    public let uptimeDisplay: String
    public let maxMonthlyDowntime: String
    public let maxAnnualDowntime: String
    public let topology: String

    enum CodingKeys: String, CodingKey {
        case tierName = "tier_name"
        case uptimePct = "uptime_pct"
        case uptimeDisplay = "uptime_display"
        case maxMonthlyDowntime = "max_monthly_downtime"
        case maxAnnualDowntime = "max_annual_downtime"
        case topology
    }
}

public struct CreditTier: Codable, Sendable, Identifiable, Hashable {
    public var id: String { threshold }
    public let threshold: String
    public let creditPct: String

    enum CodingKeys: String, CodingKey {
        case threshold
        case creditPct = "credit_pct"
    }
}

public struct ServicePricing: Codable, Sendable, Hashable {
    public let pricingUrl: String
    public let billingModel: String
    public let primaryUnits: String
    public let hasFreeTier: Bool
    public let freeTierNote: String
    public let cudSupport: String
    public let spotOrBatchDiscount: Bool
    public let discountNote: String
    public let costDrivers: [String]

    enum CodingKeys: String, CodingKey {
        case pricingUrl = "pricing_url"
        case billingModel = "billing_model"
        case primaryUnits = "primary_units"
        case hasFreeTier = "has_free_tier"
        case freeTierNote = "free_tier_note"
        case cudSupport = "cud_support"
        case spotOrBatchDiscount = "spot_or_batch_discount"
        case discountNote = "discount_note"
        case costDrivers = "cost_drivers"
    }
}

// MARK: - Cloud Regions, Future Regions & PoPs

public struct CloudRegion: Codable, Sendable, Identifiable, Hashable {
    public var id: String { regionId }
    public let regionId: String
    public let regionName: String
    public let displayName: String
    public let fullLocation: String
    public let subRegion: String
    public let status: String
    public let isLowCo2: Bool
    public let lat: Double
    public let lng: Double
    public let dateLaunched: String
    public let zones: [String]
    public let zoneCount: Int
    public let machineSeries: [String]
    public let cpus: [String]
    public let gpus: [String]
    public let confidentialOptions: [String]
    public let services: [String]
    public let serviceCount: Int
    public let aiModelCount: Int
    public let pricing: RegionPricing

    public var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }

    enum CodingKeys: String, CodingKey {
        case regionId = "region_id"
        case regionName = "region_name"
        case displayName = "display_name"
        case fullLocation = "full_location"
        case subRegion = "sub_region"
        case status
        case isLowCo2 = "is_low_co2"
        case lat, lng
        case dateLaunched = "date_launched"
        case zones
        case zoneCount = "zone_count"
        case machineSeries = "machine_series"
        case cpus, gpus
        case confidentialOptions = "confidential_options"
        case services
        case serviceCount = "service_count"
        case aiModelCount = "ai_model_count"
        case pricing
    }
}

public struct RegionPricing: Codable, Sendable, Hashable {
    public let tier: String
    public let relativeComputeIndex: Double
    public let relativeStorageIndex: Double
    public let deltaVsBaseline: String
    public let interRegionEgressBand: String
    public let cud1yDiscountPct: Int
    public let cud3yDiscountPct: Int

    enum CodingKeys: String, CodingKey {
        case tier
        case relativeComputeIndex = "relative_compute_index"
        case relativeStorageIndex = "relative_storage_index"
        case deltaVsBaseline = "delta_vs_baseline"
        case interRegionEgressBand = "inter_region_egress_band"
        case cud1yDiscountPct = "cud_1y_discount_pct"
        case cud3yDiscountPct = "cud_3y_discount_pct"
    }
}

public struct FutureRegion: Codable, Sendable, Identifiable, Hashable {
    public var id: String { regionId }
    public let regionName: String
    public let regionId: String
    public let subRegion: String
    public let status: String
    public let lat: Double
    public let lng: Double
    public let dateLaunched: String

    public var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }

    enum CodingKeys: String, CodingKey {
        case regionName = "region_name"
        case regionId = "region_id"
        case subRegion = "sub_region"
        case status, lat, lng
        case dateLaunched = "date_launched"
    }
}

public struct PoPCatalog: Codable, Sendable, Hashable {
    public let edgePops: [EdgePoP]
    public let cloudCdnPops: [EdgePoP]
    public let mediaCdnPops: [EdgePoP]

    enum CodingKeys: String, CodingKey {
        case edgePops = "edge_pops"
        case cloudCdnPops = "cloud_cdn_pops"
        case mediaCdnPops = "media_cdn_pops"
    }
}

public struct EdgePoP: Codable, Sendable, Identifiable, Hashable {
    public var id: String { "\(label)-\(lat)-\(lng)" }
    public let lat: Double
    public let lng: Double
    public let label: String

    public var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }
}

// MARK: - AI & Foundation Models

public struct AIModel: Codable, Sendable, Identifiable, Hashable {
    public var id: String { modelId }
    public let modelId: String
    public let modelName: String
    public let family: String
    public let modality: String
    public let stage: String
    public let globalEndpoint: Bool
    public let multiRegions: [String]
    public let regions: [String]
    public let regionCount: Int
    public let url: String

    enum CodingKeys: String, CodingKey {
        case modelId = "model_id"
        case modelName = "model_name"
        case family, modality, stage
        case globalEndpoint = "global_endpoint"
        case multiRegions = "multi_regions"
        case regions
        case regionCount = "region_count"
        case url
    }
}

// MARK: - What's New & Official Release Notes

public struct WhatsNewItem: Codable, Sendable, Identifiable, Hashable {
    public var id: String { "\(date)-\(type)-\(service)-\(regionId)" }
    public let date: String
    public let type: String
    public let service: String
    public let regionId: String
    public let regionName: String
    public let details: String

    enum CodingKeys: String, CodingKey {
        case date, type, service
        case regionId = "region_id"
        case regionName = "region_name"
        case details
    }
}

public struct ReleaseNoteItem: Codable, Sendable, Identifiable, Hashable {
    public let id: String
    public let date: String
    public let releaseType: String
    public let productName: String
    public let serviceSlug: String?
    public let category: String
    public let summary: String
    public let url: String

    enum CodingKeys: String, CodingKey {
        case id, date
        case releaseType = "release_type"
        case productName = "product_name"
        case serviceSlug = "service_slug"
        case category, summary, url
    }
}

// MARK: - Customer Architecture Blueprint Stack

public struct CustomerStack: Codable, Sendable, Identifiable, Hashable {
    public var id: UUID
    public var name: String
    public var subtitle: String
    public var serviceSlugs: [String]
    public var targetRegionIds: [String]
    public var topologyMode: StackTopologyMode

    public init(
        id: UUID = UUID(),
        name: String,
        subtitle: String,
        serviceSlugs: [String],
        targetRegionIds: [String],
        topologyMode: StackTopologyMode = .dualActiveActive
    ) {
        self.id = id
        self.name = name
        self.subtitle = subtitle
        self.serviceSlugs = serviceSlugs
        self.targetRegionIds = targetRegionIds
        self.topologyMode = topologyMode
    }
}

public enum StackTopologyMode: String, Codable, Sendable, CaseIterable, Identifiable {
    case singleRegionSerial = "Single-Region Serial"
    case dualActiveActive = "Dual-Region Active-Active"
    case triRegionQuorum = "Tri-Region Quorum"

    public var id: String { rawValue }

    public var shortLabel: String {
        switch self {
        case .singleRegionSerial: return "Serial (1R)"
        case .dualActiveActive: return "Active-Active (2R)"
        case .triRegionQuorum: return "Multi-Region (3R)"
        }
    }

    public var formulaCaption: String {
        switch self {
        case .singleRegionSerial: return "Critical Path: R₁ × R₂ × … × Rₙ"
        case .dualActiveActive: return "Redundant Stack: 1 − (1 − R_stack)²"
        case .triRegionQuorum: return "Triple Redundancy: 1 − (1 − R_stack)³"
        }
    }
}
