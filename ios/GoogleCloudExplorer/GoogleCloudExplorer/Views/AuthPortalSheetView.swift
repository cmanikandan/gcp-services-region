import SwiftUI
#if canImport(AuthenticationServices)
import AuthenticationServices
#endif

// MARK: - Gen Z Auth Onboarding & Holographic Builder Passport Sheet

public struct AuthPortalSheetView: View {
    @Bindable var store: CatalogStore
    @Bindable var auth: AuthManager
    @Environment(\.dismiss) private var dismiss

    @State private var draftHandle: String = "cloud.architect"
    @State private var selectedEmoji: String = "⚡"
    @State private var selectedRole: BuilderRoleVibe = .aiBuilder
    @State private var showingDeleteConfirm = false
    @State private var showingSecuritySpec = false

    private let avatarEmojis = ["⚡", "👾", "🦊", "🚀", "🌱", "🔥", "💎", "🧠"]

    public init(store: CatalogStore, auth: AuthManager) {
        self.store = store
        self.auth = auth
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    switch auth.sessionState {
                    case .ghostMode, .authenticating:
                        ghostSignInPortal
                    case .authenticated(let profile), .vaultLocked(let profile):
                        authenticatedPassportStudio(profile: profile)
                    }

                    vibeThemePickerCard
                    securityArchitectureAssumptionsCard
                }
                .padding(16)
            }
            .background(CloudPalette.canvasBackground)
            .navigationTitle(auth.currentUser == nil ? "Cloud Vault Sign-In" : "Builder Passport")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                }
            }
            .alert("Delete Cloud Account & Synced Vault?", isPresented: $showingDeleteConfirm) {
                Button("Delete Permanently", role: .destructive) {
                    Task {
                        await auth.deleteAccountAndVault(store: store)
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This permanently deletes your synced account on the sync server and wipes all Keychain tokens & P-256 Passkey material on this device. Offline Google Cloud catalog browsing remains available.")
            }
        }
    }

    // MARK: - 1. Ghost Mode -> Passwordless Gen Z Sign-In Portal

    private var ghostSignInPortal: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Aura Hero Card
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    StickerBadge("ZERO PASSWORDS ✨", background: CloudPalette.acidLime, foreground: .black)
                    Spacer()
                    Text("Unofficial App")
                        .font(.system(size: 10.5, weight: .bold, design: .rounded))
                        .foregroundStyle(.white.opacity(0.85))
                        .padding(.horizontal, 9)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(.white.opacity(0.16)))
                }

                Text("Claim Your Google Cloud Builder Passport 🪪")
                    .font(.system(size: 24, weight: .black, design: .rounded))
                    .foregroundStyle(.white)

                Text("Sync your pinned services, Low CO₂ regions, custom 5-Nines SLA stacks, and Vibe Theme across iPhone & iPad. Zero Google Cloud IAM or billing access—ever.")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(.white.opacity(0.86))

                HStack(spacing: 8) {
                    miniHeroChip("🔐 iOS Keychain")
                    miniHeroChip("🛡️ PKCE S256")
                    miniHeroChip("🔑 P-256 Passkey")
                }
            }
            .padding(20)
            .background(
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: store.vibeTheme.heroGradientColors,
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .strokeBorder(.white.opacity(0.22), lineWidth: 1.2)
                    )
            )

            // Persona Customizer (@handle + Emoji + Builder Vibe)
            BentoCard(accent: store.vibeTheme.primaryAccent) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("1. PICK YOUR @HANDLE & AURA")
                        .font(.system(size: 11, weight: .black, design: .rounded))
                        .tracking(0.6)
                        .foregroundStyle(store.vibeTheme.primaryAccent)

                    HStack(spacing: 10) {
                        Text(selectedEmoji)
                            .font(.system(size: 24))
                            .frame(width: 46, height: 46)
                            .background(
                                Circle()
                                    .fill(store.vibeTheme.primaryAccent.opacity(0.16))
                            )

                        HStack(spacing: 4) {
                            Text("@")
                                .font(.system(size: 16, weight: .black, design: .monospaced))
                                .foregroundStyle(store.vibeTheme.primaryAccent)
                            TextField("cloud.architect", text: $draftHandle)
                                .font(.system(size: 15.5, weight: .bold, design: .monospaced))
                                #if os(iOS)
                                .textInputAutocapitalization(.never)
                                #endif
                                .autocorrectionDisabled()
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 11)
                        .background(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .fill(CloudPalette.elevatedBackground)
                        )
                    }

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(avatarEmojis, id: \.self) { emoji in
                                Button {
                                    selectedEmoji = emoji
                                } label: {
                                    Text(emoji)
                                        .font(.system(size: 19))
                                        .frame(width: 38, height: 38)
                                        .background(
                                            Circle()
                                                .fill(selectedEmoji == emoji ? store.vibeTheme.primaryAccent.opacity(0.24) : CloudPalette.elevatedBackground)
                                                .overlay(
                                                    Circle()
                                                        .strokeBorder(selectedEmoji == emoji ? store.vibeTheme.primaryAccent : .clear, lineWidth: 1.5)
                                                )
                                        )
                                }
                                .buttonStyle(GenZBouncyButtonStyle())
                            }
                        }
                    }

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(BuilderRoleVibe.allCases) { vibe in
                                let active = selectedRole == vibe
                                Button {
                                    selectedRole = vibe
                                } label: {
                                    Text(vibe.label)
                                        .font(.system(size: 12, weight: .bold, design: .rounded))
                                        .foregroundStyle(active ? .white : .primary)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 7)
                                        .background(
                                            Capsule(style: .continuous)
                                                .fill(active ? store.vibeTheme.primaryAccent : CloudPalette.elevatedBackground)
                                        )
                                }
                                .buttonStyle(GenZBouncyButtonStyle())
                            }
                        }
                    }
                }
            }

            // Passwordless Sign-In Methods
            BentoCard(accent: CloudPalette.violet) {
                VStack(alignment: .leading, spacing: 11) {
                    HStack {
                        Text("2. PASSWORDLESS SIGN-IN")
                            .font(.system(size: 11, weight: .black, design: .rounded))
                            .tracking(0.6)
                            .foregroundStyle(CloudPalette.violet)
                        Spacer()
                        if case .authenticating = auth.sessionState {
                            ProgressView()
                                .controlSize(.small)
                        }
                    }

                    // Primary: Device Passkey (CryptoKit P-256)
                    Button {
                        Task {
                            await auth.signIn(
                                provider: .passkey,
                                rawHandle: draftHandle,
                                avatarEmoji: selectedEmoji,
                                roleVibe: selectedRole,
                                store: store
                            )
                        }
                    } label: {
                        HStack {
                            Image(systemName: "person.badge.key.fill")
                                .font(.system(size: 17, weight: .bold))
                            VStack(alignment: .leading, spacing: 1) {
                                Text("Mint Device Passkey (Recommended)")
                                    .font(.system(size: 14.5, weight: .heavy, design: .rounded))
                                Text("CryptoKit P-256 hardware keypair + Face ID ready")
                                    .font(.system(size: 11, weight: .medium))
                                    .opacity(0.88)
                            }
                            Spacer()
                            Image(systemName: "arrow.right.circle.fill")
                        }
                        .foregroundStyle(.white)
                        .padding(.horizontal, 15)
                        .padding(.vertical, 13)
                        .background(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .fill(
                                    LinearGradient(
                                        colors: [store.vibeTheme.primaryAccent, CloudPalette.violet],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                        )
                    }
                    .buttonStyle(GenZBouncyButtonStyle())

                    // Sign in with Apple (Guideline 4.8 compliant)
                    #if canImport(AuthenticationServices)
                    SignInWithAppleButton(.continue) { request in
                        request.requestedScopes = [.fullName, .email]
                        request.nonce = PKCEGenerator.generateOIDCNonce().sha256Hex
                    } onCompletion: { result in
                        Task {
                            await auth.handleAppleAuthorizationResult(
                                result,
                                fallbackHandle: draftHandle,
                                emoji: selectedEmoji,
                                role: selectedRole,
                                store: store
                            )
                        }
                    }
                    .frame(height: 48)
                    .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                    #endif

                    // Continue with Google Identity (OAuth 2.0 PKCE S256)
                    Button {
                        Task {
                            await auth.signIn(
                                provider: .googlePKCE,
                                rawHandle: draftHandle,
                                avatarEmoji: selectedEmoji,
                                roleVibe: selectedRole,
                                store: store
                            )
                        }
                    } label: {
                        HStack {
                            Image(systemName: "shield.checkered")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(CloudPalette.blue)
                            VStack(alignment: .leading, spacing: 1) {
                                Text("Continue with Google Identity (PKCE)")
                                    .font(.system(size: 14, weight: .bold, design: .rounded))
                                    .foregroundStyle(.primary)
                                Text("OAuth 2.0 S256 • Identity only, zero Google Cloud IAM scope")
                                    .font(.system(size: 11))
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundStyle(.tertiary)
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 11)
                        .background(
                            RoundedRectangle(cornerRadius: 15, style: .continuous)
                                .fill(CloudPalette.elevatedBackground)
                        )
                    }
                    .buttonStyle(GenZBouncyButtonStyle())

                    Button {
                        dismiss()
                    } label: {
                        HStack {
                            Spacer()
                            Text("Stay in Ghost Mode 👻 • 100% Offline, No Account Needed")
                                .font(.system(size: 12, weight: .bold, design: .rounded))
                                .foregroundStyle(.secondary)
                            Spacer()
                        }
                        .padding(.top, 4)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .sensoryFeedback(.selection, trigger: selectedEmoji)
        .sensoryFeedback(.selection, trigger: selectedRole)
    }

    // MARK: - 2. Authenticated Holographic Builder Passport & Vault Studio

    private func authenticatedPassportStudio(profile: MobileUserProfile) -> some View {
        let xpProgress = min(1.0, Double(profile.xpPoints) / 550.0)
        return VStack(alignment: .leading, spacing: 16) {
            // Holographic Builder Passport Card
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    StickerBadge("CLOUD BUILDER PASSPORT 🪪", background: CloudPalette.acidLime, foreground: .black)
                    Spacer()
                    Text(profile.resolvedProvider.protocolBadge)
                        .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(.white.opacity(0.16)))
                }

                HStack(spacing: 14) {
                    Text(profile.avatarEmoji)
                        .font(.system(size: 32))
                        .frame(width: 60, height: 60)
                        .background(
                            Circle()
                                .fill(.white.opacity(0.16))
                                .overlay(Circle().strokeBorder(.white.opacity(0.32), lineWidth: 1.5))
                        )

                    VStack(alignment: .leading, spacing: 3) {
                        Text("@\(profile.handle)")
                            .font(.system(size: 22, weight: .black, design: .rounded))
                            .foregroundStyle(.white)
                        Text(profile.resolvedRoleVibe.label)
                            .font(.system(size: 13, weight: .semibold, design: .rounded))
                            .foregroundStyle(.white.opacity(0.88))
                        Text(profile.email)
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(.white.opacity(0.68))
                    }
                    Spacer()
                }

                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(profile.builderLevel)
                            .font(.system(size: 12, weight: .heavy, design: .rounded))
                            .foregroundStyle(CloudPalette.acidLime)
                        Spacer()
                        Text("\(profile.xpPoints) XP")
                            .font(.system(size: 12, weight: .black, design: .monospaced))
                            .foregroundStyle(.white)
                    }
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Capsule().fill(.white.opacity(0.18))
                            Capsule()
                                .fill(
                                    LinearGradient(
                                        colors: [CloudPalette.acidLime, CloudPalette.cyan],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .frame(width: max(24, geo.size.width * xpProgress))
                        }
                    }
                    .frame(height: 8)
                }

                if let proof = auth.lastHandshakeProof {
                    Label(proof, systemImage: "checkmark.shield.fill")
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.88))
                }
            }
            .padding(20)
            .background(
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: store.vibeTheme.heroGradientColors,
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .strokeBorder(.white.opacity(0.24), lineWidth: 1.3)
                    )
            )

            // Cloud Vault Telemetry & Biometric Lock Card
            BentoCard(accent: CloudPalette.emerald) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Label("Encrypted Cloud Vault Sync", systemImage: "icloud.and.arrow.up.fill")
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .foregroundStyle(CloudPalette.emerald)
                        Spacer()
                        SemanticPill(vaultStatusLabel, tint: auth.isVaultSyncedLive ? CloudPalette.emerald : CloudPalette.amber)
                    }

                    HStack(spacing: 10) {
                        vaultCounterBox(value: "\(store.bookmarkedServiceSlugs.count)", label: "Pinned Svcs")
                        vaultCounterBox(value: "\(store.bookmarkedRegionIds.count)", label: "Pinned Regions")
                        vaultCounterBox(value: "\(store.customerStacks.count)", label: "SLA Stacks")
                    }

                    Toggle(isOn: $auth.biometricLockEnabled) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Face ID / Passcode Vault Lock")
                                .font(.system(size: 13.5, weight: .bold, design: .rounded))
                            Text("Require LocalAuthentication biometrics on cold launch")
                                .font(.system(size: 11.5))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .tint(store.vibeTheme.primaryAccent)

                    HStack(spacing: 10) {
                        Button {
                            Task { await auth.syncVaultIfAuthenticated(with: store) }
                        } label: {
                            Label("Sync Vault Now ⚡", systemImage: "arrow.triangle.2.circlepath")
                                .font(.system(size: 13, weight: .heavy, design: .rounded))
                                .foregroundStyle(.white)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Capsule().fill(store.vibeTheme.primaryAccent))
                        }
                        .buttonStyle(GenZBouncyButtonStyle())

                        if auth.biometricLockEnabled {
                            Button {
                                auth.lockVaultNow()
                                dismiss()
                            } label: {
                                Label("Lock", systemImage: "lock.fill")
                                    .font(.system(size: 13, weight: .bold, design: .rounded))
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 10)
                                    .background(Capsule().fill(CloudPalette.elevatedBackground))
                            }
                            .buttonStyle(GenZBouncyButtonStyle())
                        }
                    }
                }
            }

            // Session & App Store Guideline 5.1.1(v) Account Actions
            BentoCard {
                VStack(alignment: .leading, spacing: 10) {
                    Button {
                        Task { await auth.signOut(store: store) }
                    } label: {
                        HStack {
                            Label("Switch to Ghost Mode 👻 (Sign Out)", systemImage: "rectangle.portrait.and.arrow.right")
                                .font(.system(size: 14, weight: .bold, design: .rounded))
                            Spacer()
                        }
                        .foregroundStyle(.primary)
                        .padding(.vertical, 4)
                    }
                    .buttonStyle(.plain)

                    Divider()

                    Button(role: .destructive) {
                        showingDeleteConfirm = true
                    } label: {
                        HStack {
                            Label("Delete Cloud Account & Wipe Keychain", systemImage: "trash.fill")
                                .font(.system(size: 13.5, weight: .bold, design: .rounded))
                            Spacer()
                        }
                        .foregroundStyle(CloudPalette.coral)
                        .padding(.vertical, 4)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - 3. Gen Z Vibe Theme Picker Card

    private var vibeThemePickerCard: some View {
        BentoCard(accent: store.vibeTheme.primaryAccent) {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label("App Aura & Vibe Check", systemImage: "paintpalette.fill")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundStyle(store.vibeTheme.primaryAccent)
                    Spacer()
                    Text(store.vibeTheme.displayName)
                        .font(.system(size: 11.5, weight: .bold, design: .rounded))
                        .foregroundStyle(.secondary)
                }

                LazyVGrid(columns: [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)], spacing: 10) {
                    ForEach(VibeTheme.allCases) { theme in
                        let selected = store.vibeTheme == theme
                        Button {
                            withAnimation(.spring(response: 0.32, dampingFraction: 0.75)) {
                                store.vibeTheme = theme
                            }
                        } label: {
                            HStack(spacing: 8) {
                                Text(theme.emoji)
                                    .font(.system(size: 20))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(theme.displayName)
                                        .font(.system(size: 13, weight: .heavy, design: .rounded))
                                        .foregroundStyle(.primary)
                                        .lineLimit(1)
                                    Text(theme.tagline)
                                        .font(.system(size: 10))
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                Spacer(minLength: 0)
                            }
                            .padding(11)
                            .background(
                                RoundedRectangle(cornerRadius: 16, style: .continuous)
                                    .fill(selected ? theme.primaryAccent.opacity(0.15) : CloudPalette.elevatedBackground)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 16, style: .continuous)
                                            .strokeBorder(selected ? theme.primaryAccent : .clear, lineWidth: 1.6)
                                    )
                            )
                        }
                        .buttonStyle(GenZBouncyButtonStyle())
                    }
                }
            }
        }
        .sensoryFeedback(.selection, trigger: store.vibeTheme)
    }

    // MARK: - 4. Transparent Mobile Auth & Security Architecture Card

    private var securityArchitectureAssumptionsCard: some View {
        BentoCard {
            DisclosureGroup(isExpanded: $showingSecuritySpec) {
                VStack(alignment: .leading, spacing: 8) {
                    authSpecBullet("Ghost Mode First (Apple Guideline 5.1.1v)", "Every offline Google Cloud catalog, 3D Globe, and SLA/FinOps tool works with zero login gates.")
                    authSpecBullet("Passwordless Native Flows (Guideline 4.8)", "Supports CryptoKit P-256 Passkeys, Sign in with Apple (OIDC SHA-256 nonce), and Google Identity OAuth 2.0 PKCE (S256).")
                    authSpecBullet("Hardware Keychain & Token Rotation", "HS256 Bearer JWTs (1h TTL) + single-use rotating refresh tokens are stored in iOS Keychain (AfterFirstUnlockThisDeviceOnly), never UserDefaults.")
                    authSpecBullet("Strict Zero-IAM Boundary", "Unofficial companion app: never requests Google Cloud IAM, service account keys, or billing permissions.")
                }
                .padding(.top, 8)
            } label: {
                Label("Mobile Auth & Privacy Architecture", systemImage: "lock.shield.fill")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)
            }
        }
    }

    private func authSpecBullet(_ title: String, _ detail: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("• \(title)")
                .font(.system(size: 12, weight: .bold, design: .rounded))
            Text(detail)
                .font(.system(size: 11.5))
                .foregroundStyle(.secondary)
        }
    }

    private func miniHeroChip(_ label: String) -> some View {
        Text(label)
            .font(.system(size: 10.5, weight: .bold, design: .rounded))
            .foregroundStyle(.white)
            .padding(.horizontal, 9)
            .padding(.vertical, 4.5)
            .background(Capsule().fill(.white.opacity(0.14)))
    }

    private func vaultCounterBox(value: String, label: String) -> some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(size: 19, weight: .black, design: .rounded))
                .foregroundStyle(.primary)
            Text(label)
                .font(.system(size: 10.5, weight: .semibold))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 9)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(CloudPalette.elevatedBackground)
        )
    }

    private var vaultStatusLabel: String {
        switch auth.vaultSyncStatus {
        case .ghostLocalOnly: return "Local Ghost"
        case .syncing: return "Syncing…"
        case .liveCloudSynced(let tag): return tag
        case .encryptedOnDeviceQueue: return "Keychain Queued"
        }
    }
}

