# Google Cloud Explorer — Universal Native SwiftUI iOS & iPadOS App

> **⚠️ Unofficial Tool:** This is an unofficial companion app — always refer to the [official Google Cloud documentation](https://cloud.google.com/docs) and [Service Level Agreements](https://cloud.google.com/terms/sla) for authoritative information.

A modern, offline-first **Universal SwiftUI iOS 17+ (`iPhone` & `iPad`)** application designed specifically for mobile & tablet workflows—featuring Bento telemetry dashboards, `Swift Charts` Donut/Bar analytics, an interactive 3D `MapKit` globe with multi-detent frosted-glass inspector sheets, tactile SLA/FinOps scrubbers, `CoreSpotlight` system-wide indexing, and `ShareLink` architecture brief cards.

---

## 🎨 App Icons & App Store Readiness Assets Included

All mandatory Apple App Store Connect assets and metadata manifests are pre-built and wired into the Xcode target:

| Light / App Store Marketing (`1024×1024`) | iOS 18+ Dark Mode (`1024×1024`) | iOS 18+ Tinted Monochrome (`1024×1024`) |
| :---: | :---: | :---: |
| <img src="GoogleCloudExplorer/Assets.xcassets/AppIcon.appiconset/AppIcon.png" width="160" alt="Light App Icon" /> | <img src="GoogleCloudExplorer/Assets.xcassets/AppIcon.appiconset/AppIcon-Dark.png" width="160" alt="Dark App Icon" /> | <img src="GoogleCloudExplorer/Assets.xcassets/AppIcon.appiconset/AppIcon-Tinted.png" width="160" alt="Tinted App Icon" /> |
| `AppIcon.png` (24-bit RGB, no alpha) | `AppIcon-Dark.png` (24-bit RGB, no alpha) | `AppIcon-Tinted.png` (24-bit RGB, no alpha) |

- **1024×1024 Opaque App Icons (`Assets.xcassets/AppIcon.appiconset/`)**: Includes Light/Default, iOS 18+ Dark, and iOS 18+ Tinted Home Screen appearances in strict 24-bit opaque RGB (`hasAlpha: no`, required by App Store Connect). Regenerate or customize anytime via `python3 ios/scripts/generate_app_icon.py`.
- **Mandatory Apple Privacy Manifest (`GoogleCloudExplorer/PrivacyInfo.xcprivacy`)**: Satisfies App Store Connect `ITMS-91053` requirements:
  - `NSPrivacyTracking = false` & `NSPrivacyCollectedDataTypes = []` (*"Data Not Collected"* App Store Privacy Nutrition Label).
  - Declares Required Reason APIs: `NSPrivacyAccessedAPICategoryUserDefaults` (`CA92.1` — local bookmarks/stacks) and `NSPrivacyAccessedAPICategoryFileTimestamp` (`C617.1` — local delta cache check).
- **Automated US Export Compliance (`Config/Info.plist`)**: Sets `ITSAppUsesNonExemptEncryption = false` (uses only standard iOS `URLSession` HTTPS/TLS) so TestFlight and App Store builds skip manual export compliance prompts.
- **Universal Device & Launch Screen Support (`Config/Shared.xcconfig`)**: Configured with `TARGETED_DEVICE_FAMILY = 1,2` (native iPhone + iPad), `INFOPLIST_KEY_UILaunchScreen_Generation = YES`, and `LSApplicationCategoryType = public.app-category.developer-tools`.

---

## ✨ Native Architecture & 5-Tab Experience

- **Adaptive Layout (`ContentView.swift`)**:
  - **iPhone (`compact` width)**: Native 5-tab `TabView` (`Pulse`, `Globe`, `Catalog`, `SLA & Cost`, `Updates`).
  - **iPad (`regular` width)**: Native `NavigationSplitView` sidebar + detail workspace.
- **Tab 1 — Pulse Home (`PulseBentoHomeView.swift`)**:
  - Live **Omni-Search** instant answer cards across 153 services, 43 regions, and 91+ AI models.
  - **2×2 Bento Telemetry Grid** + **`Swift Charts` `SectorMark` SLA Donut** + **Regional Cost Tier `BarMark` Distribution**.
  - **Customer Architecture Stacks** carousel with instant readiness audit + **Official Release Notes** story cards.
- **Tab 2 — Interactive 3D Globe (`InteractiveGlobeMapView.swift`)**:
  - Hardware-accelerated 3D realistic `MapKit` globe (`MapStyle.imagery(elevation: .realistic)`) with fly-to region camera animations.
  - Floating frosted filter pills (`All 43`, `🌱 Low CO₂`, `🤖 Vertex AI`, `⚡ GPU Zones`, `🚀 Future`, `🌐 Edge PoPs`) and multi-detent `.regularMaterial` bottom sheets (`RegionInspectorSheetView`).
- **Tab 3 — Native Catalog Browser (`NativeCatalogBrowserView.swift`)**:
  - Segmented native browser for **153 Google Cloud Services** (with `RingGaugeView` regional coverage rings, SLA badges, Free Tier pills, and swipe/tap bookmarks) and **91+ AI & Foundation Models** (`AIModelInspectorSheet`).
- **Tab 4 — Pricing & Composite SLA Studio (`PricingSLAStudioView.swift`)**:
  - **Composite Workload SLA Simulator**: Toggle critical-path services across **Single-Region Serial (`R₁ × R₂ × …`)**, **Dual-Region Active-Active (`1 − (1 − R)²`)**, and **Tri-Region Quorum** with live monthly/annual downtime budgets.
  - **Regional FinOps & CUD Scrubber**: Tactile monthly spend slider + `On-Demand` / `1Y CUD` / `3Y CUD` picker + `Swift Charts` regional cost bar benchmark + one-tap **`ShareLink`** card export (`ImageRenderer`).
- **Tab 5 — Release Pulse Timeline (`ReleasePulseTimelineView.swift`)**:
  - Magazine-style **Official Google Cloud Release Notes** (`Feature`, `Announcement`, `Security`, `Deprecated`) + **Regional Snapshot Diffs** with a 1-tap **My Stack** filter.

---

## 📦 Zero-Latency Offline Bundle + ETag/Gzip Delta Sync

1. **Embedded Offline Snapshot (`Resources/mobile_catalog.json`, ~541 KB)**:
   - Ships inside `Bundle.main` so cold launch takes `0ms` with **100% Airplane Mode** functionality.
   - Re-sync bundled JSON anytime after running `harvester.py` / `generator.py`:
     ```bash
     python3 ios/scripts/sync_bundled_catalog.py
     ```
2. **Delta Sync Engine (`CatalogSyncActor` in `Engine/CatalogStore.swift`)**:
   - Sends `If-None-Match` + `Accept-Encoding: gzip` to `/api/mobile-catalog` (`~39.8 KB` over the wire when changed, `0 bytes` on `304 Not Modified`) and persists updates atomically to `Application Support/mobile_catalog_latest.json`.

---

## 🛠️ Building & Running in Xcode

### CLI Verification Build (No Signing Required)
```bash
# iOS Simulator build (arm64)
xcodebuild build \
  -project ios/GoogleCloudExplorer/GoogleCloudExplorer.xcodeproj \
  -scheme GoogleCloudExplorer \
  -destination 'generic/platform=iOS Simulator' \
  CODE_SIGNING_ALLOWED=NO

# Physical iPhone / iPad build (iphoneos arm64)
xcodebuild build \
  -project ios/GoogleCloudExplorer/GoogleCloudExplorer.xcodeproj \
  -scheme GoogleCloudExplorer \
  -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO
```

### Running in Xcode Simulator or on a Physical iPhone / iPad
1. Open `ios/GoogleCloudExplorer/GoogleCloudExplorer.xcodeproj` in **Xcode 16+**.
2. Select the **GoogleCloudExplorer** target -> **Signing & Capabilities**, enable **Automatically manage signing**, and select your **Apple ID Personal Team** (or Apple Developer Team).
3. Choose an iPhone or iPad Simulator (or connected device) and press **⌘R** (`Run`) or **⌘U** (`Test`).

---

## 🚀 Publishing to the Apple App Store (Step-by-Step Guide)

### 1. Enroll & Register Bundle Identifier
1. Enroll in the [Apple Developer Program](https://developer.apple.com/programs/) (`$99 USD/year`).
2. Update [`Config/Shared.xcconfig`](Config/Shared.xcconfig) with your unique reverse-DNS Bundle Identifier and release version:
   ```ini
   PRODUCT_BUNDLE_IDENTIFIER = com.<your-domain>.cloudregionexplorer
   MARKETING_VERSION = 2.0.0
   CURRENT_PROJECT_VERSION = 1
   ```
3. In [App Store Connect](https://appstoreconnect.apple.com/) -> **Apps** -> **+** -> **New App**, select **iOS**, choose your registered Bundle ID, and set Primary Category to **Developer Tools** (Secondary: **Reference**).

### 2. Follow App Store Trademark & Naming Guidelines (Guideline 4.1 & 5.2)
Because this is an independent, unofficial community reference app, Apple App Review requires that third-party titles do **not** imply official endorsement by Google LLC:
- **Recommended App Store Name**: `Cloud Region & SLA Explorer` (or `Region & SLA Companion`)
- **Recommended Subtitle**: `Unofficial Reference for Google Cloud`
- **Home Screen Display Name (`PRODUCT_DISPLAY_NAME` in `Shared.xcconfig`)**: `Cloud Explorer`
- **App Description**: Keep a clear notice in the first paragraph stating that the app is an independent, unofficial reference tool powered by public Google Cloud location, SLA, and release-note feeds.

### 3. Refresh the Offline Bundle & Create a Signed Archive
Always bundle the latest 24-hour catalog snapshot right before archiving so new users get fresh data immediately on first offline launch:
```bash
# 1. Refresh upstream catalog & sync mobile_catalog.json into the iOS bundle
python3 harvester.py --force
python3 generator.py
python3 ios/scripts/sync_bundled_catalog.py

# 2. Archive via Xcode UI:
#    Open GoogleCloudExplorer.xcodeproj -> Select "Any iOS Device (arm64)"
#    Menu: Product -> Archive -> Distribute App -> App Store Connect -> Upload

# Or archive from the terminal (with Automatic Signing configured):
xcodebuild archive \
  -project ios/GoogleCloudExplorer/GoogleCloudExplorer.xcodeproj \
  -scheme GoogleCloudExplorer \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath build/GoogleCloudExplorer.xcarchive \
  -allowProvisioningUpdates
```

### 4. App Store Connect Screenshots, Privacy & Submission Checklist
- **Required Screenshots** (App Store Connect Media Manager auto-scales smaller sizes from these two):
  1. **6.9" iPhone Display** (`iPhone 16 Pro Max` / `iPhone 17 Pro Max` — `1320 × 2868 px`)
  2. **13" iPad Display** (`iPad Pro 13-inch` — `2064 × 2752 px`)
- **App Privacy Questionnaire**: Select **"No, we do not collect data from this app"** — the app stores bookmarks and stacks strictly on-device (`PrivacyInfo.xcprivacy` is already bundled).
- **Privacy Policy & Support URLs**: Point **Support URL** to your GitHub repository Issues page and host a short static **Privacy Policy** page (e.g., via GitHub Pages) confirming zero personal data collection, zero analytics SDKs, and zero third-party ad tracking.
- **TestFlight & Review**: Once build processing completes (~5–10 minutes), smoke-test in **TestFlight** (including Airplane Mode cold launch), attach the build to your App Store version, and click **Add for Review -> Submit to App Review**.

---

## 📄 License

Released under the [MIT License](../../LICENSE).