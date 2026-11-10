import Foundation
import Observation

// MARK: - Gemini Interactions API Models (v1beta/interactions)

public enum GeminiModelOption: String, CaseIterable, Identifiable, Sendable {
    case gemini38Flash = "gemini-3.8-flash"
    case gemini35FlashLite = "gemini-3.5-flash-lite"
    case gemini4Argon = "gemini-4-argon"

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .gemini38Flash: return "Gemini 3.8 Flash"
        case .gemini35FlashLite: return "Gemini 3.5 Flash-Lite"
        case .gemini4Argon: return "Gemini 4 Argon"
        }
    }

    public var badgeSubtitle: String {
        switch self {
        case .gemini38Flash: return "Balanced • 1M Context"
        case .gemini35FlashLite: return "Ultra-Fast • High Throughput"
        case .gemini4Argon: return "Frontier Deep Reasoning"
        }
    }
}

public struct GeminiChatTurn: Identifiable, Sendable, Equatable {
    public enum Role: String, Sendable {
        case user
        case assistant
    }

    public let id: UUID
    public let role: Role
    public let text: String
    public let modelId: String?
    public let interactionId: String?
    public let totalTokens: Int?
    public let thoughtTokens: Int?
    public let timestamp: Date
    public let isOfflineFallback: Bool

    public init(
        id: UUID = UUID(),
        role: Role,
        text: String,
        modelId: String? = nil,
        interactionId: String? = nil,
        totalTokens: Int? = nil,
        thoughtTokens: Int? = nil,
        timestamp: Date = Date(),
        isOfflineFallback: Bool = false
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.modelId = modelId
        self.interactionId = interactionId
        self.totalTokens = totalTokens
        self.thoughtTokens = thoughtTokens
        self.timestamp = timestamp
        self.isOfflineFallback = isOfflineFallback
    }
}

// MARK: - Wire Codable Payloads for Gemini Interactions API

private struct GeminiInteractionRequest: Encodable {
    let model: String
    let input: String
    let systemInstruction: String
    let previousInteractionId: String?

    enum CodingKeys: String, CodingKey {
        case model
        case input
        case systemInstruction = "system_instruction"
        case previousInteractionId = "previous_interaction_id"
    }
}

private struct GeminiInteractionResponse: Decodable {
    struct StepContent: Decodable {
        let type: String?
        let text: String?
    }

    struct Step: Decodable {
        let type: String
        let summary: String?
        let content: [StepContent]?
    }

    struct Usage: Decodable {
        let totalTokens: Int?
        let totalInputTokens: Int?
        let totalOutputTokens: Int?
        let totalThoughtTokens: Int?

        enum CodingKeys: String, CodingKey {
            case totalTokens = "total_tokens"
            case totalInputTokens = "total_input_tokens"
            case totalOutputTokens = "total_output_tokens"
            case totalThoughtTokens = "total_thought_tokens"
        }
    }

    let id: String?
    let model: String?
    let status: String?
    let steps: [Step]?
    let usage: Usage?

