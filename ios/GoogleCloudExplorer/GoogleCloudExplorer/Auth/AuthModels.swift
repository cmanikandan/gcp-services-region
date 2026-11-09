import Foundation

// MARK: - Passwordless Mobile Auth & Builder Passport Models

public enum AuthProvider: String, Codable, CaseIterable, Identifiable, Sendable {
    case apple = "apple"
    case googlePKCE = "google_pkce"
    case passkey = "passkey"
    case magicHandle = "magic_handle"

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .apple: return "Sign in with Apple"
        case .googlePKCE: return "Google Identity (PKCE)"
        case .passkey: return "Device Passkey"
        case .magicHandle: return "Instant @Handle"
        }
    }

    public var protocolBadge: String {
        switch self {
        case .apple: return "OIDC + SHA256 Nonce"
        case .googlePKCE: return "OAuth 2.0 PKCE S256"
        case .passkey: return "CryptoKit P-256 Key"
        case .magicHandle: return "HS256 Bearer Session"
        }
    }

    public var systemImage: String {
        switch self {
        case .apple: return "apple.logo"
        case .googlePKCE: return "shield.checkered"
        case .passkey: return "person.badge.key.fill"
        case .magicHandle: return "sparkles"
        }
    }
}

public enum BuilderRoleVibe: String, Codable, CaseIterable, Identifiable, Sendable {
    case aiBuilder = "aiBuilder"
    case fiveNinesSRE = "fiveNinesSRE"
    case finOpsMaxi = "finOpsMaxi"
    case cloudArchitect = "cloudArchitect"

    public var id: String { rawValue }

    public var label: String {
        switch self {
        case .aiBuilder: return "GenAI Main Character 🤖"
        case .fiveNinesSRE: return "Five-Nines Wizard 🛡️"
        case .finOpsMaxi: return "FinOps Maximizer 💸"
        case .cloudArchitect: return "Multi-Region Architect 🌐"
        }
    }

    public var shortChip: String {
        switch self {
        case .aiBuilder: return "🤖 GenAI"
        case .fiveNinesSRE: return "🛡️ 5-Nines"
        case .finOpsMaxi: return "💸 FinOps"
        case .cloudArchitect: return "🌐 Infra"
        }
    }
}

public struct MobileUserProfile: Codable, Sendable, Equatable, Hashable {
    public let userId: String
    public var handle: String
    public var displayName: String
    public var email: String
    public var provider: String
    public var avatarEmoji: String
    public var roleVibe: String
    public let createdAt: String
    public var xpPoints: Int
    public var builderLevel: String

    public init(
        userId: String,
        handle: String,
        displayName: String,
        email: String,
        provider: String,
        avatarEmoji: String,
        roleVibe: String,
        createdAt: String,
        xpPoints: Int,
        builderLevel: String
    ) {
        self.userId = userId
        self.handle = handle
        self.displayName = displayName
        self.email = email
        self.provider = provider
        self.avatarEmoji = avatarEmoji
        self.roleVibe = roleVibe
        self.createdAt = createdAt
        self.xpPoints = xpPoints
        self.builderLevel = builderLevel
    }

    public var resolvedProvider: AuthProvider {
        AuthProvider(rawValue: provider) ?? .passkey
    }

    public var resolvedRoleVibe: BuilderRoleVibe {
        BuilderRoleVibe(rawValue: roleVibe) ?? .aiBuilder
    }

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case handle
        case displayName = "display_name"
        case email
        case provider
        case avatarEmoji = "avatar_emoji"
        case roleVibe = "role_vibe"
        case createdAt = "created_at"
        case xpPoints = "xp_points"
        case builderLevel = "builder_level"
    }
}

public struct AuthTokenPair: Codable, Sendable, Equatable {
    public let accessToken: String
    public let refreshToken: String
    public let tokenType: String
    public let expiresIn: Int
    public let expiresAt: Int

    public init(
        accessToken: String,
        refreshToken: String,
        tokenType: String = "Bearer",
        expiresIn: Int = 3600,
        expiresAt: Int
    ) {
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        self.tokenType = tokenType
        self.expiresIn = expiresIn
        self.expiresAt = expiresAt
    }

    public var isExpired: Bool {
        Int(Date().timeIntervalSince1970) >= (expiresAt - 30)
    }

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
        case expiresAt = "expires_at"
    }
}

public struct CloudUserVault: Codable, Sendable {
    public var bookmarkedServices: [String]
    public var bookmarkedRegions: [String]
    public var customerStacks: [CustomerStack]
    public var vibeTheme: String
    public var updatedEpoch: Int

    public init(
        bookmarkedServices: [String],
        bookmarkedRegions: [String],
        customerStacks: [CustomerStack],
        vibeTheme: String,
        updatedEpoch: Int
    ) {
        self.bookmarkedServices = bookmarkedServices
        self.bookmarkedRegions = bookmarkedRegions
        self.customerStacks = customerStacks
        self.vibeTheme = vibeTheme
        self.updatedEpoch = updatedEpoch
    }

    enum CodingKeys: String, CodingKey {
        case bookmarkedServices = "bookmarked_services"
        case bookmarkedRegions = "bookmarked_regions"
        case customerStacks = "customer_stacks"
        case vibeTheme = "vibe_theme"
        case updatedEpoch = "updated_epoch"
    }
}

public struct AuthChallengeResponse: Codable, Sendable {
    public let challengeId: String
    public let nonce: String
    public let expiresAt: Int

    enum CodingKeys: String, CodingKey {
        case challengeId = "challenge_id"
        case nonce
        case expiresAt = "expires_at"
    }
}

public struct AuthSessionResponse: Codable, Sendable {
    public let user: MobileUserProfile
    public let tokens: AuthTokenPair
    public let vault: CloudUserVault
}

public struct VaultSyncResponse: Codable, Sendable {
    public let user: MobileUserProfile
    public let vault: CloudUserVault
}

public struct StoredKeychainSession: Codable, Sendable {
    public var user: MobileUserProfile
    public var tokens: AuthTokenPair
    public var passkeyPublicKeyB64: String?
    public var isOfflineLocalSession: Bool

    public init(
        user: MobileUserProfile,
        tokens: AuthTokenPair,
        passkeyPublicKeyB64: String? = nil,
        isOfflineLocalSession: Bool = false
    ) {
        self.user = user
        self.tokens = tokens
        self.passkeyPublicKeyB64 = passkeyPublicKeyB64
        self.isOfflineLocalSession = isOfflineLocalSession
    }
}