// MARK: - Biometric Face ID Vault Lock Overlay

public struct BiometricVaultLockOverlay: View {
    public let profile: MobileUserProfile
    public let vibeTheme: VibeTheme
    public let onUnlock: () -> Void
    public let onGhostFallback: () -> Void

    public init(
        profile: MobileUserProfile,
        vibeTheme: VibeTheme,
        onUnlock: @escaping () -> Void,
        onGhostFallback: @escaping () -> Void
    ) {
        self.profile = profile
        self.vibeTheme = vibeTheme
        self.onUnlock = onUnlock
        self.onGhostFallback = onGhostFallback
    }

    public var body: some View {
        ZStack {
            Rectangle()
                .fill(.ultraThinMaterial)
                .ignoresSafeArea()

            VStack(spacing: 18) {
                Text(profile.avatarEmoji)
                    .font(.system(size: 44))
                    .frame(width: 84, height: 84)
                    .background(Circle().fill(vibeTheme.primaryAccent.opacity(0.18)))

                VStack(spacing: 6) {
                    StickerBadge("VAULT LOCKED 🔐", background: vibeTheme.primaryAccent, foreground: .white)
                    Text("Welcome back, @\(profile.handle)")
                        .font(.system(size: 22, weight: .black, design: .rounded))
                    Text("Unlock with Face ID or Passcode to access your synced Google Cloud SLA stacks & FinOps vault.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 20)
                }

                Button(action: onUnlock) {
                    Label("Unlock with Face ID", systemImage: "faceid")
                        .font(.system(size: 15, weight: .heavy, design: .rounded))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 24)
                        .padding(.vertical, 13)
                        .background(Capsule().fill(vibeTheme.primaryAccent))
                }
                .buttonStyle(GenZBouncyButtonStyle())

                Button("Continue in Ghost Mode 👻", action: onGhostFallback)
                    .font(.system(size: 12.5, weight: .bold, design: .rounded))
                    .foregroundStyle(.secondary)
            }
            .padding(26)
            .frame(maxWidth: 360)
            .background(
                RoundedRectangle(cornerRadius: 30, style: .continuous)
                    .fill(CloudPalette.cardBackground)
                    .shadow(color: .black.opacity(0.18), radius: 24, x: 0, y: 10)
            )
            .padding(24)
        }
    }
}
