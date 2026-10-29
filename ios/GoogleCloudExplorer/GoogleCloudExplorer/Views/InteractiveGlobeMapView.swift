import SwiftUI
import MapKit

// MARK: - Tab 2: 3D Apple MapKit Globe & Regional Footprint Explorer

public struct InteractiveGlobeMapView: View {
    @Bindable var store: CatalogStore

    public enum GlobeLayerFilter: String, CaseIterable, Identifiable {
        case allRegions = "All Regions (43)"
        case lowCO2 = "🌱 Low CO₂"
        case genAI = "🤖 Vertex AI"
        case gpuEnabled = "⚡ GPU Zones"
        case futureOnly = "🚀 Future"
        case edgePoPs = "🌐 Edge PoPs"

        public var id: String { rawValue }
    }

    @State private var activeFilter: GlobeLayerFilter = .allRegions
    @State private var selectedRegion: CloudRegion?
    @State private var cameraPosition: MapCameraPosition = .camera(
        MapCamera(
            centerCoordinate: CLLocationCoordinate2D(latitude: 24.0, longitude: 8.0),
            distance: 26_000_000
        )
    )

    public init(store: CatalogStore) {
        self.store = store
    }

    private var visibleRegions: [CloudRegion] {
        switch activeFilter {
        case .allRegions:
            return store.catalog.regions
        case .lowCO2:
            return store.catalog.regions.filter(\.isLowCo2)
        case .genAI:
            return store.catalog.regions.filter { $0.aiModelCount > 0 }
        case .gpuEnabled:
            return store.catalog.regions.filter { !$0.gpus.isEmpty }
        case .futureOnly, .edgePoPs:
            return []
        }
    }

    private var visibleFutureRegions: [FutureRegion] {
        (activeFilter == .allRegions || activeFilter == .futureOnly) ? store.catalog.futureRegions : []
    }

    private var visibleEdgePoPs: [EdgePoP] {
        activeFilter == .edgePoPs ? store.catalog.pops.edgePops : []
    }

    public var body: some View {
        ZStack(alignment: .top) {
            Map(position: $cameraPosition) {
                ForEach(visibleRegions) { reg in
                    Annotation(reg.regionName, coordinate: reg.coordinate) {
                        Button {
                            withAnimation(.spring(duration: 0.55)) {
                                selectedRegion = reg
                                cameraPosition = .camera(
                                    MapCamera(centerCoordinate: reg.coordinate, distance: 5_800_000)
                                )
                            }
                        } label: {
                            HStack(spacing: 4) {
                                Circle()
                                    .fill(reg.isLowCo2 ? CloudPalette.emerald : CloudPalette.blue)
                                    .frame(width: 8, height: 8)
                                Text(reg.regionId)
                                    .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                                    .foregroundStyle(.primary)
                                Text(String(format: "%.2fx", reg.pricing.relativeComputeIndex))
                                    .font(.system(size: 9.5, weight: .semibold, design: .rounded))
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 5)
                            .background(
                                Capsule(style: .continuous)
                                    .fill(.regularMaterial)
                                    .shadow(color: .black.opacity(0.18), radius: 5, x: 0, y: 2)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }

                ForEach(visibleFutureRegions) { fut in
                    Annotation(fut.regionName, coordinate: fut.coordinate) {
                        HStack(spacing: 4) {
                            Image(systemName: "sparkles")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundStyle(CloudPalette.amber)
                            Text(fut.regionName)
                                .font(.system(size: 10.5, weight: .bold, design: .rounded))
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(.ultraThinMaterial))
                    }
                }

                ForEach(visibleEdgePoPs) { pop in
                    Marker(pop.label, systemImage: "dot.radiowaves.left.and.right", coordinate: pop.coordinate)
                        .tint(CloudPalette.cyan)
                }
            }
            .mapStyle(.standard(elevation: .realistic))
            .ignoresSafeArea(edges: .top)

            // Floating Frosted-Glass Control HUD
            VStack(spacing: 10) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("3D Cloud Topology Globe")
                            .font(.system(size: 17, weight: .bold, design: .rounded))
                        Text("\(store.catalog.regions.count) Active Regions • \(store.catalog.meta.counts.totalZones) Zones • \(store.catalog.meta.counts.totalEdgeLocations) Edge PoPs")
                            .font(.system(size: 11.5, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Menu {
                        Button("Global Overview") { flyTo(lat: 24, lng: 8, distance: 26_000_000) }
                        Button("North & South America") { flyTo(lat: 34, lng: -92, distance: 14_500_000) }
                        Button("Europe & Middle East") { flyTo(lat: 48, lng: 12, distance: 9_800_000) }
                        Button("Asia-Pacific & India") { flyTo(lat: 20, lng: 104, distance: 14_500_000) }
                    } label: {
                        Label("Fly To", systemImage: "location.viewfinder")
                            .font(.system(size: 12.5, weight: .bold, design: .rounded))
                            .padding(.horizontal, 11)
                            .padding(.vertical, 7)
                            .background(Capsule().fill(CloudPalette.blue).foregroundStyle(.white))
                            .foregroundStyle(.white)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .fill(.ultraThinMaterial)
                        .shadow(color: .black.opacity(0.10), radius: 10, x: 0, y: 4)
                )

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(GlobeLayerFilter.allCases) { layer in
                            let selected = activeFilter == layer
                            Button {
                                withAnimation(.snappy) {
                                    activeFilter = layer
                                }
                            } label: {
                                Text(layer.rawValue)
                                    .font(.system(size: 12, weight: .bold, design: .rounded))
                                    .foregroundStyle(selected ? .white : .primary)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 7)
                                    .background(
                                        Capsule(style: .continuous)
                                            .fill(selected ? AnyShapeStyle(CloudPalette.blue) : AnyShapeStyle(.ultraThinMaterial))
                                    )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
            .padding(.horizontal, 14)
            .padding(.top, 8)
            .sensoryFeedback(.selection, trigger: activeFilter)
        }
        .sheet(item: $selectedRegion) { region in
            RegionInspectorSheetView(store: store, region: region)
                .presentationDetents([.height(290), .large])
                .presentationDragIndicator(.visible)
                .presentationBackground(.regularMaterial)
        }
        .onChange(of: store.deepLinkedRegionId) { _, newValue in
            if let rid = newValue, let reg = store.regionsById[rid] {
                selectedRegion = reg
                flyTo(lat: reg.lat, lng: reg.lng, distance: 6_000_000)
                store.deepLinkedRegionId = nil
            }
        }
    }

    private func flyTo(lat: Double, lng: Double, distance: Double) {
        withAnimation(.easeInOut(duration: 0.85)) {
            cameraPosition = .camera(
                MapCamera(
                    centerCoordinate: CLLocationCoordinate2D(latitude: lat, longitude: lng),
                    distance: distance
                )
            )
        }
    }
}
