#!/usr/bin/env python3
"""
SLA, Regional FinOps Pricing, Official Release Notes & Compact Mobile Payload Enrichment (enrichment.py).

Uses 100% Python 3.10+ standard library only (xml.etree.ElementTree, re, html, json, hashlib).
All network fetches run strictly through harvester.ResilientFetcher with 24h local caching.
"""

from __future__ import annotations

import hashlib
import html as html_lib
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET


MINUTES_PER_MONTH = 43830.0  # 365.25 / 12 * 24 * 60


def format_downtime_minutes(uptime_pct: float) -> tuple[str, str]:
    """Return human-readable (max_monthly_downtime, max_annual_downtime) for a given uptime percentage."""
    if uptime_pct >= 100.0:
        return ("0s / mo", "0s / yr")
    loss_ratio = max(0.0, (100.0 - uptime_pct) / 100.0)
    monthly_sec = round(MINUTES_PER_MONTH * 60.0 * loss_ratio)
    annual_sec = monthly_sec * 12

    def _fmt(sec: int, suffix: str) -> str:
        if sec < 60:
            return f"{sec}s / {suffix}"
        mins, rem_s = divmod(sec, 60)
        if mins < 60:
            return f"{mins}m {rem_s}s / {suffix}" if rem_s else f"{mins}m / {suffix}"
        hrs, rem_m = divmod(mins, 60)
        return f"{hrs}h {rem_m}m / {suffix}"

    return (_fmt(monthly_sec, "mo"), _fmt(annual_sec, "yr"))


def _make_tier(label: str, uptime_pct: float, topology: str) -> dict[str, Any]:
    mo_dt, yr_dt = format_downtime_minutes(uptime_pct)
    pct_str = "100%" if uptime_pct >= 100.0 else f"{uptime_pct:g}%"
    return {
        "tier_name": label,
        "uptime_pct": uptime_pct,
        "uptime_display": pct_str,
        "max_monthly_downtime": mo_dt,
        "max_annual_downtime": yr_dt,
        "topology": topology,
    }


STANDARD_CREDITS_99_99 = [
    {"threshold": "99.0% – < 99.99%", "credit_pct": "10%"},
    {"threshold": "95.0% – < 99.0%", "credit_pct": "25%"},
    {"threshold": "< 95.0%", "credit_pct": "50%"},
]

STANDARD_CREDITS_99_95 = [
    {"threshold": "99.0% – < 99.95%", "credit_pct": "10%"},
    {"threshold": "95.0% – < 99.0%", "credit_pct": "25%"},
    {"threshold": "< 95.0%", "credit_pct": "50%"},
]

STANDARD_CREDITS_99_9 = [
    {"threshold": "99.0% – < 99.9%", "credit_pct": "10%"},
    {"threshold": "95.0% – < 99.0%", "credit_pct": "25%"},
    {"threshold": "< 95.0%", "credit_pct": "50%"},
]

SPANNER_CREDITS_99_999 = [
    {"threshold": "99.9% – < 99.999%", "credit_pct": "10%"},
    {"threshold": "99.0% – < 99.9%", "credit_pct": "25%"},
    {"threshold": "< 99.0%", "credit_pct": "50%"},
]


