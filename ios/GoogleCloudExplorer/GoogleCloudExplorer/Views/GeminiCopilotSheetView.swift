import SwiftUI

// MARK: - Gen Z Gemini 3.8 Cloud Architect Copilot Studio Sheet

public struct GeminiCopilotSheetView: View {
    @Bindable var store: CatalogStore
    @Bindable var copilot: GeminiCopilotService
    public var initialPrompt: String?

    @Environment(\.dismiss) private var dismiss
    @State private var draftPrompt: String = ""
    @State private var showingKeyEditor: Bool = false
    @State private var draftAPIKey: String = ""
    @State private var didRunInitialPrompt: Bool = false

    private let starterChips: [(label: String, prompt: String)] = [
        ("🛡️ Spanner vs AlloyDB SLA", "Compare Cloud Spanner vs AlloyDB SLA tiers, max monthly downtime, and multi-region failover."),
        ("🌱 Low CO₂ + H100 Regions", "Which Low CO2 Google Cloud regions have H100 GPUs (A3 series) and the lowest FinOps compute multiplier?"),
        ("🇮🇳 Mumbai vs Iowa FinOps", "Compare asia-south1 (Mumbai) vs us-central1 (Iowa) across compute pricing, CUD discounts, and Vertex AI models."),
        ("⚡ 99.999% FinTech Stack", "Design a 99.999% Dual-Region Active-Active FinTech architecture on Google Cloud with composite SLA math.")
    ]

