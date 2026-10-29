#!/usr/bin/env python3
"""
Local Static & Cached HTTP Server with Daily Auto-Refresh Daemon (server.py).

Features:
  - Serves pre-generated static HTML pages from `dist/` with sub-millisecond latency.
  - Exposes local JSON REST endpoints (`/api/status`, `/api/services`, `/api/regions`,
    `/api/compare`, `/api/refresh`) backed by `data/cache/gcp_catalog.json`.
  - Runs a background daemon thread that checks every hour whether the 24-hour cache
    TTL has expired and automatically harvests fresh GCP API data & regenerates `dist/`.
"""

from __future__ import annotations

import argparse
import gzip
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

from enrichment import build_mobile_catalog
from generator import DIST_DIR, generate_all
from harvester import CATALOG_FILE, DEFAULT_TTL_SECONDS, harvest_all

_CATALOG_LOCK = threading.Lock()
_CACHED_CATALOG: dict[str, Any] | None = None
_CACHED_MOBILE_CATALOG: dict[str, Any] | None = None


def get_catalog(force_refresh: bool = False) -> dict[str, Any]:
    global _CACHED_CATALOG, _CACHED_MOBILE_CATALOG
    with _CATALOG_LOCK:
        if force_refresh or _CACHED_CATALOG is None:
            _CACHED_CATALOG = harvest_all(ttl_seconds=DEFAULT_TTL_SECONDS, force_refresh=force_refresh)
            _CACHED_MOBILE_CATALOG = build_mobile_catalog(_CACHED_CATALOG)
            generate_all(_CACHED_CATALOG)
        return _CACHED_CATALOG


def get_mobile_catalog() -> dict[str, Any]:
    global _CACHED_MOBILE_CATALOG
    cat = get_catalog(force_refresh=False)
    with _CATALOG_LOCK:
        if _CACHED_MOBILE_CATALOG is None:
            _CACHED_MOBILE_CATALOG = build_mobile_catalog(cat)
        return _CACHED_MOBILE_CATALOG


