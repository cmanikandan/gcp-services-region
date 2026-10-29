# Google Cloud Explorer — Universal Native SwiftUI iOS & iPadOS App

> **⚠️ Unofficial Tool:** This is an unofficial companion app — always refer to the [official Google Cloud documentation](https://cloud.google.com/docs) and [Service Level Agreements](https://cloud.google.com/terms/sla) for authoritative information.

A modern, offline-first **Universal SwiftUI iOS 17+ (`iPhone` & `iPad`)** application designed specifically for mobile & tablet workflows—featuring Bento telemetry dashboards, `Swift Charts` Donut/Bar analytics, an interactive 3D `MapKit` globe with multi-detent frosted-glass inspector sheets, tactile SLA/FinOps scrubbers, `CoreSpotlight` system-wide indexing, and `ShareLink` architecture brief cards.

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