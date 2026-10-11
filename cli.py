#!/usr/bin/env python3
"""
Local CLI for querying Google Cloud Services, AI Models & Regional Capabilities from the 24h local cache (cli.py).
Note: This is an unofficial tool — refer to official Google Cloud documentation for the latest information.

Examples:
  python3 cli.py status
  python3 cli.py service "Vertex AI"
  python3 cli.py service alloydb
  python3 cli.py models gemini
  python3 cli.py models claude --region us-east5
  python3 cli.py region us-central1
  python3 cli.py region asia-south1
  python3 cli.py compare us-central1 europe-west1 asia-south1
  python3 cli.py refresh [--force]
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from generator import generate_all
from harvester import CATALOG_FILE, DEFAULT_TTL_SECONDS, harvest_all


def load_cached_catalog() -> dict[str, Any]:
    return harvest_all(ttl_seconds=DEFAULT_TTL_SECONDS, force_refresh=False)


def cmd_status(catalog: dict[str, Any]) -> None:
    meta = catalog["meta"]
    counts = meta["counts"]
    age_s = int(time.time() - meta.get("generated_epoch", time.time()))
    print("=" * 76)
    print("Google Cloud Services & Regional Capabilities — Local Cache Status")
    print("⚠️  Unofficial Tool: Refer to official Google Cloud docs for latest info.")
    print("=" * 76)
    print(f"Last Updated      : {meta['generated_at']} ({age_s}s ago)")
    print(f"Refresh Policy    : {meta['refresh_policy']}")
    print(f"Unique Services   : {counts['total_services']} ({counts['regional_services']} Regional, {counts['global_services']} Global)")
    print(f"Available Regions : {counts['available_regions']} (+{counts['future_regions']} Announced Future Regions)")
    print(f"AI & GenAI Models : {counts.get('ai_models', 0)} models across {counts.get('ai_model_families', 0)} model families")
    print(f"Low CO2 Regions   : {counts['low_co2_regions']} 🌱")
    print(f"Availability Zones: {counts['total_zones']} ({counts['gpu_zones']} GPU-enabled zones)")
    print(f"Discovery APIs    : {counts['discovery_apis']} ({counts['total_api_methods']:,} REST API Operations)")
    print(f"Global PoPs       : {counts['edge_pops']} Edge • {counts['cloud_cdn_pops']} Cloud CDN • {counts['media_cdn_pops']} Media CDN")
    print("=" * 76)


def cmd_service(catalog: dict[str, Any], query: str) -> None:
    q = query.strip().lower()
    matches = [
        s for s in catalog["services"]
        if q in s["name"].lower()
        or q in s["slug"].lower()
        or any(q in api.lower() for api in s.get("api_names", []))
    ]
    if not matches:
        print(f"No Google Cloud service matching '{query}' found.")
        sys.exit(1)

    regions_by_id = {r["region_id"]: r for r in catalog["regions"]}
    for s in matches:
        print("=" * 76)
        print(f"Service   : {s['name']}  [{s['category']}]")
        print(f"Scope     : {s['scope']}  |  Regions: {s['region_count']}/{len(regions_by_id)} ({s['coverage_pct']}%)")
        print(f"APIs      : {', '.join(s.get('api_names', [])) or 'N/A'} ({s.get('total_api_methods', 0)} REST operations)")
        print(f"Docs URL  : {s['url']}")
        print("-" * 76)
        if s["regions"]:
            print(f"{'Region Code':<24} {'Region Name':<22} {'Geography':<16} {'Zones':<6} {'Low CO2'}")
            print("-" * 76)
            for rid in s["regions"]:
                r = regions_by_id.get(rid, {})
                co2 = "🌱 Yes" if r.get("is_low_co2") else "No"
                print(
                    f"{rid:<24} {r.get('region_name', ''):<22} "
                    f"{r.get('sub_region', ''):<16} {r.get('zone_count', 3):<6} {co2}"
                )
        else:
            print("Global Service (Served across all Google Cloud edge & control-plane locations)")
        print()


def cmd_models(catalog: dict[str, Any], query: str = "", region: str = "") -> None:
    q = query.strip().lower()
    reg_q = region.strip().lower()
    models = catalog.get("models", [])
    matches = []
    for m in models:
        if q and not (
            q in m["model_id"].lower()
            or q in m["model_name"].lower()
            or q in m["family"].lower()
            or q in m["modality"].lower()
        ):
            continue
        if reg_q:
            if reg_q == "global":
                if not m.get("global_endpoint"):
                    continue
            elif reg_q in ("us", "eu"):
                if reg_q.upper() not in [mr.upper() for mr in m.get("multi_regions", [])]:
                    continue
            else:
                if not any(reg_q == r.lower() or reg_q in r.lower() for r in m.get("regions", [])):
                    continue
        matches.append(m)

    if not matches:
        print(f"No Google Cloud AI models matching query='{query}' region='{region}' found.")
        sys.exit(1)

    print("=" * 96)
    print(f"Google Cloud AI & Foundation Models ({len(matches)} matching models)")
    print("⚠️  Unofficial Tool — Refer to https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations")
    print("=" * 96)
    for m in matches:
        ep = []
        if m.get("global_endpoint"):
            ep.append("global")
        ep.extend(m.get("multi_regions", []))
        ep_str = ", ".join(ep) if ep else "Regional Only"
        rids = m.get("regions", [])
        print(f"• {m['model_name']}  [{m['model_id']}]")
        print(f"  Family   : {m['family']}  |  Modality: {m['modality']}  |  Global/Multi-Region: {ep_str}")
        print(f"  Regions  : ({len(rids)}) {', '.join(rids) if rids else 'Global/Multi-Region endpoint only'}")
        print("-" * 96)


def cmd_region(catalog: dict[str, Any], query: str) -> None:
    q = query.strip().lower()
    matches = [
        r for r in catalog["regions"]
        if q == r["region_id"].lower()
        or q in r["region_id"].lower()
        or q in r["region_name"].lower()
        or q in r["full_location"].lower()
    ]
    if not matches:
        print(f"No Google Cloud region matching '{query}' found.")
        sys.exit(1)

    all_reg_svcs = [s["name"] for s in catalog["services"] if s["region_count"] > 0]
    for r in matches:
        avail_set = set(r["services"])
        missing = [sn for sn in all_reg_svcs if sn not in avail_set]
        ai_models = r.get("ai_models", [])
        print("=" * 76)
        print(f"Region      : {r['region_id']} — {r['region_name']} ({r['sub_region']})")
        print(f"Location    : {r['full_location']}  |  Launched: {r['date_launched']}  |  Low CO2: {'🌱 Yes' if r['is_low_co2'] else 'No'}")
        print(f"Zones ({r['zone_count']})   : {', '.join(r['zones'])}")
        print(f"Machine Srs : {', '.join(r.get('machine_series', []))}")
        print(f"GPUs        : {', '.join(r.get('gpus', [])) or 'Standard CPU only'}")
        print(f"AI Models   : {len(ai_models)} available ({', '.join(m['model_id'] for m in ai_models[:8])}{'...' if len(ai_models) > 8 else ''})")
        print(f"Services    : {r['service_count']} available / {len(all_reg_svcs)} regional services")
        print("-" * 76)
        for idx, sname in enumerate(r["services"], 1):
            print(f"  {idx:>3}. {sname}")
        if missing:
            print("-" * 76)
            print(f"Not Available in {r['region_id']} ({len(missing)}): {', '.join(missing[:20])}{'...' if len(missing) > 20 else ''}")
        print()


def cmd_compare(catalog: dict[str, Any], region_ids: list[str], diff_only: bool = False) -> None:
    reg_map = {r["region_id"]: r for r in catalog["regions"]}
    valid_rids = [rid for rid in region_ids if rid in reg_map]
    if len(valid_rids) < 2:
        print("Please provide at least 2 valid region codes (e.g. us-central1 europe-west1 asia-south1).")
        sys.exit(1)

    header = f"{'Google Cloud Service':<38} | " + " | ".join(f"{rid:<15}" for rid in valid_rids)
    print("=" * len(header))
    print(header)
    print("-" * len(header))
    for s in catalog["services"]:
        if s["region_count"] == 0:
            continue
        flags = [rid in s["regions"] for rid in valid_rids]
        if diff_only and (all(flags) or not any(flags)):
            continue
        cols = " | ".join(f"{'✔ Available':<15}" if ok else f"{'✖ Missing':<15}" for ok in flags)
        print(f"{s['name'][:38]:<38} | {cols}")
    print("=" * len(header))


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Cloud Services, AI Models & Regional Capabilities CLI (Unofficial)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show local cache status and summary metrics")

    p_svc = sub.add_parser("service", help="Query regions and API capabilities for a Google Cloud service")
    p_svc.add_argument("query", help="Service name or API substring (e.g. 'Vertex AI', 'alloydb', 'run')")

    p_mod = sub.add_parser("models", help="Check which AI & Foundation models are available across Google Cloud regions")
    p_mod.add_argument("query", nargs="?", default="", help="Optional model name, ID, family, or modality (e.g. 'gemini', 'claude', 'veo', 'llama')")
    p_mod.add_argument("--region", default="", help="Optional region code or endpoint filter (e.g. 'us-central1', 'europe-west1', 'global')")

    p_reg = sub.add_parser("region", help="Query available services, AI models, zones, and hardware for a Google Cloud region")
    p_reg.add_argument("query", help="Region code or city name (e.g. 'us-central1', 'mumbai', 'tokyo')")

    p_cmp = sub.add_parser("compare", help="Compare service availability across multiple Google Cloud regions")
    p_cmp.add_argument("regions", nargs="+", help="2 or more region codes (e.g. us-central1 europe-west1 asia-south1)")
    p_cmp.add_argument("--diff", action="store_true", help="Show only services where availability differs")

    p_ref = sub.add_parser("refresh", help="Refresh Google Cloud API catalog cache and rebuild static HTML site")
    p_ref.add_argument("--force", action="store_true", help="Force live API harvest even if 24h cache is still fresh")

    args = parser.parse_args()
    if args.cmd == "refresh":
        cat = harvest_all(force_refresh=args.force)
        generate_all(cat)
        return

    catalog = load_cached_catalog()
    if args.cmd == "status":
        cmd_status(catalog)
    elif args.cmd == "service":
        cmd_service(catalog, args.query)
    elif args.cmd == "models":
        cmd_models(catalog, args.query, args.region)
    elif args.cmd == "region":
        cmd_region(catalog, args.query)
    elif args.cmd == "compare":
        cmd_compare(catalog, args.regions, diff_only=args.diff)


if __name__ == "__main__":
    main()

