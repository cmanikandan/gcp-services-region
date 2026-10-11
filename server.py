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
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

from generator import DIST_DIR, generate_all
from harvester import CATALOG_FILE, DEFAULT_TTL_SECONDS, harvest_all

_CATALOG_LOCK = threading.Lock()
_CACHED_CATALOG: dict[str, Any] | None = None


def get_catalog(force_refresh: bool = False) -> dict[str, Any]:
    global _CACHED_CATALOG
    with _CATALOG_LOCK:
        if force_refresh or _CACHED_CATALOG is None:
            _CACHED_CATALOG = harvest_all(ttl_seconds=DEFAULT_TTL_SECONDS, force_refresh=force_refresh)
            generate_all(_CACHED_CATALOG)
        return _CACHED_CATALOG


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

    def _send_json(self, payload: Any, status: int = 200) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "public, max-age=300")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/status":
            cat = get_catalog()
            meta = dict(cat.get("meta", {}))
            meta["cache_age_seconds"] = int(time.time() - meta.get("generated_epoch", time.time()))
            self._send_json(meta)
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