    public init(
        store: CatalogStore,
        copilot: GeminiCopilotService,
        initialPrompt: String? = nil
    ) {
        self.store = store
        self.copilot = copilot
        self.initialPrompt = initialPrompt
    }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollViewReader { proxy in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 14) {
                            copilotHeaderHero
                            keychainConfigCard
                            quickPromptChipsRow

                            ForEach(copilot.messages) { turn in
                                chatTurnBubble(turn)
                                    .id(turn.id)
                            }

                            if copilot.isGenerating {
                                generatingIndicatorCard
                                    .id("generating-indicator")
                            }
                        }
                        .padding(16)
                    }
                    .onChange(of: copilot.messages.count) { _, _ in
                        if let lastId = copilot.messages.last?.id {
                            withAnimation(.easeOut(duration: 0.25)) {
                                proxy.scrollTo(lastId, anchor: .bottom)
                            }
                        }
                    }
                }

                Divider()
                composerBar
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle("Gemini Cloud Copilot")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Reset") {
                        copilot.clearConversation()
                    }
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                }
            }
            .task {
                if !didRunInitialPrompt,
                   let prompt = initialPrompt?.trimmingCharacters(in: .whitespacesAndNewlines),
                   !prompt.isEmpty {
                    didRunInitialPrompt = true
                    await copilot.askCopilot(prompt: prompt, store: store)
                }
            }
        }
    }

    // MARK: - Hero Banner & Model Picker

    private var copilotHeaderHero: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                StickerBadge("GEMINI INTERACTIONS API ✨", background: CloudPalette.acidLime, foreground: .black)
                Spacer()
                Text(copilot.apiKeyConfigured ? "Keychain Active ✓" : "Offline Fallback")
                    .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 9)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(.white.opacity(0.18)))
            }

            Text("Gemini Google Cloud Architect Copilot")
                .font(.system(size: 21, weight: .black, design: .rounded))
                .foregroundStyle(.white)

            Text("Grounded on all \(store.catalog.services.count) Google Cloud services, \(store.catalog.regions.count) regions, \(store.catalog.models.count) AI models, and formal SLA math.")
                .font(.system(size: 12.5, weight: .medium))
                .foregroundStyle(.white.opacity(0.88))

            Picker("Gemini Model", selection: $copilot.selectedModel) {
                ForEach(GeminiModelOption.allCases) { option in
                    Text(option.displayName).tag(option)
                }
            }
            .pickerStyle(.segmented)
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 26, style: .continuous)
                .fill(
                    LinearGradient(
                        colors: store.vibeTheme.heroGradientColors,
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 26, style: .continuous)
                        .strokeBorder(.white.opacity(0.22), lineWidth: 1.2)
                )
        )
    }

    // MARK: - Keychain Gemini API Key Status & Editor

    private var keychainConfigCard: some View {
        BentoCard(accent: copilot.apiKeyConfigured ? CloudPalette.emerald : CloudPalette.amber, padding: 13) {
            DisclosureGroup(isExpanded: $showingKeyEditor) {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Stored in hardware-backed iOS Keychain (AfterFirstUnlockThisDeviceOnly). Never committed to git.")
                        .font(.system(size: 11.5))
                        .foregroundStyle(.secondary)

                    HStack(spacing: 8) {
                        SecureField("Paste Gemini API Key…", text: $draftAPIKey)
                            .font(.system(size: 13, design: .monospaced))
                            #if os(iOS)
                            .textInputAutocapitalization(.never)
                            #endif
                            .autocorrectionDisabled()
                            .padding(.horizontal, 10)
                            .padding(.vertical, 8)
                            .background(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .fill(CloudPalette.elevatedBackground)
                            )

                        Button("Save Key") {
                            copilot.saveAPIKey(draftAPIKey)
                            draftAPIKey = ""
                            showingKeyEditor = false
                        }
                        .font(.system(size: 12.5, weight: .bold, design: .rounded))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Capsule().fill(store.vibeTheme.primaryAccent))
                    }
                }
                .padding(.top, 8)
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: copilot.apiKeyConfigured ? "key.radiowaves.forward.fill" : "key.fill")
                        .foregroundStyle(copilot.apiKeyConfigured ? CloudPalette.emerald : CloudPalette.amber)
                    Text("Gemini Key: \(copilot.maskedKeyPreview)")
                        .font(.system(size: 12.5, weight: .bold, design: .monospaced))
                        .foregroundStyle(.primary)
                    Spacer()
                    SemanticPill(copilot.selectedModel.rawValue, tint: CloudPalette.violet)
                }
            }
        }
    }

    // MARK: - Quick Prompt Chips

    private var quickPromptChipsRow: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(starterChips, id: \.label) { chip in
                    Button {
                        Task {
                            await copilot.askCopilot(prompt: chip.prompt, store: store)
                        }
                    } label: {
                        Text(chip.label)
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(.primary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 7)
                            .background(
                                Capsule(style: .continuous)
                                    .fill(CloudPalette.cardBackground)
                                    .overlay(
                                        Capsule(style: .continuous)
                                            .strokeBorder(store.vibeTheme.primaryAccent.opacity(0.35), lineWidth: 1)
                                    )
                            )
                    }
                    .buttonStyle(GenZBouncyButtonStyle())
                    .disabled(copilot.isGenerating)
                }
            }
        }
    }

    // MARK: - Chat Turn Bubble

    private func chatTurnBubble(_ turn: GeminiChatTurn) -> some View {
        let isUser = turn.role == .user
        return BentoCard(
            accent: isUser ? store.vibeTheme.primaryAccent : CloudPalette.violet,
            padding: 14
        ) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 6) {
                    Image(systemName: isUser ? "person.crop.circle.fill" : "sparkles")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(isUser ? store.vibeTheme.primaryAccent : CloudPalette.violet)
                    Text(isUser ? "You" : "Gemini Architect")
                        .font(.system(size: 12.5, weight: .heavy, design: .rounded))
                    Spacer()
                    if let model = turn.modelId {
                        SemanticPill(model, tint: turn.isOfflineFallback ? CloudPalette.amber : CloudPalette.violet)
                    }
                    if let total = turn.totalTokens {
                        SemanticPill("\(total) tok", tint: CloudPalette.emerald)
                    }
                }

                Text(LocalizedStringKey(turn.text))
                    .font(.system(size: 13.5, weight: .regular, design: .rounded))
                    .foregroundStyle(.primary)
                    .textSelection(.enabled)

                if let thought = turn.thoughtTokens, thought > 0 {
                    HStack(spacing: 4) {
                        Image(systemName: "brain.head.profile")
                            .font(.system(size: 10))
                        Text("Reasoning thought tokens: \(thought)")
                            .font(.system(size: 10.5, weight: .medium, design: .monospaced))
                    }
                    .foregroundStyle(.secondary)
                }
            }
        }
    }

    private var generatingIndicatorCard: some View {
        BentoCard(accent: CloudPalette.violet, padding: 14) {
            HStack(spacing: 10) {
                ProgressView()
                Text("Gemini (\(copilot.selectedModel.rawValue)) is analyzing Google Cloud topology & SLAs…")
                    .font(.system(size: 12.5, weight: .semibold, design: .rounded))
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Bottom Composer Bar

    private var composerBar: some View {
        HStack(spacing: 10) {
            TextField("Ask Gemini about Google Cloud regions, SLAs, GPUs, or FinOps…", text: $draftPrompt, axis: .vertical)
                .lineLimit(1...4)
                .font(.system(size: 14, weight: .medium, design: .rounded))
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(CloudPalette.cardBackground)
                )

            Button {
                let promptToSend = draftPrompt
                draftPrompt = ""
                Task {
                    await copilot.askCopilot(prompt: promptToSend, store: store)
                }
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 30))
                    .foregroundStyle(
                        draftPrompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || copilot.isGenerating
                            ? Color.secondary
                            : store.vibeTheme.primaryAccent
                    )
            }
            .disabled(draftPrompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || copilot.isGenerating)
            .buttonStyle(GenZBouncyButtonStyle())
            .accessibilityLabel("Send prompt to Gemini")
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial)
    }
}
