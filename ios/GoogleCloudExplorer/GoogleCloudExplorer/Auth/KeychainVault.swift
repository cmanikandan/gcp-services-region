import Foundation
import CryptoKit
#if canImport(Security)
import Security
#endif

// MARK: - RFC 7636 OAuth 2.0 PKCE S256 & OIDC Nonce Generator

public enum PKCEGenerator {
    public struct PKCEPair: Sendable {
        public let codeVerifier: String
        public let codeChallenge: String
        public let method: String = "S256"
    }

    public static func generateS256Pair() -> PKCEPair {
        var randomBytes = [UInt8](repeating: 0, count: 32)
        for idx in randomBytes.indices {
            randomBytes[idx] = UInt8.random(in: 0...255)
        }
        let verifier = base64URLEncode(Data(randomBytes))
        let digest = SHA256.hash(data: Data(verifier.utf8))
        let challenge = base64URLEncode(Data(digest))
        return PKCEPair(codeVerifier: verifier, codeChallenge: challenge)
    }

    public static func generateOIDCNonce() -> (rawNonce: String, sha256Hex: String) {
        var bytes = [UInt8](repeating: 0, count: 24)
        for idx in bytes.indices {
            bytes[idx] = UInt8.random(in: 0...255)
        }
        let raw = base64URLEncode(Data(bytes))
        let hashed = SHA256.hash(data: Data(raw.utf8))
            .map { String(format: "%02x", $0) }
            .joined()
        return (raw, hashed)
    }

    public static func base64URLEncode(_ data: Data) -> String {
        data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

// MARK: - CryptoKit P-256 Device Passkey Signer

public enum DevicePasskeySigner {
    private static let passkeyAccount = "gce.passkey.p256.privatekey"

    public static func loadOrCreatePublicKeyAndSign(nonce: String) -> (publicKeyB64: String, signatureB64: String) {
        let privateKey: P256.Signing.PrivateKey
        if let rawData = KeychainVault.readRawData(account: passkeyAccount),
           let restored = try? P256.Signing.PrivateKey(rawRepresentation: rawData) {
            privateKey = restored
        } else {
            let fresh = P256.Signing.PrivateKey()
            KeychainVault.saveRawData(fresh.rawRepresentation, account: passkeyAccount)
            privateKey = fresh
        }

        let pubB64 = privateKey.publicKey.rawRepresentation.base64EncodedString()
        let sigData = (try? privateKey.signature(for: Data(nonce.utf8)).derRepresentation) ?? Data()
        return (pubB64, sigData.base64EncodedString())
    }
}

// MARK: - Hardware-Backed iOS Keychain Session Vault

public enum KeychainVault {
    private static let serviceName = "com.unofficial.googlecloudexplorer.authvault"
    private static let sessionAccount = "gce.mobile.session.v1"

    public static func saveSession(_ session: StoredKeychainSession) {
        guard let encoded = try? JSONEncoder().encode(session) else { return }
        saveRawData(encoded, account: sessionAccount)
    }

    public static func loadSession() -> StoredKeychainSession? {
        guard let data = readRawData(account: sessionAccount) else { return nil }
        return try? JSONDecoder().decode(StoredKeychainSession.self, from: data)
    }

    public static func deleteSession() {
        deleteRawData(account: sessionAccount)
    }

    public static func wipeAllAuthMaterial() {
        deleteRawData(account: sessionAccount)
        deleteRawData(account: "gce.passkey.p256.privatekey")
    }

    public static func saveRawData(_ data: Data, account: String) {
        #if canImport(Security)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)

        var insert = query
        insert[kSecValueData as String] = data
        insert[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(insert as CFDictionary, nil)
        #endif
    }

    public static func readRawData(account: String) -> Data? {
        #if canImport(Security)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else {
            return nil
        }
        return data
        #else
        return nil
        #endif
    }

    public static func deleteRawData(account: String) {
        #if canImport(Security)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
        #endif
    }
}