    var outputText: String {
        guard let steps else { return "" }
        var parts: [String] = []
        for step in steps where step.type == "model_output" {
            for item in step.content ?? [] {
                if item.type == "text" || item.type == nil, let txt = item.text, !txt.isEmpty {
                    parts.append(txt)
                }
            }
        }
        return parts.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

// MARK: - Main-Actor Observable Gemini Cloud Architect Copilot

@Observable
@MainActor
public final class GeminiCopilotService {
    public var selectedModel: GeminiModelOption = .gemini38Flash
    public private(set) var messages: [GeminiChatTurn] = []
    public private(set) var isGenerating: Bool = false
    public private(set) var lastInteractionId: String?
    public private(set) var lastErrorMessage: String?
    public private(set) var apiKeyConfigured: Bool = false
    public private(set) var maskedKeyPreview: String = "Not Configured"

    private static let interactionsEndpoint = URL(string: "https://generativelanguage.googleapis.com/v1beta/interactions")!

    public init() {
        bootstrapAPIKeyIfNeeded()
        seedWelcomeTurn()
    }

    public func bootstrapAPIKeyIfNeeded() {
        if let plistKey = (Bundle.main.object(forInfoDictionaryKey: "GEMINI_API_KEY") as? String)?
            .trimmingCharacters(in: .whitespacesAndNewlines),
           !plistKey.isEmpty,
           !plistKey.hasPrefix("$(") {
            KeychainVault.saveGeminiAPIKey(plistKey)
            updateKeyStatus(plistKey)
            return
        }

        if let existing = KeychainVault.loadGeminiAPIKey(), !existing.isEmpty {
            updateKeyStatus(existing)
            return
        }

        if let envKey = ProcessInfo.processInfo.environment["GEMINI_API_KEY"]?
            .trimmingCharacters(in: .whitespacesAndNewlines),
           !envKey.isEmpty,
           !envKey.hasPrefix("$(") {
            KeychainVault.saveGeminiAPIKey(envKey)
            updateKeyStatus(envKey)
            return
        }

        updateKeyStatus(nil)
    }

    public func saveAPIKey(_ newKey: String) {
        let trimmed = newKey.trimmingCharacters(in: .whitespacesAndNewlines)
        KeychainVault.saveGeminiAPIKey(trimmed)
        updateKeyStatus(trimmed.isEmpty ? nil : trimmed)
        lastErrorMessage = nil
    }

    public func clearConversation() {
        lastInteractionId = nil
        lastErrorMessage = nil
        messages.removeAll()
        seedWelcomeTurn()
    }

    public func askCopilot(prompt: String, store: CatalogStore) async {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isGenerating else { return }

        lastErrorMessage = nil
        messages.append(GeminiChatTurn(role: .user, text: trimmed))
        isGenerating = true
        defer { isGenerating = false }

        let systemInstruction = buildGroundedSystemInstruction(for: trimmed, store: store)

        guard let apiKey = KeychainVault.loadGeminiAPIKey(), !apiKey.isEmpty else {
            let fallback = buildOfflineGroundedResponse(for: trimmed, store: store)
            messages.append(
                GeminiChatTurn(
                    role: .assistant,
                    text: fallback,
                    modelId: "Offline Catalog Engine",
                    isOfflineFallback: true
                )
            )
            return
        }

        do {
            let response = try await performInteractionCall(
                apiKey: apiKey,
                model: selectedModel.rawValue,
                input: trimmed,
                systemInstruction: systemInstruction,
                previousInteractionId: lastInteractionId
            )

            let text = response.outputText.isEmpty
                ? buildOfflineGroundedResponse(for: trimmed, store: store)
                : response.outputText

            lastInteractionId = response.id
            messages.append(
                GeminiChatTurn(
                    role: .assistant,
                    text: text,
                    modelId: response.model ?? selectedModel.rawValue,
                    interactionId: response.id,
                    totalTokens: response.usage?.totalTokens,
                    thoughtTokens: response.usage?.totalThoughtTokens,
                    isOfflineFallback: false
                )
            )
        } catch {
            lastErrorMessage = error.localizedDescription
            let fallback = buildOfflineGroundedResponse(for: trimmed, store: store)
            messages.append(
                GeminiChatTurn(
                    role: .assistant,
                    text: "\(fallback)\n\n*(Note: Live Gemini API request encountered an error: \(error.localizedDescription) — answered using grounded local Google Cloud catalog.)*",
                    modelId: "Offline Catalog Fallback",
                    isOfflineFallback: true
                )
            )
        }
    }

    // MARK: - Direct Audit Helper for SLA & FinOps Studio

    public func auditArchitectureStack(
        services: [CloudService],
        topology: StackTopologyMode,
        slaResult: CompositeSLAResult,
        primaryRegion: CloudRegion?,
        secondaryRegion: CloudRegion?,
        monthlySpendUSD: Double,
        commitment: CommitmentTier,
        store: CatalogStore
    ) async -> GeminiChatTurn {
        let svcSummary = services.map { "\($0.name) (SLA \($0.sla.headlineDisplay), \($0.regionCount) regions)" }.joined(separator: ", ")
        let r1Text = primaryRegion.map { "\($0.regionId) (\($0.regionName), \(String(format: "%.2fx", $0.pricing.relativeComputeIndex)) compute, Low CO2: \($0.isLowCo2))" } ?? "us-central1"
        let r2Text = secondaryRegion.map { "\($0.regionId) (\($0.regionName), \(String(format: "%.2fx", $0.pricing.relativeComputeIndex)) compute, Low CO2: \($0.isLowCo2))" } ?? "asia-south1"

        let auditPrompt = """
        Audit this Google Cloud workload stack and provide a concise, actionable architectural review (4 short bullet points covering: 1. Composite SLA & Bottleneck mitigation, 2. Primary vs DR regional service/model parity, 3. FinOps & CUD optimization, 4. High-Availability prerequisites):
        - Topology: \(topology.rawValue)
        - Critical-Path Services: \(svcSummary)
        - Composite Uptime: \(slaResult.formattedUptime) (Max monthly downtime: \(slaResult.formattedMonthlyDowntime), weakest link: \(slaResult.weakestServiceName ?? "None"))
        - Primary Region: \(r1Text)
        - Secondary / DR Region: \(r2Text)
        - Baseline Spend: $\(Int(monthlySpendUSD))/mo on \(commitment.rawValue)
        """

        let sys = buildGroundedSystemInstruction(for: auditPrompt, store: store)

        if let apiKey = KeychainVault.loadGeminiAPIKey(), !apiKey.isEmpty {
            if let resp = try? await performInteractionCall(
                apiKey: apiKey,
                model: selectedModel.rawValue,
                input: auditPrompt,
                systemInstruction: sys,
                previousInteractionId: nil
            ), !resp.outputText.isEmpty {
                return GeminiChatTurn(
                    role: .assistant,
                    text: resp.outputText,
                    modelId: resp.model ?? selectedModel.rawValue,
                    interactionId: resp.id,
                    totalTokens: resp.usage?.totalTokens,
                    thoughtTokens: resp.usage?.totalThoughtTokens,
                    isOfflineFallback: false
                )
            }
        }

        return GeminiChatTurn(
            role: .assistant,
            text: buildOfflineGroundedResponse(for: auditPrompt, store: store),
            modelId: "Offline Catalog Engine",
            isOfflineFallback: true
        )
    }

    // MARK: - Private Network & Grounding Engine

    private func performInteractionCall(
        apiKey: String,
        model: String,
        input: String,
        systemInstruction: String,
        previousInteractionId: String?
    ) async throws -> GeminiInteractionResponse {
        var request = URLRequest(url: Self.interactionsEndpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = 28.0
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "x-goog-api-key")

        let payload = GeminiInteractionRequest(
            model: model,
            input: input,
            systemInstruction: systemInstruction,
            previousInteractionId: previousInteractionId
        )
        request.httpBody = try JSONEncoder().encode(payload)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        guard (200..<300).contains(http.statusCode) else {
            let errBody = String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"
            throw NSError(
                domain: "GeminiCopilotService",
                code: http.statusCode,
                userInfo: [NSLocalizedDescriptionKey: "Gemini API HTTP \(http.statusCode): \(errBody.prefix(180))"]
            )
        }

        return try JSONDecoder().decode(GeminiInteractionResponse.self, from: data)
    }

    private func buildGroundedSystemInstruction(for query: String, store: CatalogStore) -> String {
        let counts = store.catalog.meta.counts
        let hits = store.omniSearch(query, limit: 8)
        let hitContext = hits.isEmpty
            ? "No direct keyword matches; use catalog totals and top regional/SLA facts."
            : hits.map { "• [\($0.kind.rawValue)] \($0.title): \($0.subtitle) (\($0.badge))" }.joined(separator: "\n")

        let pinnedSvcs = store.bookmarkedServiceSlugs.sorted().joined(separator: ", ")
        let pinnedRegs = store.bookmarkedRegionIds.sorted().joined(separator: ", ")

        return """
        You are the Gemini Google Cloud Architect Copilot inside the unofficial Google Cloud Explorer iOS & iPadOS app.
        Rules:
        1. Always write "Google Cloud" (never use the abbreviation "G" + "C" + "P").
        2. Keep answers concise, crisp, and mobile-friendly using clean markdown bullets, exact region IDs (e.g., us-central1, asia-south1, europe-west4), SLA uptime percentages, monthly downtime budgets, and FinOps cost multipliers.
        3. Ground your response in the live catalog snapshot (\(store.catalog.meta.generatedAt)):
           - \(counts.totalServices) Google Cloud Services (\(counts.formalSlaServices ?? 149) with formal SLAs, \(counts.highSla9999Services ?? 41) at >=99.99% uptime, \(counts.freeTierServices ?? 87) with Free Tier).
           - \(counts.availableRegions) Active Google Cloud Regions (\(counts.lowCo2Regions) Low CO2 regions, \(counts.totalZones) zones, \(counts.gpuZones) GPU zones) + \(counts.futureRegions) announced future regions.
           - \(counts.aiModels) AI & Foundation Models across \(counts.aiModelFamilies) model families.
           - User's pinned services: \(pinnedSvcs) | Pinned regions: \(pinnedRegs).
        4. Relevant catalog matches for this query:
        \(hitContext)
        """
    }

    private func buildOfflineGroundedResponse(for query: String, store: CatalogStore) -> String {
        let hits = store.omniSearch(query, limit: 5)
        if !hits.isEmpty {
            let bullets = hits.map { "• **\($0.title)** (\($0.badge)): \($0.subtitle)" }.joined(separator: "\n")
            return """
            **Grounded Google Cloud Catalog Summary (\(store.catalog.meta.generatedAt)):**
            \(bullets)

            • **Tip:** Open the **SLA & Cost** tab to simulate Multi-Region Active-Active composite uptime or compare 1Y/3Y CUD pricing across all \(store.catalog.regions.count) active Google Cloud regions.
            """
        }
        let counts = store.catalog.meta.counts
        return """
        **Google Cloud Explorer Catalog Snapshot (\(store.catalog.meta.generatedAt)):**
        • **\(counts.totalServices) Google Cloud Services** across \(counts.availableRegions) active regions (\(counts.lowCo2Regions) Low CO₂ 🌱 regions).
        • **\(counts.formalSlaServices ?? 149) Formal SLAs** (\(counts.highSla9999Services ?? 41) services with ≥ 99.99% uptime, led by Cloud Spanner Multi-Region at 99.999%).
        • **\(counts.aiModels) AI & Foundation Models** across \(counts.aiModelFamilies) families and \(counts.gpuZones) GPU-enabled zones.
        """
    }

    private func updateKeyStatus(_ rawKey: String?) {
        guard let key = rawKey, key.count >= 10 else {
            apiKeyConfigured = false
            maskedKeyPreview = "Not Configured"
            return
        }
        apiKeyConfigured = true
        let prefix = key.prefix(7)
        let suffix = key.suffix(4)
        maskedKeyPreview = "\(prefix)…\(suffix)"
    }

    private func seedWelcomeTurn() {
        messages = [
            GeminiChatTurn(
                role: .assistant,
                text: "Hey Builder ⚡ I'm your **Gemini 3.8 Google Cloud Architect Copilot**. Ask me to compare service SLAs, design a 99.999% Multi-Region stack, find the lowest-cost Low CO₂ 🌱 region with H100 GPUs, or audit your FinOps CUD spend!",
                modelId: selectedModel.rawValue
            )
        ]
    }
}