def daily_auto_refresh_daemon(ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    """Background daemon that checks cache age and refreshes once every 24 hours."""
    while True:
        time.sleep(300)  # Check every 5 minutes
        try:
            if not CATALOG_FILE.exists() or (time.time() - CATALOG_FILE.stat().st_mtime) >= ttl_seconds:
                print("[Auto-Refresh Daemon] 24h TTL expired. Refreshing GCP catalog & static HTML in background...")
                get_catalog(force_refresh=True)
        except Exception as err:
            print(f"[Auto-Refresh Daemon] Warning during scheduled refresh: {err}")


class GCPExplorerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(DIST_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def _send_json(self, payload: Any, status: int = 200, etag: str | None = None, compact: bool = False) -> None:
        raw = (
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
            if compact
            else json.dumps(payload, indent=2).encode("utf-8")
        )
        accept_enc = self.headers.get("Accept-Encoding", "")
        use_gzip = "gzip" in accept_enc and len(raw) > 4096
        if use_gzip:
            raw = gzip.compress(raw, compresslevel=6)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if etag:
            self.send_header("ETag", f'"{etag}"')
        if use_gzip:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/status":
            cat = get_catalog()
            mcat = get_mobile_catalog()
            meta = dict(cat.get("meta", {}))
            meta["cache_age_seconds"] = int(time.time() - meta.get("generated_epoch", time.time()))
            meta["etag"] = mcat.get("etag", "")
            self._send_json(meta)
            return

        if path == "/api/mobile-catalog":
            mcat = get_mobile_catalog()
            etag = mcat.get("etag", "")
            inm = (self.headers.get("If-None-Match") or "").strip().strip('"')
            if etag and inm == etag:
                self.send_response(304)
                self.send_header("ETag", f'"{etag}"')
                self.end_headers()
                return
            self._send_json(mcat, etag=etag, compact=True)
            return

        if path == "/api/pricing-sla":
            cat = get_catalog()
            q = (qs.get("q", [""])[0]).strip().lower()
            category = (qs.get("category", [""])[0]).strip().lower()
            svcs = []
            for s in cat.get("services", []):
                if q and q not in s["name"].lower() and q not in s.get("category", "").lower():
                    continue
                if category and s.get("category", "").lower() != category:
                    continue
                svcs.append(
                    {
                        "name": s["name"],
                        "slug": s["slug"],
                        "category": s["category"],
                        "scope": s["scope"],
                        "region_count": s["region_count"],
                        "sla": s.get("sla", {}),
                        "pricing": s.get("pricing", {}),
                    }
                )
            reg_pricing = [
                {
                    "region_id": r["region_id"],
                    "region_name": r["region_name"],
                    "sub_region": r["sub_region"],
                    "is_low_co2": r["is_low_co2"],
                    "pricing": r.get("pricing", {}),
                }
                for r in cat.get("regions", [])
            ]
            self._send_json({"count": len(svcs), "services": svcs, "regions": reg_pricing})
            return

        if path == "/api/updates":
            cat = get_catalog()
            q = (qs.get("q", [""])[0]).strip().lower()
            rel_type = (qs.get("type", [""])[0]).strip().lower()
            notes = cat.get("release_notes", [])
            diffs = cat.get("whats_new", [])
            if q:
                notes = [
                    n for n in notes
                    if q in n["product_name"].lower() or q in n["summary"].lower() or q in n["category"].lower()
                ]
                diffs = [
                    d for d in diffs
                    if q in d["service"].lower() or q in d["details"].lower() or q in d["region_id"].lower()
                ]
            if rel_type:
                notes = [n for n in notes if n["release_type"].lower() == rel_type]
            self._send_json({"release_notes": notes, "snapshot_diffs": diffs})
            return

        if path == "/api/services":
            cat = get_catalog()
            q = (qs.get("q", [""])[0]).strip().lower()
            category = (qs.get("category", [""])[0]).strip().lower()
            region = (qs.get("region", [""])[0]).strip().lower()
            items = cat.get("services", [])
            if q:
                items = [
                    s for s in items
                    if q in s["name"].lower() or any(q in a.lower() for a in s.get("api_names", []))
                ]
            if category:
                items = [s for s in items if s.get("category", "").lower() == category]
            if region:
                items = [s for s in items if region in [r.lower() for r in s.get("regions", [])]]
            self._send_json({"count": len(items), "services": items})
            return

        if path == "/api/regions":
            cat = get_catalog()
            q = (qs.get("q", [""])[0]).strip().lower()
            items = cat.get("regions", [])
            if q:
                items = [
                    r for r in items
                    if q in r["region_id"].lower()
                    or q in r["region_name"].lower()
                    or q in r["full_location"].lower()
                ]
            self._send_json({"count": len(items), "regions": items, "future_regions": cat.get("future_regions", [])})
            return

        if path == "/api/models":
            cat = get_catalog()
            q = (qs.get("q", [""])[0]).strip().lower()
            family = (qs.get("family", [""])[0]).strip().lower()
            region = (qs.get("region", [""])[0]).strip().lower()
            items = cat.get("models", [])
            if q:
                items = [
                    m for m in items
                    if q in m["model_id"].lower()
                    or q in m["model_name"].lower()
                    or q in m["family"].lower()
                    or q in m["modality"].lower()
                ]
            if family:
                items = [m for m in items if family in m.get("family", "").lower()]
            if region:
                if region == "global":
                    items = [m for m in items if m.get("global_endpoint")]
                else:
                    items = [m for m in items if region in [r.lower() for r in m.get("regions", [])]]
            self._send_json({"count": len(items), "models": items})
            return

        if path == "/api/compare":
            cat = get_catalog()
            rids = [r.strip() for r in qs.get("regions", ["us-central1,europe-west1"])[0].split(",") if r.strip()]
            matrix = []
            for s in cat.get("services", []):
                if s["region_count"] == 0:
                    continue
                matrix.append(
                    {
                        "service": s["name"],
                        "category": s["category"],
                        "sla": s.get("sla", {}).get("headline_display", ""),
                        "availability": {rid: (rid in s["regions"]) for rid in rids},
                    }
                )
            self._send_json({"regions": rids, "matrix": matrix})
            return

        return super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/refresh":
            cat = get_catalog(force_refresh=True)
            self._send_json({"status": "refreshed", "meta": cat.get("meta", {})})
            return
        self._send_json({"error": "Not Found"}, status=404)


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Cloud Services, AI Models & Regional Capabilities Local Web Server (Unofficial)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS, help="Cache TTL in seconds (default: 86400)")
    args = parser.parse_args()

    # Ensure cache and static HTML exist before starting server
    cat = get_catalog(force_refresh=False)
    if not (DIST_DIR / "index.html").exists():
        generate_all(cat)

    # Start background daily refresh thread
    t = threading.Thread(target=daily_auto_refresh_daemon, args=(args.ttl,), daemon=True)
    t.start()

    server = ThreadingHTTPServer((args.host, args.port), GCPExplorerHandler)
    print("=" * 76)
    print("🚀 Google Cloud Services & Regional Capabilities Explorer running locally!")
    print("   ⚠️  Unofficial tool — refer to official Google Cloud docs for latest info.")
    print(f"   Web UI (Services)     : http://{args.host}:{args.port}/index.html")
    print(f"   Web UI (Regions)      : http://{args.host}:{args.port}/regions.html")
    print(f"   Web UI (AI Models)    : http://{args.host}:{args.port}/models.html")
    print(f"   Web UI (Capabilities) : http://{args.host}:{args.port}/capabilities.html")
    print(f"   Web UI (Architecture) : http://{args.host}:{args.port}/arch.html")
    print(f"   JSON API Status       : http://{args.host}:{args.port}/api/status")
    print(f"   JSON API AI Models    : http://{args.host}:{args.port}/api/models")
    print("=" * 76)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()

