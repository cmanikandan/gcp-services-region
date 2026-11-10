#!/usr/bin/env python3
"""
End-to-end automated verification suite for Google Cloud Services & Regional Capabilities Explorer:
  1. Strict 1-to-1 Swift Codable schema check across all items in mobile_catalog.json + iOS bundle parity
  2. Static Offline Web PWA artifacts (pricing-sla.html, whatsnew.html, sw.js, manifest.webmanifest)
  3. Live HTTP server endpoints (ETag 304 Not Modified, Gzip compression, CORS, new APIs)
  4. Terminal CLI subcommands (status, sla, pricing, updates)

100% Python 3.10+ standard library only.
"""
import base64
import gzip
import hashlib
import json
import plistlib
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def assert_keys(obj: dict, required_types: dict[str, tuple], context: str) -> None:
    for k, expected in required_types.items():
        assert k in obj, f"Missing key '{k}' in {context}: keys={list(obj.keys())}"
        val = obj[k]
        assert isinstance(val, expected), (
            f"Type mismatch for '{k}' in {context}: expected {expected}, got {type(val).__name__} ({val!r})"
        )


def verify_catalogs_and_swift_codable_schema() -> None:
    dist_mobile = ROOT / "dist" / "data" / "mobile_catalog.json"
    ios_mobile = (
        ROOT
        / "ios"
        / "GoogleCloudExplorer"
        / "GoogleCloudExplorer"
        / "Resources"
        / "mobile_catalog.json"
    )
    assert dist_mobile.exists(), f"Missing {dist_mobile}"
    assert ios_mobile.exists(), f"Missing {ios_mobile}"
    assert dist_mobile.read_bytes() == ios_mobile.read_bytes(), (
        "iOS bundled mobile_catalog.json is out of sync with dist/data/mobile_catalog.json"
    )

    payload = json.loads(dist_mobile.read_text(encoding="utf-8"))
    assert_keys(
        payload,
        {
            "meta": (dict,),
            "regions": (list,),
            "future_regions": (list,),
            "services": (list,),
            "models": (list,),
            "pops": (dict,),
            "whats_new": (list,),
            "release_notes": (list,),
        },
        "MobileCatalog root",
    )

    # Verify CatalogMeta & CatalogCounts
    assert_keys(
        payload["meta"],
        {
            "generated_at": (str,),
            "generated_epoch": (int,),
            "ttl_seconds": (int,),
            "refresh_policy": (str,),
            "counts": (dict,),
        },
        "CatalogMeta",
    )
    assert_keys(
        payload["meta"]["counts"],
        {
            "total_services": (int,),
            "regional_services": (int,),
            "multi_region_services": (int,),
            "global_services": (int,),
            "available_regions": (int,),
            "future_regions": (int,),
            "total_zones": (int,),
            "gpu_zones": (int,),
            "low_co2_regions": (int,),
            "ai_models": (int,),
            "ai_model_families": (int,),
            "discovery_apis": (int,),
            "total_api_methods": (int,),
            "edge_pops": (int,),
            "cloud_cdn_pops": (int,),
            "media_cdn_pops": (int,),
        },
        "CatalogCounts",
    )

    services = payload["services"]
    regions = payload["regions"]
    models = payload["models"]
    notes = payload["release_notes"]

    assert len(services) >= 150, f"Expected >=150 services, got {len(services)}"
    assert len(regions) >= 43, f"Expected >=43 regions, got {len(regions)}"
    assert len(models) >= 85, f"Expected >=85 AI models, got {len(models)}"
    assert len(notes) >= 10, f"Expected >=10 release notes, got {len(notes)}"

    # Strictly validate every CloudService against Swift CloudService + ServiceSLA + ServicePricing
    for svc in services:
        ctx = f"CloudService({svc.get('slug')})"
        assert_keys(
            svc,
            {
                "name": (str,),
                "slug": (str,),
                "category": (str,),
                "url": (str,),
                "scope": (str,),
                "is_global": (bool,),
                "regions": (list,),
                "region_count": (int,),
                "coverage_pct": (int, float),
                "multi_regions": (list,),
                "api_names": (list,),
                "total_api_methods": (int,),
                "sla": (dict,),
                "pricing": (dict,),
            },
            ctx,
        )
        assert all(isinstance(mr, str) for mr in svc["multi_regions"]), (
            f"Expected list[str] for {ctx}.multi_regions, got {svc['multi_regions']}"
        )
        assert_keys(
            svc["sla"],
            {
                "has_formal_sla": (bool,),
                "headline_uptime_pct": (int, float, type(None)),
                "headline_display": (str,),
                "max_monthly_downtime": (str,),
                "sla_url": (str,),
                "tiers": (list,),
                "credit_schedule": (list,),
                "ha_requirements": (list,),
            },
            f"{ctx}.sla",
        )
        for tier in svc["sla"]["tiers"]:
            assert_keys(
                tier,
                {
                    "tier_name": (str,),
                    "uptime_pct": (int, float),
                    "uptime_display": (str,),
                    "max_monthly_downtime": (str,),
                    "max_annual_downtime": (str,),
                    "topology": (str,),
                },
                f"{ctx}.sla.tier",
            )
        assert_keys(
            svc["pricing"],
            {
                "pricing_url": (str,),
                "billing_model": (str,),
                "primary_units": (str,),
                "has_free_tier": (bool,),
                "free_tier_note": (str,),
                "cud_support": (str,),
                "spot_or_batch_discount": (bool,),
                "discount_note": (str,),
                "cost_drivers": (list,),
            },
            f"{ctx}.pricing",
        )

    # Strictly validate every CloudRegion against Swift CloudRegion + RegionPricing
    for reg in regions:
        ctx = f"CloudRegion({reg.get('region_id')})"
        assert_keys(
            reg,
            {
                "region_id": (str,),
                "region_name": (str,),
                "display_name": (str,),
                "full_location": (str,),
                "sub_region": (str,),
                "status": (str,),
                "is_low_co2": (bool,),
                "lat": (int, float),
                "lng": (int, float),
                "date_launched": (str,),
                "zones": (list,),
                "zone_count": (int,),
                "machine_series": (list,),
                "cpus": (list,),
                "gpus": (list,),
                "confidential_options": (list,),
                "services": (list,),
                "service_count": (int,),
                "ai_model_count": (int,),
                "pricing": (dict,),
            },
            ctx,
        )
        assert_keys(
            reg["pricing"],
            {
                "tier": (str,),
                "relative_compute_index": (int, float),
                "relative_storage_index": (int, float),
                "delta_vs_baseline": (str,),
                "inter_region_egress_band": (str,),
                "cud_1y_discount_pct": (int,),
                "cud_3y_discount_pct": (int,),
            },
            f"{ctx}.pricing",
        )

    # Validate FutureRegion, PoPCatalog, AIModel, ReleaseNoteItem
    for fr in payload["future_regions"]:
        assert_keys(
            fr,
            {
                "region_name": (str,),
                "region_id": (str,),
                "sub_region": (str,),
                "status": (str,),
                "lat": (int, float),
                "lng": (int, float),
                "date_launched": (str,),
            },
            "FutureRegion",
        )
    assert_keys(
        payload["pops"],
        {"edge_pops": (list,), "cloud_cdn_pops": (list,), "media_cdn_pops": (list,)},
        "PoPCatalog",
    )
    for m in models:
        assert_keys(
            m,
            {
                "model_id": (str,),
                "model_name": (str,),
                "family": (str,),
                "modality": (str,),
                "stage": (str,),
                "global_endpoint": (bool,),
                "multi_regions": (list,),
                "regions": (list,),
                "region_count": (int,),
                "url": (str,),
            },
            f"AIModel({m.get('model_id')})",
        )
    for n in notes:
        assert_keys(
            n,
            {
                "id": (str,),
                "date": (str,),
                "release_type": (str,),
                "product_name": (str,),
                "service_slug": (str, type(None)),
                "category": (str,),
                "summary": (str,),
                "url": (str,),
            },
            f"ReleaseNoteItem({n.get('id')})",
        )

    spanner = next((s for s in services if "spanner" in s["slug"]), None)
    assert spanner is not None and (spanner["sla"]["headline_uptime_pct"] or 0) >= 99.999
    us_central1 = next((r for r in regions if r["region_id"] == "us-central1"), None)
    assert us_central1 is not None and us_central1["pricing"]["relative_compute_index"] == 1.0

    print(
        f"[OK] Strict Swift Codable schema & iOS bundle parity verified across all "
        f"{len(services)} services, {len(regions)} regions, {len(models)} AI models, "
        f"and {len(notes)} release notes ({dist_mobile.stat().st_size / 1024:.1f} KB)"
    )