# Curated architectural SLA profiles for core Google Cloud services
CURATED_SLA_PROFILES: dict[str, dict[str, Any]] = {
    "Cloud DNS": {
        "sla_slug": "cloud-dns",
        "tiers": [
            _make_tier("Global Authoritative Anycast", 100.0, "Global Anycast name servers across all PoPs"),
        ],
        "credits": [{"threshold": "< 100%", "credit_pct": "10% – 50%"}],
        "ha_requirements": [
            "Use managed Cloud DNS public or private zones with Google Cloud Anycast name servers.",
            "Avoid single-region custom forwarding bottlenecks for authoritative resolution.",
        ],
    },
    "Cloud Spanner": {
        "sla_slug": "cloud-spanner",
        "tiers": [
            _make_tier("Multi-Region Configuration", 99.999, "Multi-region instance (quorum across 2+ regions + witness)"),
            _make_tier("Regional Configuration", 99.99, "Regional instance (synchronous replication across 3 zones)"),
        ],
        "credits": SPANNER_CREDITS_99_999,
        "ha_requirements": [
            "Select a multi-region instance config (e.g., nam-eur-asia1, nam3, eur6) for 99.999% uptime.",
            "Provision sufficient compute capacity (nodes/processing units) to keep high-priority CPU < 65%.",
        ],
    },
    "Firestore": {
        "sla_slug": "firestore",
        "tiers": [
            _make_tier("Multi-Region (nam5 / eur3)", 99.999, "Multi-region database location with automatic synchronous replication"),
            _make_tier("Regional Location", 99.99, "Single-region multi-zone replication"),
        ],
        "credits": SPANNER_CREDITS_99_999,
        "ha_requirements": [
            "Deploy database in multi-region location (nam5 or eur3) for 99.999% availability.",
            "Implement exponential backoff retries in client SDKs on transient ABORTED/UNAVAILABLE statuses.",
        ],
    },
    "Cloud Bigtable": {
        "sla_slug": "bigtable",
        "tiers": [
            _make_tier("Multi-Cluster Replicated (3+ Regions/Zones)", 99.999, "Multi-cluster routing across 3+ zones in multiple regions"),
            _make_tier("Multi-Cluster Same Region (2+ Zones)", 99.99, "Replicated instance with multi-cluster app profile"),
            _make_tier("Single-Cluster Instance", 99.9, "Single-zone cluster with single-cluster routing"),
        ],
        "credits": SPANNER_CREDITS_99_999,
        "ha_requirements": [
            "Configure a multi-cluster routing policy in your App Profile across 2+ clusters.",
            "Enable automatic cluster autoscaling with sufficient headroom for failover traffic.",
        ],
    },
    "AlloyDB": {
        "sla_slug": "alloydb",
        "tiers": [
            _make_tier("Regional High Availability (Maintenance Inclusive)", 99.99, "Primary instance with active HA standby across separate zones"),
            _make_tier("Basic / Zonal Primary", 99.5, "Single-zone non-HA instance (dev/test only)"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Configure Primary Instance in High Availability (HA) mode (includes planned maintenance within 99.99%).",
            "Add Cross-Region Read Pool replicas for full regional disaster recovery.",
        ],
    },
    "Cloud SQL": {
        "sla_slug": "cloud-sql",
        "tiers": [
            _make_tier("Enterprise Plus Edition (Regional HA)", 99.99, "Enterprise Plus HA primary + synchronous zonal standby (near-zero downtime)"),
            _make_tier("Enterprise Edition (Regional HA)", 99.95, "Regional HA configuration with automatic zonal failover"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Enable High Availability (Regional) on the primary instance; single-zone instances are not covered by the HA SLA.",
            "Use Cloud SQL Auth Proxy or connection pooling with automatic reconnect on failover.",
        ],
    },
    "BigQuery": {
        "sla_slug": "bigquery",
        "tiers": [
            _make_tier("Query, Storage & Streaming Engine", 99.99, "Regional and Multi-Region (US / EU) datasets & reservations"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Automatic multi-zone durability within Regional or US/EU Multi-Region locations.",
            "Use Cross-Region Dataset Replication for sub-RPO regional disaster recovery.",
        ],
    },
    "Compute Engine": {
        "sla_slug": "compute",
        "tiers": [
            _make_tier("Multi-Zone / Regional Architecture", 99.99, "Instances spread across 2+ zones in a Region behind Load Balancing"),
            _make_tier("Single Instance", 99.5, "Single VM with Live Migration enabled on standard Persistent Disk / Hyperdisk"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Deploy Regional Managed Instance Groups (MIGs) across at least 2 (ideally 3) availability zones.",
            "Set Maintenance Policy to MIGRATE (Spot/Preemptible VMs and some GPUs without live migration require multi-zone redundancy).",
        ],
    },
    "Google Kubernetes Engine": {
        "sla_slug": "kubernetes-engine",
        "tiers": [
            _make_tier("Regional Control Plane & Autopilot Pods", 99.95, "Regional GKE cluster control plane & multi-zone worker pools"),
            _make_tier("Zonal Cluster Control Plane", 99.5, "Single-zone control plane"),
        ],
        "credits": STANDARD_CREDITS_99_95,
        "ha_requirements": [
            "Use Regional GKE Standard or Autopilot clusters with PodTopologySpreadConstraints across 3 zones.",
            "Define PodDisruptionBudgets (PDBs) and readiness probes for zero-downtime rolling upgrades.",
        ],
    },
    "Cloud Run": {
        "sla_slug": "cloud-run",
        "tiers": [
            _make_tier("Regional Serverless Service", 99.95, "Automatic multi-zone redundancy within selected region"),
            _make_tier("Multi-Region behind Global External LB", 99.99, "Composite architecture with Global Load Balancer + 2+ regions"),
        ],
        "credits": STANDARD_CREDITS_99_95,
        "ha_requirements": [
            "Keep minimum instances >= 1 for latency-sensitive synchronous APIs to eliminate cold starts.",
            "Pair with Global External Application Load Balancer + Serverless NEGs across 2+ regions for >99.99% availability.",
        ],
    },
    "Cloud Storage": {
        "sla_slug": "cloud-storage",
        "tiers": [
            _make_tier("Multi-Region / Dual-Region (Turbo Replication)", 99.99, "Standard Storage in Dual/Multi-Region with 15-min RPO Turbo Replication"),
            _make_tier("Multi-Region / Dual-Region Standard", 99.95, "Geo-redundant Standard Storage"),
            _make_tier("Regional Standard Storage", 99.9, "Multi-zone redundant within a single region (Nearline/Coldline: 99.0%)"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Choose Dual-Region with Turbo Replication when cross-region RPO < 15 minutes and 99.99% SLA are required.",
            "Implement truncated exponential backoff for HTTP 429/5xx object operations.",
        ],
    },
    "Cloud Load Balancing": {
        "sla_slug": "cloud-load-balancing",
        "tiers": [
            _make_tier("Global & Multi-Zone Load Balancing", 99.99, "Global Anycast frontends + backends in 2+ zones/regions"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Deploy healthy backend instances or Serverless NEGs in at least two distinct zones or regions.",
        ],
    },
    "Cloud Armor": {
        "sla_slug": "cloud-armor",
        "tiers": [
            _make_tier("Global Edge WAF & DDoS Protection", 99.99, "Attached to Global External Application Load Balancer"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Attach security policies to Global External Application or Classic Load Balancers with multi-zone backends.",
        ],
    },
    "Cloud Interconnect": {
        "sla_slug": "cloud-interconnect",
        "tiers": [
            _make_tier("Production Critical (99.99% Topology)", 99.99, "4 redundant connections across 2 Edge Availability Domains in 2 metros"),
            _make_tier("Production Non-Critical (99.9% Topology)", 99.9, "2 redundant connections across 2 EADs in 1 metro"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Terminate VLAN attachments on redundant Cloud Routers with Global Dynamic Routing enabled in the VPC.",
        ],
    },
    "Cloud VPN": {
        "sla_slug": "cloud-vpn",
        "tiers": [
            _make_tier("HA VPN (2 Interfaces / Active-Active or Active-Passive)", 99.99, "HA VPN gateway with both interfaces connected to peer gateway(s)"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Use HA VPN (not Classic VPN) with tunnels configured on both interface 0 and interface 1 + BGP dynamic routing.",
        ],
    },
    "Vertex AI": {
        "sla_slug": "vertex-ai",
        "tiers": [
            _make_tier("Online Prediction, Gemini API & Vector Search", 99.9, "Regional or global managed prediction endpoints"),
        ],
        "credits": STANDARD_CREDITS_99_9,
        "ha_requirements": [
            "Use Provisioned Throughput or global endpoint routing for predictable enterprise GenAI capacity.",
            "Configure multi-region endpoint failover for mission-critical inference pipelines.",
        ],
    },
    "Pub/Sub": {
        "sla_slug": "pubsub",
        "tiers": [
            _make_tier("Global / Regional Message Bus", 99.95, "Synchronous multi-zone message storage & delivery"),
        ],
        "credits": STANDARD_CREDITS_99_95,
        "ha_requirements": [
            "Configure dead-letter topics and exponential retry policies on push/pull subscriptions.",
        ],
    },
    "Secret Manager": {
        "sla_slug": "secret-manager",
        "tiers": [
            _make_tier("Automatic Global or Multi-Region Replication", 99.95, "Replicated secrets across multiple zones/regions"),
        ],
        "credits": STANDARD_CREDITS_99_95,
        "ha_requirements": [
            "Use automatic replication or user-managed replication across 2+ regions when constrained by data residency.",
        ],
    },
    "Cloud KMS": {
        "sla_slug": "cloud-kms",
        "tiers": [
            _make_tier("Multi-Region / Global Key Ring", 99.99, "Geo-redundant cryptographic key operations"),
            _make_tier("Single-Region Key Ring", 99.95, "Multi-zone regional key operations"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Align KMS key ring location with encrypted resource location (e.g., dual-region KMS for dual-region GCS buckets).",
        ],
    },
    "Apigee": {
        "sla_slug": "apigee",
        "tiers": [
            _make_tier("Multi-Region Runtime Deployment", 99.99, "Active-active Apigee X instances across 2+ regions behind Global LB"),
            _make_tier("Single-Region Runtime Deployment", 99.9, "Multi-zone Apigee X instance in 1 region"),
        ],
        "credits": STANDARD_CREDITS_99_99,
        "ha_requirements": [
            "Provision Apigee runtime instances in at least 2 Google Cloud regions with Global External Load Balancing.",
        ],
    },
    "Memorystore": {
        "sla_slug": "memorystore",
        "tiers": [
            _make_tier("Standard / Cluster High Availability Tier", 99.9, "Cross-zone primary + replica with automatic failover"),
        ],
        "credits": STANDARD_CREDITS_99_9,
        "ha_requirements": [
            "Deploy Standard HA or Redis Cluster / Valkey multi-zone replicas (Basic tier has no SLA).",
        ],
    },
}

NO_FORMAL_SLA_SERVICES = {
    "Cloud Shell",
    "Cloud Deployment Manager",
    "Application Design Center",
    "Cloud Source Repositories",
}


def harvest_sla_links(fetcher: Any, raw_cache_dir: Path) -> dict[str, str]:
    """Fetch https://cloud.google.com/terms/sla and return normalized_name -> official SLA URL."""
    discovered: dict[str, str] = {}
    try:
        raw_html = fetcher.fetch_text(
            "https://cloud.google.com/terms/sla",
            cache_path=raw_cache_dir / "sla_index.html",
            timeout=15,
        )
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']*?/terms/sla/[^"\'#?]+)["\'][^>]*>(.*?)</a>', raw_html, re.I | re.S):
            href = m.group(1).strip()
            if href.startswith("/"):
                href = f"https://cloud.google.com{href}"
            label = re.sub(r"<[^>]+>", " ", m.group(2))
            label = html_lib.unescape(re.sub(r"\s+", " ", label)).strip()
            norm = re.sub(r"[^a-z0-9]", "", label.lower().replace("google", "").replace("cloud", "").replace("sla", ""))
            if norm:
                discovered[norm] = href
            slug_part = href.rstrip("/").split("/")[-1].lower()
            discovered[re.sub(r"[^a-z0-9]", "", slug_part)] = href
    except Exception:
        pass
    return discovered


def build_service_sla(service: dict[str, Any], discovered_sla_links: dict[str, str]) -> dict[str, Any]:
    """Build structured SLA metadata for any Google Cloud service."""
    pname = service["name"]
    category = service.get("category", "")
    scope = service.get("scope", "Regional")

    if pname in NO_FORMAL_SLA_SERVICES:
        return {
            "has_formal_sla": False,
            "headline_uptime_pct": 0.0,
            "headline_display": "No Formal SLA (Free / Tooling)",
            "max_monthly_downtime": "Best-effort",
            "sla_url": "https://cloud.google.com/terms/sla",
            "tiers": [],
            "credit_schedule": [],
            "ha_requirements": [
                "Developer/management tooling intended for interactive or build-time workflows; do not place in synchronous production request paths."
            ],
        }

    norm_name = re.sub(r"[^a-z0-9]", "", pname.lower().replace("google", "").replace("cloud", ""))
    # Check curated exact, normalized, or substring match
    matched_profile = CURATED_SLA_PROFILES.get(pname)
    if not matched_profile:
        for k, prof in CURATED_SLA_PROFILES.items():
            norm_k = re.sub(r"[^a-z0-9]", "", k.lower().replace("google", "").replace("cloud", ""))
            if k.lower() in pname.lower() or (norm_k and norm_k == norm_name):
                matched_profile = prof
                break

    sla_url = discovered_sla_links.get(norm_name, "")

    if matched_profile:
        if not sla_url:
            sla_url = f"https://cloud.google.com/terms/sla/{matched_profile['sla_slug']}"
        top_tier = matched_profile["tiers"][0]
        return {
            "has_formal_sla": True,
            "headline_uptime_pct": top_tier["uptime_pct"],
            "headline_display": top_tier["uptime_display"],
            "max_monthly_downtime": top_tier["max_monthly_downtime"],
            "sla_url": sla_url,
            "tiers": matched_profile["tiers"],
            "credit_schedule": matched_profile["credits"],
            "ha_requirements": matched_profile["ha_requirements"],
        }

    # Intelligent dynamic inference for remaining or newly launched Google Cloud services
    cat_lower = category.lower()
    if "Multi-Region" in scope or "Global" in scope:
        if any(tok in cat_lower for tok in ("network", "security", "storage", "database")):
            tiers = [
                _make_tier("Multi-Region / Global Redundant", 99.99, "Geo-redundant or Anycast multi-region deployment"),
                _make_tier("Single-Region Multi-Zone", 99.95, "Regional multi-zone deployment"),
            ]
            credits = STANDARD_CREDITS_99_99
        else:
            tiers = [
                _make_tier("Multi-Region / Global Endpoint", 99.95, "Managed multi-region / global service endpoint"),
                _make_tier("Regional Endpoint", 99.9, "Single-region managed endpoint"),
            ]
            credits = STANDARD_CREDITS_99_95
        ha_reqs = [
            "Deploy using multi-region or dual-region endpoints where supported by data residency rules.",
            "Implement client-side retries with exponential backoff and jitter.",
        ]
    elif any(tok in cat_lower for tok in ("database", "storage", "data", "analytics", "serverless", "containers")):
        tiers = [
            _make_tier("Regional High Availability (Multi-Zone)", 99.95, "Managed multi-zone regional deployment"),
            _make_tier("Zonal / Standard Deployment", 99.9, "Single-zone or standard regional resource"),
        ]
        credits = STANDARD_CREDITS_99_95
        ha_reqs = [
            "Enable multi-zone High Availability (HA) within the region and avoid single-zone resource pinning.",
            "Pair with a secondary DR region if business continuity requires survival of a full regional outage.",
        ]
    else:
        tiers = [
            _make_tier("Managed Regional Service", 99.9, "Standard managed regional endpoint"),
        ]
        credits = STANDARD_CREDITS_99_9
        ha_reqs = [
            "Use regional endpoints closest to workloads and implement idempotent retry logic for transient 5xx responses.",
        ]

    top = tiers[0]
    return {
        "has_formal_sla": True,
        "headline_uptime_pct": top["uptime_pct"],
        "headline_display": top["uptime_display"],
        "max_monthly_downtime": top["max_monthly_downtime"],
        "sla_url": sla_url or "https://cloud.google.com/terms/sla",
        "tiers": tiers,
        "credit_schedule": credits,
        "ha_requirements": ha_reqs,
    }


# Baseline relative Compute/Storage cost multipliers vs. us-central1 (Iowa) = 1.00x
REGION_COST_INDEX: dict[str, tuple[float, float, str]] = {
    "us-central1": (1.00, 1.00, "Tier 1 — Baseline"),
    "us-east1": (1.00, 1.00, "Tier 1 — Baseline"),
    "us-west1": (1.00, 1.00, "Tier 1 — Baseline"),
    "us-south1": (1.06, 1.05, "Tier 1 — Baseline"),
    "us-east5": (1.04, 1.05, "Tier 1 — Baseline"),
    "us-east4": (1.11, 1.15, "Tier 2 — Moderate"),
    "us-west2": (1.20, 1.15, "Tier 2 — Moderate"),
    "us-west3": (1.20, 1.15, "Tier 2 — Moderate"),
    "us-west4": (1.11, 1.15, "Tier 2 — Moderate"),
    "northamerica-northeast1": (1.10, 1.10, "Tier 2 — Moderate"),
    "northamerica-northeast2": (1.10, 1.15, "Tier 2 — Moderate"),
    "northamerica-south1": (1.14, 1.15, "Tier 2 — Moderate"),
    "southamerica-east1": (1.48, 1.75, "Tier 3 — Premium"),
    "southamerica-west1": (1.36, 1.50, "Tier 3 — Premium"),
    "europe-west1": (1.10, 1.00, "Tier 1 — Baseline"),
    "europe-west4": (1.10, 1.00, "Tier 1 — Baseline"),
    "europe-north1": (1.10, 1.00, "Tier 1 — Baseline"),
    "europe-north2": (1.12, 1.05, "Tier 2 — Moderate"),
    "europe-central2": (1.22, 1.15, "Tier 2 — Moderate"),
    "europe-southwest1": (1.18, 1.15, "Tier 2 — Moderate"),
    "europe-west2": (1.24, 1.15, "Tier 2 — Moderate"),
    "europe-west3": (1.24, 1.15, "Tier 2 — Moderate"),
    "europe-west6": (1.40, 1.25, "Tier 3 — Premium"),
    "europe-west8": (1.20, 1.15, "Tier 2 — Moderate"),
    "europe-west9": (1.20, 1.15, "Tier 2 — Moderate"),
    "europe-west10": (1.24, 1.15, "Tier 2 — Moderate"),
    "europe-west12": (1.20, 1.15, "Tier 2 — Moderate"),
    "asia-east1": (1.16, 1.00, "Tier 2 — Moderate"),
    "asia-east2": (1.34, 1.15, "Tier 3 — Premium"),
    "asia-northeast1": (1.28, 1.15, "Tier 3 — Premium"),
    "asia-northeast2": (1.28, 1.15, "Tier 3 — Premium"),
    "asia-northeast3": (1.28, 1.15, "Tier 3 — Premium"),
    "asia-south1": (1.12, 1.15, "Tier 2 — Moderate"),
    "asia-south2": (1.16, 1.15, "Tier 2 — Moderate"),
    "asia-southeast1": (1.18, 1.00, "Tier 2 — Moderate"),
    "asia-southeast2": (1.24, 1.15, "Tier 2 — Moderate"),
    "asia-southeast3": (1.20, 1.15, "Tier 2 — Moderate"),
    "australia-southeast1": (1.32, 1.15, "Tier 3 — Premium"),
    "australia-southeast2": (1.32, 1.15, "Tier 3 — Premium"),
    "me-west1": (1.22, 1.15, "Tier 2 — Moderate"),
    "me-central1": (1.30, 1.20, "Tier 3 — Premium"),
    "me-central2": (1.30, 1.20, "Tier 3 — Premium"),
    "africa-south1": (1.34, 1.20, "Tier 3 — Premium"),
}


def build_region_pricing(region: dict[str, Any]) -> dict[str, Any]:
    """Attach relative FinOps cost index and CUD/egress summary to a Google Cloud region."""
    rid = region["region_id"]
    if rid in REGION_COST_INDEX:
        comp_idx, stor_idx, tier = REGION_COST_INDEX[rid]
    elif rid.startswith("us-"):
        comp_idx, stor_idx, tier = (1.08, 1.10, "Tier 1 — Baseline")
    elif rid.startswith("europe-"):
        comp_idx, stor_idx, tier = (1.20, 1.15, "Tier 2 — Moderate")
    elif rid.startswith("asia-"):
        comp_idx, stor_idx, tier = (1.22, 1.15, "Tier 2 — Moderate")
    else:
        comp_idx, stor_idx, tier = (1.28, 1.20, "Tier 3 — Premium")

    delta_pct = round((comp_idx - 1.0) * 100)
    delta_label = "Baseline (0%)" if delta_pct == 0 else f"+{delta_pct}% vs us-central1"

    if rid.startswith(("us-", "northamerica-")):
        egress = "$0.01–$0.02/GiB intra-NA • $0.08–$0.12/GiB global"
    elif rid.startswith("europe-"):
        egress = "$0.01–$0.02/GiB intra-EU • $0.08–$0.12/GiB global"
    else:
        egress = "$0.05–$0.08/GiB regional • $0.11–$0.15/GiB global"

    return {
        "tier": tier,
        "relative_compute_index": comp_idx,
        "relative_storage_index": stor_idx,
        "delta_vs_baseline": delta_label,
        "inter_region_egress_band": egress,
        "cud_1y_discount_pct": 37,
        "cud_3y_discount_pct": 55,
    }


CURATED_SERVICE_PRICING: dict[str, dict[str, Any]] = {
    "Compute Engine": {
        "billing_model": "Per-second vCPU + Memory + Persistent Disk / Hyperdisk",
        "primary_units": "vCPU-hour • GiB-hour • GiB-month + IOPS/Throughput",
        "has_free_tier": True,
        "free_tier_note": "1 non-preemptible e2-micro/mo in us-west1, us-central1, or us-east1 + 30 GB Standard PD",
        "cud_support": "1Y (37% off) / 3Y (55–70% off) Resource & Flexible CUDs",
        "spot_or_batch_discount": True,
        "discount_note": "Spot VMs offer 60%–91% discount for fault-tolerant workloads",
        "cost_drivers": [
            "Cross-zone ($0.01/GiB) & internet egress bandwidth",
            "Hyperdisk Extreme / Balanced provisioned IOPS & throughput",
            "Unattached Persistent Disks & idle static external IPs",
        ],
    },
    "Google Kubernetes Engine": {
        "billing_model": "Cluster Management Fee + Worker Compute (Standard) or Pod Resource Request (Autopilot)",
        "primary_units": "$0.10/cluster-hr (after 1 free cluster) + vCPU-hr & GiB-hr",
        "has_free_tier": True,
        "free_tier_note": "$74.40/mo cluster management credit (covers 1 zonal or regional cluster fee)",
        "cud_support": "1Y / 3Y Compute Flexible CUDs (Autopilot & Standard)",
        "spot_or_batch_discount": True,
        "discount_note": "Spot Pods & Spot Node Pools save up to 60%–91%",
        "cost_drivers": [
            "Over-provisioned Pod CPU/memory requests in Autopilot",
            "Multi-zone inter-pod network chatter across AZs",
            "GKE Enterprise tier per-vCPU fleet management fee if enabled",
        ],
    },
    "Cloud Run": {
        "billing_model": "Serverless Pay-per-Use (Request-based or Instance-based billing)",
        "primary_units": "vCPU-second • GiB-second • per-1M requests",
        "has_free_tier": True,
        "free_tier_note": "2M requests + 180,000 vCPU-sec + 360,000 GiB-sec free every month",
        "cud_support": "1Y (17% off) / 3Y Compute Flexible Spend CUDs",
        "spot_or_batch_discount": False,
        "discount_note": "Scale-to-zero eliminates idle compute cost when min-instances = 0",
        "cost_drivers": [
            "Minimum instances > 0 kept warm 24x7",
            "Instance-based (CPU always allocated) vs request-based billing selection",
            "VPC Direct Egress / Serverless VPC Access throughput",
        ],
    },
    "Vertex AI": {
        "billing_model": "Token-metered GenAI APIs / Provisioned Throughput / GPU Node-hour",
        "primary_units": "1M Input & Output Tokens • GSU/PTU-hour • Accelerator-hour",
        "has_free_tier": False,
        "free_tier_note": "New-customer $300 Google Cloud trial credits apply",
        "cud_support": "Provisioned Throughput subscriptions (monthly / 1Y commitments)",
        "spot_or_batch_discount": True,
        "discount_note": "Batch Prediction & Gemini Context Caching save 50%–75% on token costs",
        "cost_drivers": [
            "Long-context output tokens & thinking tokens without Context Caching",
            "24x7 idle dedicated GPU prediction endpoints without autoscaling",
            "Vector Search index shard memory sizing",
        ],
    },
    "BigQuery": {
        "billing_model": "On-Demand (per TiB scanned) or Capacity Editions (Autoscaling Slot-hours)",
        "primary_units": "$6.25/TiB scanned (On-Demand) or Slot-hour + Active/Long-Term Logical/Physical GiB-mo",
        "has_free_tier": True,
        "free_tier_note": "1 TiB query processing/mo + 10 GiB active storage/mo free",
        "cud_support": "1Y (20% off) / 3Y (40% off) Enterprise & Enterprise Plus Slot Commitments",
        "spot_or_batch_discount": True,
        "discount_note": "Long-term unmodified partitions automatically drop ~50% in storage price after 90 days",
        "cost_drivers": [
            "Unpartitioned / unclustered SELECT * full-table scans in On-Demand mode",
            "High max-slots cap in Autoscaling Editions during spiky BI concurrency",
            "Physical vs Logical storage billing model choice for high-compression tables",
        ],
    },
    "Cloud Spanner": {
        "billing_model": "Provisioned Compute Capacity (Processing Units / Nodes) + Database Storage + Backups",
        "primary_units": "100 Processing Units-hr (0.1 Node) • GiB-month",
        "has_free_tier": True,
        "free_tier_note": "90-day free trial instance available once per billing account",
        "cud_support": "1Y (20% off) / 3Y (40% off) Spanner Compute Capacity CUDs",
        "spot_or_batch_discount": False,
        "discount_note": "Granular sizing down to 100 Processing Units (~$65/mo regional entry)",
        "cost_drivers": [
            "Multi-region instance (~3x–4.5x compute & storage multiplier vs single-region)",
            "Spanner Enterprise Plus vs Standard edition feature tier",
            "Cross-region data replication & backup retention windows",
        ],
    },
    "AlloyDB": {
        "billing_model": "vCPU + RAM per Primary/Read-Pool Node + Regional Auto-Scaling Storage + I/O",
        "primary_units": "vCPU-hour • GiB-hour • GiB-month",
        "has_free_tier": False,
        "free_tier_note": "Eligible for free trial cluster credits on qualifying accounts",
        "cud_support": "1Y (25% off) / 3Y (52% off) AlloyDB Spend CUDs",
        "spot_or_batch_discount": False,
        "discount_note": "Storage scales automatically and is billed only for actual bytes used (no pre-provisioning)",
        "cost_drivers": [
            "HA Primary (2x zonal compute for active + standby) plus Read Pool node count",
            "Cross-region Read Pool replication egress",
            "Continuous backup & point-in-time recovery retention window",
        ],
    },
    "Cloud SQL": {
        "billing_model": "Instance vCPU + Memory + Provisioned SSD/HDD Storage + HA Multiplier",
        "primary_units": "vCPU-hour • GiB-hour • GiB-month",
        "has_free_tier": False,
        "free_tier_note": "Shared-core db-f1-micro / db-g1-small available for low-cost dev (~$9/mo)",
        "cud_support": "1Y (25% off) / 3Y (52% off) Cloud SQL Spend CUDs",
        "spot_or_batch_discount": False,
        "discount_note": "Regional HA doubles instance compute & storage for synchronous standby",
        "cost_drivers": [
            "Enterprise Plus vs Enterprise edition multiplier (~1.3x–1.4x for 99.99% SLA & Data Cache)",
            "Regional HA standby doubling compute + disk capacity",
            "Over-provisioned SSD storage (storage auto-increases cannot be shrunk in-place)",
        ],
    },
    "Cloud Storage": {
        "billing_model": "Data Volume by Storage Class + Class A/B Operations + Retrieval & Network Egress",
        "primary_units": "GiB-month • per-10k operations • GiB egress",
        "has_free_tier": True,
        "free_tier_note": "5 GB-months Regional Standard Storage (US regions) + 5k Class A / 50k Class B ops",
        "cud_support": "Autoclass automatic lifecycle tiering (no upfront lock-in required)",
        "spot_or_batch_discount": False,
        "discount_note": "Archive Storage drops storage floor to ~$0.0012/GiB-month",
        "cost_drivers": [
            "Early deletion / retrieval fees on Nearline (30d), Coldline (90d), and Archive (365d)",
            "Dual-region / Multi-region replication & Turbo Replication write fees",
            "High-frequency small-object Class A LIST/PUT operations",
        ],
    },
}


def build_service_pricing(service: dict[str, Any]) -> dict[str, Any]:
    """Build structured FinOps & pricing profile for any Google Cloud service."""
    pname = service["name"]
    category = service.get("category", "")
    url = service.get("url", "https://cloud.google.com/pricing")
    pricing_url = (
        f"{url.rstrip('/')}/pricing"
        if url.startswith("https://cloud.google.com/") and "/about/" not in url and "#" not in url
        else "https://cloud.google.com/pricing/list"
    )

    norm_name = re.sub(r"[^a-z0-9]", "", pname.lower().replace("google", "").replace("cloud", ""))
    matched = CURATED_SERVICE_PRICING.get(pname)
    if not matched:
        for k, prof in CURATED_SERVICE_PRICING.items():
            norm_k = re.sub(r"[^a-z0-9]", "", k.lower().replace("google", "").replace("cloud", ""))
            if k.lower() in pname.lower() or (norm_k and norm_k == norm_name):
                matched = prof
                break

    if matched:
        out = dict(matched)
        out["pricing_url"] = pricing_url
        return out

    cat_lower = category.lower()
    if any(t in cat_lower for t in ("ai", "machine learning")):
        return {
            "pricing_url": pricing_url,
            "billing_model": "Usage-Metered API Calls / Tokens / Compute Node-Hours",
            "primary_units": "per-1k units / 1M tokens / accelerator-hour",
            "has_free_tier": True,
            "free_tier_note": "Monthly free usage units on select Vision, Speech, Translation & NLP APIs",
            "cud_support": "Provisioned Throughput / Compute CUDs on dedicated nodes",
            "spot_or_batch_discount": True,
            "discount_note": "Offline / asynchronous batch processing typically discounted vs real-time",
            "cost_drivers": [
                "Synchronous real-time vs batch inference volume",
                "Media duration (audio minutes / video seconds / document pages)",
                "Dedicated endpoint minimum replica count",
            ],
        }
    if any(t in cat_lower for t in ("database", "storage")):
        return {
            "pricing_url": pricing_url,
            "billing_model": "Provisioned or Serverless Capacity + Replicated Storage + I/O",
            "primary_units": "GiB-month • vCPU/Node-hour • I/O operations",
            "has_free_tier": False,
            "free_tier_note": "Pay-as-you-go with zero upfront license cost",
            "cud_support": "1Y (20–25% off) / 3Y (40–52% off) Spend Commitments on eligible engines",
            "spot_or_batch_discount": False,
            "discount_note": "Lower storage tiers & regional placement reduce baseline spend",
            "cost_drivers": [
                "Multi-region vs single-region HA replication topology",
                "Backup retention & point-in-time recovery log volume",
                "Cross-region read replica network egress",
            ],
        }
    if any(t in cat_lower for t in ("network", "security")):
        return {
            "pricing_url": pricing_url,
            "billing_model": "Hourly Gateway / Policy / Rule Base + Processed Data or Queries",
            "primary_units": "Resource-hour • GiB processed • per-1M requests/queries",
            "has_free_tier": False,
            "free_tier_note": "Core IAM & VPC firewall rules included; advanced tiers metered",
            "cud_support": "Enterprise subscription tiers available (e.g., Cloud Armor Enterprise, SCC Enterprise)",
            "spot_or_batch_discount": False,
            "discount_note": "Private Service Connect & intra-zone traffic minimize egress charges",
            "cost_drivers": [
                "Cross-region / internet data processing & egress volume (GiB)",
                "Number of active forwarding rules, tunnels, or WAF policies",
                "Packet mirroring & VPC Flow Logs sampling ingestion volume",
            ],
        }

    return {
        "pricing_url": pricing_url,
        "billing_model": "Consumption-Based Pay-As-You-Go",
        "primary_units": "Active resource-hours • API operations • GiB ingested",
        "has_free_tier": True,
        "free_tier_note": "Initial monthly free tier quota available on many operations/observability APIs",
        "cud_support": "On-Demand (Spend CUDs where supported)",
        "spot_or_batch_discount": False,
        "discount_note": "Zero upfront minimums; billed strictly on metered consumption",
        "cost_drivers": [
                "High-cardinality log/metric ingestion & retention (>30 days)",
                "Regional price multiplier differences across Tier 1 vs Tier 3 regions",
                "Automated polling frequency on high-scale APIs",
        ],
    }


def harvest_release_notes(
    fetcher: Any,
    raw_cache_dir: Path,
    known_services: list[dict[str, Any]],
    limit: int = 120,
) -> list[dict[str, Any]]:
    """Fetch and parse the official Google Cloud Release Notes Atom XML feed."""
    notes: list[dict[str, Any]] = []
    svc_lookup = sorted(
        [(s["name"], s["slug"], s["category"]) for s in known_services],
        key=lambda x: len(x[0]),
        reverse=True,
    )

    try:
        xml_text = fetcher.fetch_text(
            "https://cloud.google.com/feeds/gcp-release-notes.xml",
            cache_path=raw_cache_dir / "gcp_release_notes.xml",
            timeout=20,
        )
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

        for entry in entries[:limit]:
            updated_el = entry.find("atom:updated", ns)
            title_el = entry.find("atom:title", ns)
            content_el = entry.find("atom:content", ns)
            link_el = entry.find("atom:link", ns)

            raw_date = (updated_el.text or "").strip() if updated_el is not None else ""
            pub_date = raw_date[:10] if len(raw_date) >= 10 else "Recent"
            raw_title = (title_el.text or "").strip() if title_el is not None else "Google Cloud Update"
            href = link_el.attrib.get("href", "https://cloud.google.com/release-notes") if link_el is not None else "https://cloud.google.com/release-notes"
            raw_html = (content_el.text or "") if content_el is not None else ""

            # Detect release badge type (FEATURE, ANNOUNCEMENT, CHANGED, DEPRECATED, FIXED, SECURITY)
            badge_match = re.search(
                r"\b(FEATURE|ANNOUNCEMENT|CHANGED|DEPRECATED|FIXED|SECURITY|ISSUE|BREAKING)\b",
                raw_html.upper() + " " + raw_title.upper(),
            )
            rel_type = badge_match.group(1).title() if badge_match else "Feature"

            # Extract product name from h2/h3 or title or match known service
            h_match = re.search(r"<h[23][^>]*>(.*?)</h[23]>", raw_html, re.I | re.S)
            extracted_prod = ""
            if h_match:
                extracted_prod = html_lib.unescape(re.sub(r"<[^>]+>", " ", h_match.group(1))).strip()

            clean_body = re.sub(r"<h[1-4][^>]*>.*?</h[1-4]>", " ", raw_html, flags=re.I | re.S)
            clean_body = re.sub(r"<[^>]+>", " ", clean_body)
            clean_body = html_lib.unescape(re.sub(r"\s+", " ", clean_body)).strip()
            clean_body = re.sub(r"^(FEATURE|ANNOUNCEMENT|CHANGED|DEPRECATED|FIXED|SECURITY)\s*:?\s*", "", clean_body, flags=re.I)

            matched_name = extracted_prod or raw_title
            matched_slug = ""
            matched_cat = "Google Cloud Platform"
            combined_haystack = f"{extracted_prod} {raw_title} {clean_body[:140]}".lower()
            for sname, sslug, scat in svc_lookup:
                if sname.lower() in combined_haystack:
                    matched_name = sname
                    matched_slug = sslug
                    matched_cat = scat
                    break

            summary = clean_body[:260].rstrip()
            if len(clean_body) > 260:
                summary += "…"

            notes.append(
                {
                    "id": hashlib.sha1(f"{pub_date}:{matched_name}:{summary[:80]}".encode("utf-8")).hexdigest()[:12],
                    "date": pub_date,
                    "release_type": rel_type,
                    "product_name": matched_name,
                    "service_slug": matched_slug,
                    "category": matched_cat,
                    "summary": summary or raw_title,
                    "url": href,
                }
            )
    except Exception as exc:
        print(f"[Harvester] Warning parsing release notes XML feed: {exc}")

    return notes


def build_mobile_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """
    Create a compact, offline-first JSON payload (~550-750 KB) for both the Native iOS App
    and the Offline Web PWA Service Worker, omitting verbose 10,501 REST method schemas.
    """
    compact_services = []
    for s in catalog.get("services", []):
        compact_services.append(
            {
                "name": s["name"],
                "slug": s["slug"],
                "category": s["category"],
                "url": s["url"],
                "scope": s["scope"],
                "is_global": s["is_global"],
                "regions": s["regions"],
                "region_count": s["region_count"],
                "coverage_pct": s["coverage_pct"],
                "multi_regions": s.get("multi_regions", []),
                "api_names": s.get("api_names", []),
                "total_api_methods": s.get("total_api_methods", 0),
                "sla": s.get("sla", {}),
                "pricing": s.get("pricing", {}),
            }
        )

    compact_regions = []
    for r in catalog.get("regions", []):
        compact_regions.append(
            {
                "region_id": r["region_id"],
                "region_name": r["region_name"],
                "display_name": r["display_name"],
                "full_location": r["full_location"],
                "sub_region": r["sub_region"],
                "status": r["status"],
                "is_low_co2": r["is_low_co2"],
                "lat": r.get("Lat") if "Lat" in r else r.get("lat"),
                "lng": r.get("Lng") if "Lng" in r else r.get("lng"),
                "date_launched": r.get("date_launched", ""),
                "zones": r.get("zones", []),
                "zone_count": r.get("zone_count", 3),
                "machine_series": r.get("machine_series", []),
                "cpus": r.get("cpus", []),
                "gpus": r.get("gpus", []),
                "confidential_options": r.get("confidential_options", []),
                "services": r.get("services", []),
                "service_count": r.get("service_count", 0),
                "ai_model_count": r.get("ai_model_count", len(r.get("ai_models", []))),
                "pricing": r.get("pricing", {}),
            }
        )

    compact_models = []
    for m in catalog.get("models", []):
        compact_models.append(
            {
                "model_id": m["model_id"],
                "model_name": m.get("model_name", m.get("name", "")),
                "family": m.get("family", ""),
                "modality": m.get("modality", ""),
                "stage": m.get("stage", "GA"),
                "global_endpoint": bool(m.get("global_endpoint", False)),
                "multi_regions": m.get("multi_regions", []),
                "regions": m.get("regions", []),
                "region_count": len(m.get("regions", [])),
                "url": m.get("url", ""),
            }
        )

    payload = {
        "meta": catalog.get("meta", {}),
        "regions": compact_regions,
        "future_regions": catalog.get("future_regions", []),
        "services": compact_services,
        "models": compact_models,
        "pops": catalog.get("pops", {}),
        "whats_new": catalog.get("whats_new", [])[:120],
        "release_notes": catalog.get("release_notes", [])[:120],
    }
    raw_bytes = repr(payload.get("meta", {}).get("generated_epoch", 0)).encode("utf-8")
    payload["etag"] = hashlib.sha256(raw_bytes + str(len(compact_services)).encode()).hexdigest()[:16]
    return payload