def verify_pwa_files() -> None:
    required = [
        ROOT / "dist" / "index.html",
        ROOT / "dist" / "pricing-sla.html",
        ROOT / "dist" / "whatsnew.html",
        ROOT / "dist" / "sw.js",
        ROOT / "dist" / "manifest.webmanifest",
        ROOT / "dist" / "assets" / "icon.svg",
    ]
    for p in required:
        assert p.exists() and p.stat().st_size > 100, f"Missing or empty PWA artifact: {p}"

    manifest = json.loads((ROOT / "dist" / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert "Google Cloud" in manifest["name"], "Branding check failed in manifest.webmanifest"
    assert "GCP" not in manifest["name"], "Forbidden 'GCP' abbreviation in manifest.webmanifest"
    print("[OK] Offline PWA static bundle & branding verified (pricing-sla.html, sw.js, manifest.webmanifest)")


def verify_live_server() -> None:
    port = find_free_port()
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py"), "--port", str(port)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"{base}/api/status", timeout=1.0) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.15)
        else:
            raise RuntimeError("server.py did not become ready in time")

        req = urllib.request.Request(
            f"{base}/api/mobile-catalog",
            headers={"Accept-Encoding": "gzip"},
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            assert resp.status == 200
            etag = resp.headers.get("ETag")
            encoding = resp.headers.get("Content-Encoding")
            cors = resp.headers.get("Access-Control-Allow-Origin")
            raw_bytes = resp.read()
            assert etag, "Missing ETag header on /api/mobile-catalog"
            assert encoding == "gzip", f"Expected gzip encoding, got {encoding}"
            assert cors == "*", f"Expected CORS *, got {cors}"
            decompressed = json.loads(gzip.decompress(raw_bytes).decode("utf-8"))
            assert len(decompressed["services"]) >= 150

        req_304 = urllib.request.Request(
            f"{base}/api/mobile-catalog",
            headers={"If-None-Match": etag, "Accept-Encoding": "gzip"},
        )
        try:
            urllib.request.urlopen(req_304, timeout=5.0)
            raise AssertionError("Expected 304 Not Modified, got 200 OK")
        except urllib.error.HTTPError as e:
            assert e.code == 304, f"Expected 304 Not Modified, got {e.code}"

        for path in ("/api/pricing-sla", "/api/updates", "/pricing-sla.html", "/sw.js", "/manifest.webmanifest"):
            with urllib.request.urlopen(f"{base}{path}", timeout=5.0) as resp:
                assert resp.status == 200, f"Unexpected status {resp.status} for {path}"

        # Verify Mobile Auth & Cloud Vault lifecycle (/api/auth/*)
        def http_json(method: str, path: str, body: dict | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict]:
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)
            data = json.dumps(body).encode("utf-8") if body is not None else None
            r = urllib.request.Request(f"{base}{path}", data=data, headers=req_headers, method=method)
            try:
                with urllib.request.urlopen(r, timeout=25.0) as res:
                    return res.status, json.loads(res.read().decode("utf-8"))
            except urllib.error.HTTPError as err:
                return err.code, json.loads(err.read().decode("utf-8"))

        st_chl, chl = http_json("POST", "/api/auth/challenge", {"provider": "passkey"})
        assert st_chl == 200 and chl.get("nonce"), f"Challenge failed: {chl}"

        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")

        # Tampered PKCE verifier must be rejected with 401
        st_bad, _ = http_json(
            "POST",
            "/api/auth/login",
            {"provider": "google_pkce", "handle": "e2e.tamper", "code_verifier": "wrong_verifier", "code_challenge": challenge},
        )
        assert st_bad == 401, f"Expected 401 for tampered PKCE verifier, got {st_bad}"

        test_handle = f"e2e.genz.{secrets.token_hex(3)}"
        st_login, session = http_json(
            "POST",
            "/api/auth/login",
            {
                "provider": "google_pkce",
                "handle": test_handle,
                "avatar_emoji": "🔮",
                "role_vibe": "aiBuilder",
                "code_verifier": verifier,
                "code_challenge": challenge,
            },
        )
        assert st_login == 200, f"Login failed: {session}"
        access_tok = session["tokens"]["access_token"]
        refresh_tok = session["tokens"]["refresh_token"]
        assert access_tok.count(".") == 2, "Expected 3-part HS256 JWT access_token"

        st_unauth, _ = http_json("GET", "/api/auth/me")
        assert st_unauth == 401, "Expected 401 without Bearer token"

        st_me, me_payload = http_json("GET", "/api/auth/me", headers={"Authorization": f"Bearer {access_tok}"})
        assert st_me == 200 and me_payload["user"]["handle"] == test_handle

        st_sync, synced = http_json(
            "PUT",
            "/api/auth/sync",
            {
                "bookmarked_services": ["spanner", "vertex-ai", "cloud-run", "alloydb"],
                "bookmarked_regions": ["us-central1", "asia-south1", "europe-west4"],
                "customer_stacks": [
                    {
                        "id": "E621E1F8-C36C-495A-93FC-0C247A3E6E5F",
                        "name": "Gen Z AI Stack",
                        "subtitle": "99.999% Multi-Region",
                        "serviceSlugs": ["vertex-ai", "spanner"],
                        "targetRegionIds": ["us-central1", "asia-south1"],
                        "topologyMode": "Dual-Region Active-Active",
                    }
                ],
                "vibe_theme": "ultravioletPulse",
            },
            headers={"Authorization": f"Bearer {access_tok}"},
        )
        assert st_sync == 200 and synced["vault"]["vibe_theme"] == "ultravioletPulse"
        assert synced["user"]["xp_points"] >= 285

        # Refresh token rotation + replay rejection
        st_ref, rotated = http_json("POST", "/api/auth/refresh", {"refresh_token": refresh_tok})
        assert st_ref == 200
        new_access_tok = rotated["tokens"]["access_token"]
        st_replay, _ = http_json("POST", "/api/auth/refresh", {"refresh_token": refresh_tok})
        assert st_replay == 401, "Replayed refresh token must be rejected with 401"

        # Permanent account deletion (App Store Guideline 5.1.1v)
        st_del, _ = http_json("DELETE", "/api/auth/account", headers={"Authorization": f"Bearer {new_access_tok}"})
        assert st_del == 200
        st_after_del, _ = http_json("GET", "/api/auth/me", headers={"Authorization": f"Bearer {new_access_tok}"})
        assert st_after_del == 401

        # Verify Gemini Architect endpoint (/api/gemini/ask)
        st_gem, gem_payload = http_json(
            "POST",
            "/api/gemini/ask",
            {"prompt": "Compare Cloud Spanner and AlloyDB SLA in 2 bullet points.", "model": "gemini-3.8-flash"},
        )
        assert st_gem == 200 and len(gem_payload.get("output_text", "")) > 20, f"Gemini ask failed: {gem_payload}"

        print(
            f"[OK] Live HTTP server + Mobile Auth Vault verified on :{port} "
            f"(Gzip={len(raw_bytes) / 1024:.1f} KB, ETag={etag}, PKCE S256, HS256 JWT, Refresh Rotation, Vault Sync & Delete)"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def verify_ios_swift_architecture() -> None:
    ios_app_dir = ROOT / "ios" / "GoogleCloudExplorer" / "GoogleCloudExplorer"
    required_swift = [
        ios_app_dir / "GoogleCloudExplorerApp.swift",
        ios_app_dir / "ContentView.swift",
        ios_app_dir / "DesignSystem" / "GlassBentoTheme.swift",
        ios_app_dir / "Auth" / "AuthModels.swift",
        ios_app_dir / "Auth" / "KeychainVault.swift",
        ios_app_dir / "Auth" / "AuthManager.swift",
        ios_app_dir / "Engine" / "CatalogStore.swift",
        ios_app_dir / "Engine" / "GeminiCopilotService.swift",
        ios_app_dir / "Engine" / "SLACalculator.swift",
        ios_app_dir / "Models" / "CatalogModels.swift",
        ios_app_dir / "Views" / "AuthPortalSheetView.swift",
        ios_app_dir / "Views" / "GeminiCopilotSheetView.swift",
        ios_app_dir / "Views" / "PulseBentoHomeView.swift",
        ios_app_dir / "Views" / "InteractiveGlobeMapView.swift",
        ios_app_dir / "Views" / "NativeCatalogBrowserView.swift",
        ios_app_dir / "Views" / "PricingSLAStudioView.swift",
        ios_app_dir / "Views" / "ReleasePulseTimelineView.swift",
        ios_app_dir / "Views" / "ServiceAndRegionDetailViews.swift",
    ]
    for sf in required_swift:
        assert sf.exists() and sf.stat().st_size > 80, f"Missing Swift source file: {sf}"

    all_swift = list((ROOT / "ios" / "GoogleCloudExplorer").rglob("*.swift"))
    for sf in all_swift:
        src = sf.read_text(encoding="utf-8")
        # Strip multiline strings, single-line strings, and comments before checking balanced braces
        cleaned = re.sub(r'"""[\s\S]*?"""', '""', src)
        cleaned = re.sub(r'"(?:\\.|[^"\\])*"', '""', cleaned)
        cleaned = re.sub(r"//.*", "", cleaned)
        cleaned = re.sub(r"/\*[\s\S]*?\*/", "", cleaned)
        assert cleaned.count("{") == cleaned.count("}"), f"Unbalanced braces in {sf}"
        assert cleaned.count("(") == cleaned.count(")"), f"Unbalanced parens in {sf}"
        assert not re.search(r'"[^"]*\bGCP\b[^"]*"', src), f"Forbidden 'GCP' branding in string literal in {sf}"

    # Verify Apple Privacy Manifest & Info.plist are valid plists
    privacy_plist = plistlib.loads((ios_app_dir / "PrivacyInfo.xcprivacy").read_bytes())
    assert privacy_plist["NSPrivacyTracking"] is False
    info_plist = plistlib.loads((ROOT / "ios" / "GoogleCloudExplorer" / "Config" / "Info.plist").read_bytes())
    assert info_plist["ITSAppUsesNonExemptEncryption"] is False
    assert info_plist.get("GEMINI_API_KEY") == "$(GEMINI_API_KEY)", "Info.plist must use $(GEMINI_API_KEY) variable placeholder"

    print(
        f"[OK] Native SwiftUI Gen Z iOS & Auth architecture verified across {len(all_swift)} Swift files "
        "(balanced syntax, zero 'GCP' branding, valid PrivacyInfo.xcprivacy & Info.plist)"
    )


def verify_cli() -> None:
    cmds = [
        ["status"],
        ["sla", "Cloud Spanner"],
        ["pricing", "asia-south1"],
        ["updates"],
        ["ask", "What is Cloud Spanner Multi-Region SLA?"],
    ]
    for args in cmds:
        res = subprocess.run(
            [sys.executable, str(ROOT / "cli.py"), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        assert len(res.stdout.strip()) > 40, f"Empty CLI output for {args}"
    print("[OK] Terminal CLI subcommands verified (status, sla, pricing, updates)")


if __name__ == "__main__":
    verify_catalogs_and_swift_codable_schema()
    verify_pwa_files()
    verify_ios_swift_architecture()
    verify_live_server()
    verify_cli()
    print("\nALL PLATFORM VERIFICATION CHECKS PASSED.")
