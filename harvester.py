#!/usr/bin/env python3
"""
GCP Services & Regional Capabilities Harvester (harvester.py)

Queries official Google Cloud Location feeds, Compute Region/Zone & GPU matrices,
and Google APIs Discovery Service ($discovery/rest) to build a comprehensive,
locally cached dataset of:
  1. All GCP Regions (Available & Future), Availability Zones (130+), Machine Series,
     CPU Microarchitectures, Confidential Computing, and GPU Accelerators per zone.
  2. All GCP Services & Products (Regional, Multi-Region, and Global) mapped to regions.
  3. Deep API-level capabilities per service (API identifiers, versions, REST resources,
     regional endpoint patterns, and thousands of REST API methods/operations).
  4. Edge Points of Presence (PoPs), Cloud CDN PoPs, and Media CDN PoPs.
  5. Daily Snapshot Diffs ("What's New").

Designed with:
  - Daily Cache TTL (default 24 hours / 86,400s) so normal queries hit local cache/static HTML.
  - Token-bucket rate limiting to prevent burst quota exhaustion.
  - Exponential backoff with full jitter + Retry-After header support for 429/403/5xx resilience.
  - Per-API disk checkpointing so interrupted harvests resume seamlessly.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import html as html_lib
import json
import os
from pathlib import Path
import random
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "data" / "cache"
RAW_CACHE_DIR = CACHE_DIR / "raw"
DISC_CACHE_DIR = CACHE_DIR / "discovery"
SNAPSHOT_DIR = CACHE_DIR / "snapshots"
CATALOG_FILE = CACHE_DIR / "gcp_catalog.json"

DEFAULT_TTL_SECONDS = 86400  # 24 hours (once-a-day refresh)


def create_ssl_context() -> ssl.SSLContext:
    """Create an SSL context that works reliably across macOS and Linux environments."""
    cafile = "/etc/ssl/cert.pem"
    if os.path.exists(cafile):
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


class TokenBucketRateLimiter:
    """Thread-safe token-bucket rate limiter to avoid API quota bursts."""

    def __init__(self, rate_per_sec: float = 10.0, capacity: float = 10.0) -> None:
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_refill = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                wait_time = (1.0 - self.tokens) / self.rate
            time.sleep(max(0.01, wait_time))


class ResilientFetcher:
    """HTTP fetcher with token-bucket rate limiting, exponential backoff + jitter, and disk caching."""

    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        rate_per_sec: float = 12.0,
        max_retries: int = 5,
        force_refresh: bool = False,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_retries = max_retries
        self.force_refresh = force_refresh
        self.limiter = TokenBucketRateLimiter(rate_per_sec=rate_per_sec, capacity=rate_per_sec)
        self.ssl_ctx = create_ssl_context()
        self.stats = {
            "network_requests": 0,
            "cache_hits": 0,
            "retries": 0,
            "errors": 0,
        }
        self.stats_lock = threading.Lock()

    def _inc_stat(self, key: str, amount: int = 1) -> None:
        with self.stats_lock:
            self.stats[key] = self.stats.get(key, 0) + amount

    def is_cache_fresh(self, path: Path) -> bool:
        if self.force_refresh or not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < self.ttl_seconds

    def fetch_bytes(self, url: str, cache_path: Path | None = None, timeout: int = 20) -> bytes:
        if cache_path and self.is_cache_fresh(cache_path):
            self._inc_stat("cache_hits")
            return cache_path.read_bytes()

        base_delay = 1.0
        last_err: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            self.limiter.acquire()
            self._inc_stat("network_requests")
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "GCP-Services-Region-Explorer/1.0 (Local Static Caching Harvester)",
                    "Accept": "application/json, text/html, */*",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx) as resp:
                    content = resp.read()
                    if cache_path:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
                        tmp_path.write_bytes(content)
                        tmp_path.replace(cache_path)
                    return content
            except urllib.error.HTTPError as err:
                last_err = err
                # Handle quota / rate-limit (429, 403) and transient server errors (500, 502, 503, 504)
                if err.code in (429, 403, 500, 502, 503, 504) and attempt < self.max_retries:
                    self._inc_stat("retries")
                    retry_after = err.headers.get("Retry-After") if err.headers else None
                    if retry_after and retry_after.isdigit():
                        sleep_s = float(retry_after)
                    else:
                        # Exponential backoff with full jitter
                        max_sleep = min(30.0, base_delay * (2 ** (attempt - 1)))
                        sleep_s = random.uniform(0.5 * max_sleep, max_sleep)
                    time.sleep(sleep_s)
                    continue
                break
            except Exception as err:
                last_err = err
                if attempt < self.max_retries:
                    self._inc_stat("retries")
                    max_sleep = min(20.0, base_delay * (2 ** (attempt - 1)))
                    time.sleep(random.uniform(0.4 * max_sleep, max_sleep))
                    continue
                break

        # Fallback to stale cache if available on network error
        if cache_path and cache_path.exists():
            self._inc_stat("cache_hits")
            return cache_path.read_bytes()

        self._inc_stat("errors")
        raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts: {last_err}")

    def fetch_json(self, url: str, cache_path: Path | None = None, timeout: int = 20) -> Any:
        raw = self.fetch_bytes(url, cache_path=cache_path, timeout=timeout)
        return json.loads(raw.decode("utf-8"))

    def fetch_text(self, url: str, cache_path: Path | None = None, timeout: int = 20) -> str:
        raw = self.fetch_bytes(url, cache_path=cache_path, timeout=timeout)
        return raw.decode("utf-8", errors="ignore")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "item"


def clean_html_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = s.replace("\u200a", "").replace("\u2009", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


# Explicit mapping between GCP Product Names and Google Discovery API Service Names
PRODUCT_TO_API_MAP: dict[str, list[str]] = {
    "API Gateway": ["apigateway"],
    "Access Context Manager": ["accesscontextmanager"],
    "Access Transparency": ["accessapproval"],
    "AlloyDB": ["alloydb"],
    "Anthos": ["gkehub", "anthos", "gkemulticloud"],
    "Apigee": ["apigee", "apihub", "apim"],
    "App Engine": ["appengine"],
    "Application Design Center": ["designcenter"],
    "Application Integration": ["integrations"],
    "Artifact Registry": ["artifactregistry"],
    "Assured Workloads": ["assuredworkloads"],
    "AutoML Natural Language": ["language", "aiplatform"],
    "AutoML Translation": ["translate", "aiplatform"],
    "AutoML Video": ["videointelligence", "aiplatform"],
    "AutoML Vision": ["vision", "aiplatform"],
    "BI Engine": ["bigquery", "bigqueryreservation"],
    "BQML": ["bigquery"],
    "Backup and DR": ["backupdr"],
    "Bare Metal Solution": ["baremetalsolution"],
    "Batch": ["batch"],
    "BeyondCorp Enterprise": ["beyondcorp"],
    "BigQuery": ["bigquery", "bigquerydatatransfer", "bigqueryreservation", "bigqueryconnection", "biglake"],
    "BigQuery Data Transfer Service": ["bigquerydatatransfer"],
    "BigQuery Omni": ["bigquery", "bigqueryconnection"],
    "Bigtable": ["bigtableadmin"],
    "Binary Authorization": ["binaryauthorization"],
    "Certificate Authority Service": ["privateca"],
    "Certificate Manager": ["certificatemanager"],
    "Chronicle": ["chronicle"],
    "Cloud Armor": ["compute", "networksecurity"],
    "Cloud Asset Inventory": ["cloudasset"],
    "Cloud Billing API": ["cloudbilling", "billingbudgets"],
    "Cloud Build": ["cloudbuild"],
    "Cloud CDN": ["compute", "networkservices"],
    "Cloud Composer": ["composer"],
    "Cloud Code": ["cloudaicompanion"],
    "Cloud Data Fusion": ["datafusion"],
    "Cloud Data Loss Prevention": ["dlp"],
    "Cloud Deploy": ["clouddeploy"],
    "Cloud Deployment Manager": ["deploymentmanager"],
    "Cloud DNS": ["dns"],
    "Cloud Domains": ["domains"],
    "Cloud EKM": ["cloudkms"],
    "Cloud Endpoints": ["servicemanagement", "servicecontrol"],
    "Cloud External Key Manager": ["cloudkms"],
    "Cloud Filestore": ["file"],
    "Cloud Firestore": ["firestore"],
    "Cloud Healthcare API": ["healthcare"],
    "Cloud HSM": ["cloudkms"],
    "Cloud IDS": ["ids"],
    "Cloud Identity": ["cloudidentity"],
    "Cloud Interconnect": ["compute", "networkconnectivity"],
    "Cloud Key Management Service": ["cloudkms", "kmsinventory"],
    "Cloud Life Sciences": ["lifesciences", "batch"],
    "Cloud Load Balancing": ["compute", "networkservices"],
    "Cloud Logging": ["logging"],
    "Cloud Monitoring": ["monitoring"],
    "Cloud NAT": ["compute"],
    "Cloud NGFW": ["compute", "networksecurity"],
    "Cloud Natural Language API": ["language"],
    "Cloud Profiler": ["cloudprofiler"],
    "Cloud Router": ["compute"],
    "Cloud Run": ["run"],
    "Cloud Run functions": ["cloudfunctions", "run"],
    "Cloud Scheduler": ["cloudscheduler"],
    "Cloud Shell": ["cloudshell"],
    "Cloud Source Repositories": ["sourcerepo"],
    "Cloud SQL": ["sqladmin"],
    "Cloud Storage": ["storage", "storagetransfer"],
    "Cloud Storage for Firebase": ["firebasestorage", "storage"],
    "Cloud Tasks": ["cloudtasks"],
    "Cloud TPU": ["tpu"],
    "Cloud Trace": ["cloudtrace"],
    "Cloud Translation": ["translate"],
    "Cloud Vision": ["vision"],
    "Cloud VPN": ["compute"],
    "Cloud Workstations": ["workstations"],
    "Compute Engine": ["compute"],
    "Confidential VM": ["compute", "confidentialcomputing"],
    "Config Connector": ["config"],
    "Connectors": ["connectors"],
    "Contact Center AI": ["contactcenterinsights", "dialogflow"],
    "Container Registry": ["containeranalysis", "artifactregistry"],
    "Data Catalog": ["datacatalog", "dataplex"],
    "Database Center": ["databasecenter"],
    "Database Migration Service": ["datamigration"],
    "Dataflow": ["dataflow"],
    "Dataform": ["dataform"],
    "Dataplex": ["dataplex"],
    "Dataproc": ["dataproc", "dataprocrm"],
    "Dataproc Metastore": ["metastore"],
    "Datastore": ["datastore"],
    "Datastream": ["datastream"],
    "Dialogflow CX": ["dialogflow"],
    "Dialogflow ES": ["dialogflow"],
    "Document AI": ["documentai"],
    "Document AI Processors": ["documentai"],
    "Document AI Warehouse": ["contentwarehouse"],
    "Error Reporting": ["clouderrorreporting"],
    "Eventarc": ["eventarc", "eventarcpublishing"],
    "Extreme PD": ["compute"],
    "Firebase App Hosting": ["firebaseapphosting"],
    "Firebase Authentication": ["identitytoolkit"],
    "Firebase Data Connect": ["firebasedataconnect"],
    "Firebase Hosting": ["firebasehosting"],
    "Firebase Realtime Database": ["firebasedatabase"],
    "Firebase Test Lab": ["testing", "toolresults"],
    "Filestore": ["file"],
    "Fleet Engine": ["mapsbooking"],
    "GKE Autopilot": ["container"],
    "GKE Enterprise": ["gkehub", "container"],
    "Gemini API in Google AI Studio": ["generativelanguage"],
    "Gemini Business": ["cloudaicompanion", "discoveryengine"],
    "Gemini Cloud Assist": ["cloudaicompanion", "geminicloudassist"],
    "Gemini Code Assist": ["cloudaicompanion"],
    "Gemini Enterprise Agent Platform (Vertex AI)": ["aiplatform", "discoveryengine"],
    "Gemini Enterprise Plus": ["discoveryengine", "cloudaicompanion"],
    "Gemini Enterprise Standard": ["discoveryengine", "cloudaicompanion"],
    "Gemini Enterprise for Customer Experience (GECX)": ["dialogflow", "contactcenterinsights"],
    "Google Cloud Armor": ["compute", "networksecurity"],
    "Google Cloud Marketplace": ["cloudcommerceprocurement"],
    "Google Cloud NetApp Volumes": ["netapp"],
    "Google Cloud VMware Engine": ["vmwareengine"],
    "Google Distributed Cloud Edge": ["edgecontainer", "edgenetwork"],
    "Google Kubernetes Engine": ["container", "gkebackup", "gkehub"],
    "Google SecOps": ["chronicle", "securitycenter"],
    "Hyperdisk": ["compute"],
    "Identity and Access Management": ["iam", "iamcredentials", "policytroubleshooter"],
    "Identity Platform": ["identitytoolkit"],
    "Identity-Aware Proxy": ["iap"],
    "Infrastructure Manager": ["config"],
    "Integration Connectors": ["connectors"],
    "Key Access Justifications": ["cloudkms"],
    "Key Management Service": ["cloudkms"],
    "Local SSD": ["compute"],
    "Looker": ["looker"],
    "Looker Studio": ["datastudio"],
    "Managed Lustre": ["lustre", "parallelstore"],
    "Managed Microsoft AD": ["managedidentities"],
    "Managed Service for Apache Airflow": ["composer"],
    "Managed Service for Apache Kafka": ["managedkafka"],
    "Managed Service for Apache Spark": ["dataproc"],
    "Managed Service for Prometheus": ["monitoring"],
    "Media CDN": ["networkservices"],
    "Media Translation": ["translate"],
    "Memorystore for Memcached": ["memcache"],
    "Memorystore for Redis": ["redis"],
    "Memorystore for Redis Cluster": ["redis"],
    "Memorystore for Valkey": ["memorystore", "redis"],
    "Migrate to Containers": ["vmmigration"],
    "Migrate to Virtual Machines": ["vmmigration"],
    "Network Connectivity Center": ["networkconnectivity"],
    "Network Intelligence Center": ["networkmanagement"],
    "Network Security Integration": ["networksecurity"],
    "Network Service Tiers": ["compute"],
    "Oracle Database@Google Cloud": ["oracledatabase"],
    "Organization Policy": ["orgpolicy"],
    "Parallelstore": ["parallelstore"],
    "Persistent Disk": ["compute"],
    "Policy Intelligence": ["policyanalyzer", "policytroubleshooter"],
    "Private Service Connect": ["compute", "servicedirectory", "networkconnectivity"],
    "Pub/Sub": ["pubsub", "pubsublite"],
    "Pub/Sub Lite": ["pubsublite"],
    "Recommendations AI": ["recommendationengine", "retail"],
    "Resource Manager": ["cloudresourcemanager"],
    "Retail Search": ["retail"],
    "Secret Manager": ["secretmanager"],
    "Secure Source Manager": ["securesourcemanager"],
    "Security Command Center": ["securitycenter", "securityposture"],
    "Sensitive Data Protection": ["dlp"],
    "Service Directory": ["servicedirectory"],
    "Service Extensions": ["networkservices"],
    "Service Mesh": ["networkservices", "meshca"],
    "Service Usage": ["serviceusage"],
    "Spanner": ["spanner"],
    "Spectrum Access System": ["sasportal"],
    "Speech-to-Text": ["speech"],
    "Storage Transfer Service": ["storagetransfer"],
    "Text-to-Speech": ["texttospeech"],
    "Traffic Director": ["networkservices", "compute"],
    "Transcoder API": ["transcoder"],
    "Transfer Appliance": ["transferappliance"],
    "Unified Maintenance": ["maintenance"],
    "Vertex AI": ["aiplatform", "notebooks"],
    "Vertex AI Agent Builder": ["discoveryengine", "aiplatform"],
    "Vertex AI Feature Store": ["aiplatform"],
    "Vertex AI Matching Engine": ["aiplatform"],
    "Vertex AI Model Registry": ["aiplatform"],
    "Vertex AI Pipelines": ["aiplatform"],
    "Vertex AI Platform": ["aiplatform"],
    "Vertex AI Search": ["discoveryengine"],
    "Vertex AI TensorBoard": ["aiplatform"],
    "Vertex AI Workbench": ["notebooks", "aiplatform"],
    "Vertex Explainable AI": ["aiplatform"],
    "Video Intelligence API": ["videointelligence"],
    "Video Stitcher API": ["videostitcher"],
    "Virtual Private Cloud": ["compute", "vpcaccess", "networkconnectivity"],
    "VM Manager": ["osconfig"],
    "VMware Engine": ["vmwareengine"],
    "Web Risk": ["webrisk"],
    "Web Security Scanner": ["websecurityscanner"],
    "Workflows": ["workflows", "workflowexecutions"],
    "Workload Manager": ["workloadmanager"],
    "reCAPTCHA Enterprise": ["recaptchaenterprise"],
}


def parse_zones_html(raw_html: str) -> dict[str, list[dict[str, Any]]]:
    """Parse all 130+ GCP availability zones and hardware capabilities from compute/docs/regions-zones."""
    by_region: dict[str, list[dict[str, Any]]] = {}
    pattern = re.compile(
        r"<tr>\s*<td><code[^>]*>([a-z]+-[a-z]+[0-9]+-[a-z])</code></td>(.*?)</tr>",
        re.S,
    )
    for zid, rest in pattern.findall(raw_html):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", rest, re.S)
        if len(tds) >= 4:
            region_id = "-".join(zid.split("-")[:2])
            machine_types = [x.strip() for x in clean_html_text(tds[1]).split(",") if x.strip()]
            cpus = [x.strip() for x in clean_html_text(tds[2]).split(",") if x.strip()]
            options = [x.strip() for x in clean_html_text(tds[3]).split(",") if x.strip()]
            by_region.setdefault(region_id, []).append(
                {
                    "zone": zid,
                    "region": region_id,
                    "location": clean_html_text(tds[0]),
                    "machine_types": machine_types,
                    "cpus": cpus,
                    "options": options,
                }
            )
    return by_region


def parse_gpu_zones_html(raw_html: str) -> dict[str, dict[str, Any]]:
    """Parse GPU accelerator availability per zone from compute/docs/gpus/gpu-regions-zones."""
    gpu_by_zone: dict[str, dict[str, Any]] = {}
    pattern = re.compile(
        r"<tr>\s*<td><code[^>]*>([a-z]+-[a-z]+[0-9]+-[a-z0-9]+)</code></td>(.*?)</tr>",
        re.S,
    )
    for zid, rest in pattern.findall(raw_html):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", rest, re.S)
        if len(tds) >= 3:
            gpus = [x.strip() for x in clean_html_text(tds[2]).split("•") if x.strip()]
            gpu_by_zone[zid] = {
                "zone_type": clean_html_text(tds[1]),
                "gpus": gpus,
            }
    return gpu_by_zone


def parse_vertex_ai_models_html(raw_html: str) -> list[dict[str, Any]]:
    """Parse Vertex AI Generative & Partner Models regional availability from vertex-ai/generative-ai/docs/learn/locations."""
    tables = re.findall(r"<table.*?</table>", raw_html, re.S | re.I)
    models: dict[str, dict[str, Any]] = {}

    for t in tables:
        trs = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S | re.I)
        if not trs:
            continue
        ths = [
            html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip())
            for h in re.findall(r"<th[^>]*>(.*?)</th>", trs[0], re.S | re.I)
        ]
        if len(ths) < 2 or "(" not in ths[1]:
            continue
        col_locs: list[str] = []
        for h in ths[1:]:
            m = re.search(r"\(([^)]+)\)", h)
            col_locs.append(m.group(1).strip() if m else h)

        current_family = "Gemini models"
        for r in trs[1:]:
            if "vertex-ai-table-heading" in r or "colspan=" in r:
                heading = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r)).strip())
                if heading:
                    current_family = heading
                continue
            tds = re.findall(r"(<td[^>]*>)(.*?)(</td>)", r, re.S | re.I)
            if len(tds) < 2:
                continue
            first_open, first_inner, _ = tds[0]
            is_preview = "preview" in first_inner.lower()
            href_m = re.search(r'href="([^"]+)"', first_inner)
            doc_url = href_m.group(1) if href_m else "https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations"
            if doc_url.startswith("/"):
                doc_url = f"https://cloud.google.com{doc_url}"

            code_m = re.search(r"<code[^>]*>\(?([^)<]+)\)?</code>", first_inner, re.I)
            clean_name = re.sub(r"<span[^>]*vertex-ai-not-ga[^>]*>.*?</span>", "", first_inner, flags=re.S | re.I)
            clean_name = re.sub(r"<code[^>]*>.*?</code>", "", clean_name, flags=re.S | re.I)
            clean_name = html_lib.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", clean_name)).strip())
            clean_name = clean_name.replace("\xa0", " ").strip()
            if not clean_name:
                continue

            if code_m:
                raw_code = html_lib.unescape(code_m.group(1).strip())
                raw_code = re.sub(r"[\[\]\'\"`]", "", raw_code).strip()
                model_id = raw_code
            else:
                mg_m = re.search(r"/model-garden/([a-z0-9._-]+)", doc_url, re.I)
                if mg_m and mg_m.group(1) not in ("claude", "mistral", "llama"):
                    model_id = mg_m.group(1)
                else:
                    slug_base = re.sub(r"\s+on\s+google\s+cloud.*$", "", clean_name, flags=re.I)
                    slug_base = re.sub(r"^anthropic['’]?s\s+", "", slug_base, flags=re.I)
                    slug_base = re.sub(r"\(deprecated\)", "", slug_base, flags=re.I).strip()
                    if "claude" in slug_base.lower():
                        model_id = re.sub(r"[^a-z0-9]+", "-", slug_base.lower()).strip("-")
                    else:
                        model_id = re.sub(r"[^a-z0-9.]+", "-", slug_base.lower()).strip("-")

            low_name = f"{clean_name} {current_family}".lower()
            if "veo" in low_name or "video" in low_name:
                modality = "Video Generation"
            elif "image" in low_name or "banana" in low_name or "try-on" in low_name or "imagen" in low_name:
                modality = "Image Generation"
            elif any(w in low_name for w in ("speech", "tts", "chirp", "transcribe", "audio", "voice")):
                modality = "Audio, Speech & TTS"
            elif "embedding" in low_name or "e5" in low_name:
                modality = "Embeddings"
            elif "codestral" in low_name or "coder" in low_name:
                modality = "Code & Reasoning"
            elif "live" in low_name:
                modality = "Live Real-Time Streaming"
            else:
                modality = "Text & Multimodal"

            stage = "Deprecated" if "deprecated" in clean_name.lower() else ("Preview" if is_preview else "GA")
            family_clean = current_family.replace(
                "Veo on Gemini Enterprise Agent Platform models",
                "Veo Video models",
            )

            entry = models.setdefault(
                clean_name,
                {
                    "name": clean_name,
                    "model_id": model_id,
                    "family": family_clean,
                    "modality": modality,
                    "stage": stage,
                    "url": doc_url,
                    "global_endpoint": False,
                    "multi_regions": set(),
                    "regions": set(),
                },
            )
            for idx, (td_open, td_inner, _) in enumerate(tds[1:]):
                if idx >= len(col_locs):
                    break
                loc = col_locs[idx]
                supported = ("supported" in td_open.lower()) or ("check" in td_inner.lower())
                if supported:
                    if loc == "global":
                        entry["global_endpoint"] = True
                    elif loc in ("us", "eu", "asia"):
                        entry["multi_regions"].add(loc.upper())
                    else:
                        entry["regions"].add(loc)

    out: list[dict[str, Any]] = []
    for _, v in models.items():
        regs = sorted(v["regions"])
        mrs = sorted(v["multi_regions"])
        scope_parts = []
        if v["global_endpoint"]:
            scope_parts.append("Global")
        if mrs:
            scope_parts.append(f"Multi-Region ({'/'.join(mrs)})")
        if regs:
            scope_parts.append(f"Regional ({len(regs)})")
        out.append(
            {
                "name": v["name"],
                "model_name": v["name"],
                "model_id": v["model_id"],
                "family": v["family"],
                "modality": v["modality"],
                "stage": v["stage"],
                "url": v["url"],
                "docs_url": v["url"],
                "global_endpoint": v["global_endpoint"],
                "multi_regions": mrs,
                "regions": regs,
                "region_count": len(regs),
                "endpoint_scope": " + ".join(scope_parts) if scope_parts else "Regional",
            }
        )
    return out


def extract_discovery_methods(doc: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Recursively extract all REST API methods and top-level resources from a Google Discovery document."""
    methods: list[dict[str, Any]] = []
    top_resources = sorted(list(doc.get("resources", {}).keys()))

    def _walk(node: dict[str, Any], prefix: str = "") -> None:
        for mname, mval in node.get("methods", {}).items():
            mid = mval.get("id", f"{prefix}.{mname}" if prefix else mname)
            flat_path = mval.get("flatPath") or mval.get("path", "")
            http_method = mval.get("httpMethod", "GET")
            desc = (mval.get("description") or "").strip()
            if len(desc) > 220:
                desc = desc[:217] + "..."
            scopes = [
                s.split("/")[-1]
                for s in mval.get("scopes", [])
            ]
            is_regional = any(
                tok in flat_path.lower()
                for tok in ["{locationsid}", "{location}", "{region}", "{regionsid}", "{zone}", "{zonesid}"]
            )
            methods.append(
                {
                    "id": mid,
                    "httpMethod": http_method,
                    "path": flat_path,
                    "description": desc,
                    "scopes": scopes,
                    "isRegional": is_regional,
                }
            )
        for rname, rval in node.get("resources", {}).items():
            _walk(rval, f"{prefix}.{rname}" if prefix else rname)

    _walk(doc)
    methods.sort(key=lambda m: m["id"])
    return methods, top_resources


def filter_gcp_discovery_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter Google Discovery directory items to GCP-relevant APIs and group versions."""
    gcp_keywords = {
        "cloud", "compute", "kubernetes", "container", "bigquery", "spanner", "vertex",
        "aiplatform", "dataproc", "dataflow", "alloydb", "pubsub", "firestore", "bigtable",
        "storage", "looker", "apigee", "run", "functions", "secret", "kms", "iam", "logging",
        "monitoring", "trace", "profiler", "network", "dns", "sql", "redis", "memcache",
        "filestore", "batch", "workflows", "eventarc", "scheduler", "tasks", "artifact",
        "build", "deploy", "chronicle", "dlp", "securitycenter", "healthcare", "documentai",
        "dialogflow", "translate", "vision", "speech", "texttospeech", "videointelligence",
        "datamigration", "datastream", "dataplex", "datacatalog", "dataform", "datafusion",
        "composer", "notebooks", "tpu", "vmmigration", "backupdr", "assuredworkloads",
        "beyondcorp", "certificatemanager", "vpcaccess", "ids", "orgpolicy", "serviceusage",
        "servicemanagement", "servicecontrol", "servicedirectory", "privateca", "binaryauthorization",
        "vmwareengine", "baremetalsolution", "edgecontainer", "edgenetwork", "workstations",
        "parallelstore", "lustre", "netapp", "oracledatabase", "managedkafka", "memorystore",
        "gkehub", "gkebackup", "gkemulticloud", "config", "connectors", "integrations",
        "discoveryengine", "generativelanguage", "cloudaicompanion", "recaptchaenterprise",
        "webrisk", "websecurityscanner", "osconfig", "workloadmanager", "transcoder",
        "videostitcher", "lifesciences", "retail", "domains", "iap", "cloudidentity",
        "cloudasset", "cloudresourcemanager", "cloudbilling", "billingbudgets", "cloudlocationfinder",
        "firebase", "datastore", "metastore", "securesourcemanager", "databasecenter",
    }
    referenced_apis = {api for apis in PRODUCT_TO_API_MAP.values() for api in apis}

    # Track all versions per API name, and pick preferred (or latest) item for REST doc fetch
    by_name: dict[str, dict[str, Any]] = {}
    for item in items:
        name = item.get("name", "")
        version = item.get("version", "")
        title = item.get("title", "")
        doc_link = item.get("documentationLink", "")
        is_gcp = (
            name in referenced_apis
            or "cloud.google.com" in doc_link
            or "firebase.google.com" in doc_link
            or "ai.google.dev" in doc_link
            or any(k in name.lower() or k in title.lower() for k in gcp_keywords)
        )
        if not is_gcp:
            continue

        entry = by_name.setdefault(
            name,
            {
                "name": name,
                "versions": [],
                "preferred_item": None,
            },
        )
        entry["versions"].append(version)
        if item.get("preferred", False) or entry["preferred_item"] is None:
            entry["preferred_item"] = item

    result = []
    for name, info in sorted(by_name.items()):
        pitem = dict(info["preferred_item"])
        pitem["all_versions"] = sorted(set(info["versions"]))
        result.append(pitem)
    return result


def harvest_all(
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    force_refresh: bool = False,
    max_workers: int = 8,
    rate_per_sec: float = 15.0,
) -> dict[str, Any]:
    """Execute the full GCP Services & Regions harvest (or load from valid daily cache)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DISC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    if not force_refresh and CATALOG_FILE.exists():
        age_sec = time.time() - CATALOG_FILE.stat().st_mtime
        if age_sec < ttl_seconds:
            print(f"[Cache Hit] Loading cached GCP catalog ({int(age_sec)}s old, TTL={ttl_seconds}s): {CATALOG_FILE}")
            catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
            catalog.setdefault("meta", {})["served_from_cache"] = True
            catalog["meta"]["cache_age_seconds"] = int(age_sec)
            return catalog

    start_ts = time.time()
    fetcher = ResilientFetcher(
        ttl_seconds=ttl_seconds,
        rate_per_sec=rate_per_sec,
        max_retries=5,
        force_refresh=force_refresh,
    )

    print("[Harvester] Step 1/5: Fetching official GCP Location, Multi-Region, Global & PoP feeds...")
    locations_map = fetcher.fetch_json(
        "https://cloud.google.com/about/locations/locations_map.json",
        cache_path=RAW_CACHE_DIR / "locations_map.json",
    )
    data_json = fetcher.fetch_json(
        "https://cloud.google.com/about/locations/data.json",
        cache_path=RAW_CACHE_DIR / "data.json",
    )
    multi_region_json = fetcher.fetch_json(
        "https://cloud.google.com/about/locations/multi-region-data.json",
        cache_path=RAW_CACHE_DIR / "multi-region-data.json",
    )
    global_json = fetcher.fetch_json(
        "https://cloud.google.com/about/locations/global-data.json",
        cache_path=RAW_CACHE_DIR / "global-data.json",
    )
    edge_pops = fetcher.fetch_json(
        "https://cloud.google.com/about/locations/edge_pop_markers.json",
        cache_path=RAW_CACHE_DIR / "edge_pop_markers.json",
    )
    cdn_pops = fetcher.fetch_json(
        "https://cloud.google.com/about/locations/cloud_cdn_markers.json",
        cache_path=RAW_CACHE_DIR / "cloud_cdn_markers.json",
    )
    media_cdn_pops = fetcher.fetch_json(
        "https://cloud.google.com/about/locations/media_cdn_markers.json",
        cache_path=RAW_CACHE_DIR / "media_cdn_markers.json",
    )

    print("[Harvester] Step 2/5: Fetching Google Cloud Availability Zones, Machine Series, CPUs, GPUs & AI Models...")
    regions_zones_html = fetcher.fetch_text(
        "https://cloud.google.com/compute/docs/regions-zones",
        cache_path=RAW_CACHE_DIR / "regions_zones.html",
    )
    gpu_zones_html = fetcher.fetch_text(
        "https://cloud.google.com/compute/docs/gpus/gpu-regions-zones",
        cache_path=RAW_CACHE_DIR / "gpu_regions_zones.html",
    )
    vertex_ai_models_html = fetcher.fetch_text(
        "https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations",
        cache_path=RAW_CACHE_DIR / "vertex_ai_models_locations.html",
    )
    zones_by_region = parse_zones_html(regions_zones_html)
    gpu_by_zone = parse_gpu_zones_html(gpu_zones_html)
    ai_models_list = parse_vertex_ai_models_html(vertex_ai_models_html)

    # Enrich zones with GPU accelerator models
    for r_zones in zones_by_region.values():
        for z in r_zones:
            ginfo = gpu_by_zone.get(z["zone"], {})
            z["gpus"] = ginfo.get("gpus", [])
            z["zone_type"] = ginfo.get("zone_type", "Standard")

    print("[Harvester] Step 3/5: Fetching Google APIs Discovery directory & harvesting GCP REST specs...")
    discovery_index = fetcher.fetch_json(
        "https://discovery.googleapis.com/discovery/v1/apis",
        cache_path=RAW_CACHE_DIR / "discovery_apis.json",
    )
    gcp_api_items = filter_gcp_discovery_items(discovery_index.get("items", []))
    print(f"[Harvester] Identified {len(gcp_api_items)} GCP APIs in Discovery directory. Harvesting REST specifications...")

    api_specs: dict[str, dict[str, Any]] = {}

    def _fetch_single_api_spec(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        api_name = item["name"]
        version = item["version"]
        rest_url = item.get("discoveryRestUrl") or f"https://{api_name}.googleapis.com/$discovery/rest?version={version}"
        cache_file = DISC_CACHE_DIR / f"{api_name}_{version}.json"
        base_spec = {
            "name": api_name,
            "service_endpoint": f"{api_name}.googleapis.com",
            "preferred_version": version,
            "all_versions": item.get("all_versions", [version]),
            "title": item.get("title", api_name),
            "description": item.get("description", ""),
            "documentation_link": item.get("documentationLink", ""),
            "discovery_rest_url": rest_url,
            "root_url": f"https://{api_name}.googleapis.com/",
            "resources": [],
            "methods": [],
            "method_count": 0,
            "regional_method_count": 0,
        }
        try:
            doc = fetcher.fetch_json(rest_url, cache_path=cache_file, timeout=15)
            methods, top_resources = extract_discovery_methods(doc)
            base_spec["root_url"] = doc.get("rootUrl", base_spec["root_url"])
            base_spec["title"] = doc.get("title", base_spec["title"])
            base_spec["description"] = doc.get("description", base_spec["description"])
            base_spec["documentation_link"] = doc.get("documentationLink", base_spec["documentation_link"])
            base_spec["resources"] = top_resources
            base_spec["methods"] = methods
            base_spec["method_count"] = len(methods)
            base_spec["regional_method_count"] = sum(1 for m in methods if m.get("isRegional"))
        except Exception:
            # Keep directory metadata even if an alpha/restricted discovery doc returns 404/403
            pass
        return api_name, base_spec

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_single_api_spec, item): item["name"] for item in gcp_api_items}
        done_count = 0
        for fut in as_completed(futures):
            done_count += 1
            api_name, spec_data = fut.result()
            api_specs[api_name] = spec_data
            if done_count % 40 == 0 or done_count == len(gcp_api_items):
                print(f"  -> Harvested {done_count}/{len(gcp_api_items)} GCP Discovery REST specs...")

    print("[Harvester] Step 4/5: Normalizing & cross-linking Regions, Services, Multi-Region, and API Capabilities...")

    # Build regions dictionary
    regions_dict: dict[str, dict[str, Any]] = {}
    future_regions_list: list[dict[str, Any]] = []

    for r in locations_map:
        status = r.get("regionStatus", "available")
        rid = (r.get("regionId") or "").strip()
        rname = (r.get("regionName") or "").strip()
        sub_region = (r.get("subRegionName") or "").strip()
        if sub_region == "APAC":
            sub_region = "Asia Pacific"
        info = r.get("infoWindowDetails") or {}
        date_launched = str(info.get("dateLaunched", ""))

        if status != "available" or not rid:
            future_regions_list.append(
                {
                    "region_name": rname,
                    "region_id": rid or f"future-{slugify(rname)}",
                    "sub_region": sub_region,
                    "status": "future",
                    "lat": r.get("lat"),
                    "lng": r.get("lng"),
                    "date_launched": date_launched or "Future Region",
                }
            )
            continue

        rzones = zones_by_region.get(rid, [])
        # Aggregate unique machine series, CPUs, GPUs, and confidential options across zones in this region
        all_mtypes = sorted({m for z in rzones for m in z.get("machine_types", [])})
        all_cpus = sorted({c for z in rzones for c in z.get("cpus", [])})
        all_gpus = sorted({g for z in rzones for g in z.get("gpus", [])})
        all_opts = sorted({o for z in rzones for o in z.get("options", [])})
        city_country = rzones[0]["location"] if rzones else f"{rname}, {sub_region}"

        regions_dict[rid] = {
            "region_id": rid,
            "region_name": rname,
            "display_name": f"{rname} ({rid})",
            "full_location": city_country,
            "sub_region": sub_region,
            "status": "available",
            "is_low_co2": bool(r.get("isLowCO2", False)),
            "lat": r.get("lat"),
            "lng": r.get("lng"),
            "date_launched": date_launched,
            "zones": [z["zone"] for z in rzones] or [f"{rid}-a", f"{rid}-b", f"{rid}-c"],
            "zone_count": len(rzones) if rzones else 3,
            "zone_details": rzones,
            "machine_series": all_mtypes,
            "cpus": all_cpus,
            "gpus": all_gpus,
            "confidential_options": all_opts,
            "services": set(r.get("products", [])),
        }

    # Build services dictionary from data.json + locations_map + multi-region + global
    services_dict: dict[str, dict[str, Any]] = {}

    for row in data_json:
        pname = row["product_name"].strip()
        pgroup = row.get("product_group", "Other").strip()
        url = row.get("url", "").strip()
        if url.startswith("/"):
            url = f"https://cloud.google.com{url}"

        svc = services_dict.setdefault(
            pname,
            {
                "name": pname,
                "slug": slugify(pname),
                "category": pgroup,
                "url": url or "https://cloud.google.com/products",
                "scope": "Regional",
                "regions": set(),
                "multi_regions": [],
                "is_global": False,
            },
        )
        if pgroup and svc["category"] == "Other":
            svc["category"] = pgroup
        if url and svc["url"] == "https://cloud.google.com/products":
            svc["url"] = url

        for loc_str in row.get("low_co2_locations", []) or []:
            m_co2 = re.search(r"\(([a-z0-9-]+)\)", loc_str)
            if m_co2 and m_co2.group(1) in regions_dict:
                regions_dict[m_co2.group(1)]["is_low_co2"] = True

        for loc_str, is_avail in row.get("locations", {}).items():
            if not is_avail:
                continue
            m = re.search(r"\(([a-z0-9-]+)\)", loc_str)
            if m:
                rid = m.group(1)
                svc["regions"].add(rid)
                if rid in regions_dict:
                    regions_dict[rid]["services"].add(pname)

    # Ensure any product listed in locations_map.json is also in services_dict
    for rid, rinfo in regions_dict.items():
        for pname in list(rinfo["services"]):
            svc = services_dict.setdefault(
                pname,
                {
                    "name": pname,
                    "slug": slugify(pname),
                    "category": "AI/ML" if "Gemini" in pname or "AI" in pname else "Compute & Cloud",
                    "url": "https://cloud.google.com/about/locations",
                    "scope": "Regional",
                    "regions": set(),
                    "multi_regions": [],
                    "is_global": False,
                },
            )
            svc["regions"].add(rid)

    # Enrich with multi-region products
    for mr in multi_region_json:
        pname = mr["product_name"].strip()
        plink = mr.get("product_link", "").strip()
        if plink.startswith("/"):
            plink = f"https://cloud.google.com{plink}"
        svc = services_dict.setdefault(
            pname,
            {
                "name": pname,
                "slug": slugify(pname),
                "category": "Storage & Databases",
                "url": plink or "https://cloud.google.com/about/locations",
                "scope": "Multi-Region",
                "regions": set(),
                "multi_regions": [],
                "is_global": False,
            },
        )
        mr_list = []
        for geo, entries in (mr.get("regions") or {}).items():
            for e in entries:
                mr_list.append({"geography": geo, "code": e.get("textKey", "").upper()})
        svc["multi_regions"] = mr_list
        if svc["regions"]:
            svc["scope"] = "Regional + Multi-Region"
        else:
            svc["scope"] = "Multi-Region"

    # Enrich with global products
    cat_name_map = {c["id"]: c["name"] for c in global_json.get("categories", [])}
    for cat_id, items in (global_json.get("products") or {}).items():
        cat_label = cat_name_map.get(cat_id, "Global Services")
        for gitem in items:
            pname = gitem["name"].strip()
            href = gitem.get("href", "").strip()
            if href.startswith("/"):
                href = f"https://cloud.google.com{href}"
            svc = services_dict.setdefault(
                pname,
                {
                    "name": pname,
                    "slug": slugify(pname),
                    "category": cat_label,
                    "url": href or "https://cloud.google.com/about/locations/#global-products",
                    "scope": "Global",
                    "regions": set(),
                    "multi_regions": [],
                    "is_global": True,
                },
            )
            svc["is_global"] = True
            if svc["regions"]:
                svc["scope"] = "Regional + Global"

    # Map each service to its Discovery APIs & capabilities (supports brand-new GCP services automatically)
    used_apis: set[str] = set()
    stop_words = {"google", "cloud", "api", "apis", "service", "services", "for", "the", "and", "in", "to", "enterprise", "managed", "platform"}

    def _extract_doc_slug(url_str: str) -> str:
        m = re.search(r"cloud\.google\.com/([a-z0-9-]+)", (url_str or "").lower())
        if m and m.group(1) not in {"about", "products", "docs", "solutions", "security", "compute"}:
            return m.group(1)
        return ""

    for pname, svc in services_dict.items():
        mapped_api_names = list(PRODUCT_TO_API_MAP.get(pname, []))
        if not mapped_api_names:
            # 1. Match by cloud.google.com/<product-slug> in documentationLink
            svc_doc_slug = _extract_doc_slug(svc.get("url", ""))
            # 2. Match by normalized name and title tokens
            norm = re.sub(r"[^a-z0-9]", "", pname.lower().replace("google", "").replace("cloud", "").replace("api", ""))
            pname_tokens = {t for t in re.findall(r"[a-z0-9]+", pname.lower()) if t not in stop_words and len(t) > 2}

            for api_name, spec in api_specs.items():
                api_doc_slug = _extract_doc_slug(spec.get("documentation_link", ""))
                title_tokens = {t for t in re.findall(r"[a-z0-9]+", spec.get("title", "").lower()) if t not in stop_words and len(t) > 2}
                if svc_doc_slug and svc_doc_slug == api_doc_slug:
                    mapped_api_names.append(api_name)
                elif norm and (norm == api_name or (len(norm) >= 5 and (norm in api_name or api_name in norm))):
                    mapped_api_names.append(api_name)
                elif pname_tokens and title_tokens and pname_tokens == title_tokens:
                    mapped_api_names.append(api_name)

        apis_detail = []
        total_methods = 0
        sample_methods = []
        resources_set = set()
        for api_name in dict.fromkeys(mapped_api_names):
            if api_name in api_specs:
                used_apis.add(api_name)
                spec = api_specs[api_name]
                apis_detail.append(
                    {
                        "name": spec["name"],
                        "service_endpoint": spec["service_endpoint"],
                        "preferred_version": spec["preferred_version"],
                        "all_versions": spec["all_versions"],
                        "title": spec["title"],
                        "documentation_link": spec["documentation_link"],
                        "method_count": spec["method_count"],
                        "regional_method_count": spec["regional_method_count"],
                        "resources": spec["resources"],
                    }
                )
                total_methods += spec["method_count"]
                resources_set.update(spec["resources"])
                for m in spec["methods"]:
                    if len(sample_methods) < 60:
                        sample_methods.append(m)

        svc["apis"] = apis_detail
        svc["api_names"] = [a["service_endpoint"] for a in apis_detail]
        svc["total_api_methods"] = total_methods
        svc["resources"] = sorted(resources_set)
        svc["methods"] = sample_methods

    # Map AI models per region
    models_by_region: dict[str, list[dict[str, Any]]] = {rid: [] for rid in regions_dict}
    for m in ai_models_list:
        for rid in m.get("regions", []):
            if rid in models_by_region:
                models_by_region[rid].append(
                    {
                        "name": m["name"],
                        "model_name": m["name"],
                        "model_id": m["model_id"],
                        "family": m["family"],
                        "modality": m["modality"],
                        "stage": m["stage"],
                        "url": m["url"],
                        "docs_url": m["url"],
                    }
                )

    # Finalize serializable lists for regions and services
    total_available_regions = len(regions_dict)
    serialized_regions: list[dict[str, Any]] = []
    for rid in sorted(regions_dict.keys()):
        rinfo = regions_dict[rid]
        svc_list = sorted(rinfo["services"])
        reg_models = models_by_region.get(rid, [])
        serialized_regions.append(
            {
                "region_id": rinfo["region_id"],
                "region_name": rinfo["region_name"],
                "display_name": rinfo["display_name"],
                "full_location": rinfo["full_location"],
                "sub_region": rinfo["sub_region"],
                "status": rinfo["status"],
                "is_low_co2": rinfo["is_low_co2"],
                "lat": rinfo["lat"],
                "lng": rinfo["lng"],
                "date_launched": rinfo["date_launched"],
                "zones": rinfo["zones"],
                "zone_count": rinfo["zone_count"],
                "zone_details": rinfo["zone_details"],
                "machine_series": rinfo["machine_series"],
                "cpus": rinfo["cpus"],
                "gpus": rinfo["gpus"],
                "confidential_options": rinfo["confidential_options"],
                "services": svc_list,
                "service_count": len(svc_list),
                "ai_models": reg_models,
                "ai_model_count": len(reg_models),
            }
        )

    serialized_services: list[dict[str, Any]] = []
    for pname in sorted(services_dict.keys(), key=lambda x: x.lower()):
        svc = services_dict[pname]
        reg_list = sorted(svc["regions"])
        coverage_pct = round((len(reg_list) / total_available_regions) * 100, 1) if total_available_regions else 0.0
        serialized_services.append(
            {
                "name": svc["name"],
                "slug": svc["slug"],
                "category": svc["category"],
                "url": svc["url"],
                "scope": svc["scope"],
                "is_global": svc["is_global"],
                "regions": reg_list,
                "region_count": len(reg_list),
                "coverage_pct": coverage_pct,
                "multi_regions": svc["multi_regions"],
                "apis": svc["apis"],
                "api_names": svc["api_names"],
                "total_api_methods": svc["total_api_methods"],
                "resources": svc["resources"],
                "methods": svc["methods"],
            }
        )

    # Also serialize full Discovery API catalog for the Capabilities Explorer
    serialized_apis: list[dict[str, Any]] = []
    total_harvested_methods = 0
    for api_name in sorted(api_specs.keys()):
        spec = api_specs[api_name]
        total_harvested_methods += spec["method_count"]
        serialized_apis.append(
            {
                "name": spec["name"],
                "service_endpoint": spec["service_endpoint"],
                "preferred_version": spec["preferred_version"],
                "all_versions": spec["all_versions"],
                "title": spec["title"],
                "description": spec["description"],
                "documentation_link": spec["documentation_link"],
                "root_url": spec["root_url"],
                "resources": spec["resources"],
                "method_count": spec["method_count"],
                "regional_method_count": spec["regional_method_count"],
                "methods": spec["methods"][:80],
            }
        )

    print("[Harvester] Step 5/5: Computing snapshot diffs & What's New timeline...")
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build What's New feed from recent region launches + snapshot diff
    whats_new: list[dict[str, Any]] = []
    # Compare with previous snapshot if available
    prev_snapshots = sorted(p for p in SNAPSHOT_DIR.glob("*.json") if p.stem != today_str)
    if prev_snapshots:
        try:
            prev_data = json.loads(prev_snapshots[-1].read_text(encoding="utf-8"))
            prev_svc_map = {s["name"]: set(s["regions"]) for s in prev_data.get("services", [])}
            prev_regions = set(prev_data.get("regions", []))
            prev_apis = set(prev_data.get("apis", []))
            prev_models = {m["name"]: set(m.get("regions", [])) for m in prev_data.get("models", [])}

            # Detect brand-new regions
            for r in serialized_regions:
                if prev_regions and r["region_id"] not in prev_regions:
                    whats_new.append(
                        {
                            "date": today_str,
                            "type": "New Google Cloud Region",
                            "service": f"{r['service_count']} Regional Services",
                            "region_id": r["region_id"],
                            "region_name": r["region_name"],
                            "details": f"New Google Cloud Region {r['display_name']} launched in {r['full_location']}",
                        }
                    )

            # Detect brand-new services & regional expansions of existing services
            for s in serialized_services:
                if s["name"] not in prev_svc_map:
                    whats_new.append(
                        {
                            "date": today_str,
                            "type": "New Google Cloud Service",
                            "service": s["name"],
                            "region_id": f"{s['region_count']} regions" if s["region_count"] else s["scope"],
                            "region_name": s["category"],
                            "details": f"New Google Cloud service '{s['name']}' launched ({s['scope']}, {s['region_count']} regions)",
                        }
                    )
                else:
                    old_regs = prev_svc_map[s["name"]]
                    added_regs = sorted(set(s["regions"]) - old_regs)
                    for rid in added_regs:
                        r_obj = regions_dict.get(rid, {})
                        whats_new.append(
                            {
                                "date": today_str,
                                "type": "Regional Expansion",
                                "service": s["name"],
                                "region_id": rid,
                                "region_name": r_obj.get("region_name", rid),
                                "details": f"{s['name']} added to {r_obj.get('display_name', rid)}",
                            }
                        )

            # Detect brand-new AI models & regional expansions
            if prev_models:
                for m in ai_models_list:
                    if m["name"] not in prev_models:
                        whats_new.append(
                            {
                                "date": today_str,
                                "type": "New AI Model",
                                "service": m["name"],
                                "region_id": m["model_id"],
                                "region_name": m["family"],
                                "details": f"New AI Model '{m['name']}' ({m['model_id']}) launched in {m['endpoint_scope']}",
                            }
                        )

            # Detect brand-new Discovery REST APIs
            for a in serialized_apis:
                if prev_apis and a["service_endpoint"] not in prev_apis:
                    whats_new.append(
                        {
                            "date": today_str,
                            "type": "New Discovery API",
                            "service": a["title"],
                            "region_id": a["service_endpoint"],
                            "region_name": a["preferred_version"],
                            "details": f"New Google Cloud REST API {a['service_endpoint']} ({a['method_count']} operations)",
                        }
                    )
        except Exception:
            pass

    # Add chronological region launch history (recent launches first)
    for r in sorted(
        serialized_regions,
        key=lambda x: (str(x.get("date_launched", "0")), x["region_id"]),
        reverse=True,
    ):
        yr = str(r.get("date_launched", ""))
        if yr.isdigit() and int(yr) >= 2022:
            whats_new.append(
                {
                    "date": f"{yr}",
                    "type": "Region Launch",
                    "service": f"{r['service_count']} Regional Services",
                    "region_id": r["region_id"],
                    "region_name": r["region_name"],
                    "details": f"Google Cloud Region {r['display_name']} launched in {r['full_location']} ({r['zone_count']} zones)",
                }
            )

    for fr in future_regions_list:
        whats_new.append(
            {
                "date": "Upcoming",
                "type": "Announced Future Region",
                "service": "Core Google Cloud Launch Bundle",
                "region_id": fr["region_id"],
                "region_name": fr["region_name"],
                "details": f"Announced upcoming Google Cloud region in {fr['region_name']} ({fr['sub_region']})",
            }
        )

    elapsed = round(time.time() - start_ts, 2)
    catalog = {
        "meta": {
            "generated_at": now_iso,
            "generated_epoch": int(time.time()),
            "ttl_seconds": ttl_seconds,
            "refresh_policy": "Daily (24h Cache TTL with Exponential Backoff & Per-API Checkpointing)",
            "served_from_cache": False,
            "harvest_duration_seconds": elapsed,
            "fetcher_stats": fetcher.stats,
            "counts": {
                "total_services": len(serialized_services),
                "regional_services": sum(1 for s in serialized_services if s["region_count"] > 0),
                "multi_region_services": sum(1 for s in serialized_services if s["multi_regions"]),
                "global_services": sum(1 for s in serialized_services if s["is_global"]),
                "available_regions": len(serialized_regions),
                "future_regions": len(future_regions_list),
                "total_zones": sum(r["zone_count"] for r in serialized_regions),
                "gpu_zones": len(gpu_by_zone),
                "low_co2_regions": sum(1 for r in serialized_regions if r["is_low_co2"]),
                "ai_models": len(ai_models_list),
                "ai_model_families": len({m["family"] for m in ai_models_list}),
                "discovery_apis": len(serialized_apis),
                "total_api_methods": total_harvested_methods,
                "edge_pops": len(edge_pops),
                "cloud_cdn_pops": len(cdn_pops),
                "media_cdn_pops": len(media_cdn_pops),
            },
        },
        "regions": serialized_regions,
        "future_regions": future_regions_list,
        "services": serialized_services,
        "models": ai_models_list,
        "apis": serialized_apis,
        "pops": {
            "edge_pops": edge_pops,
            "cloud_cdn_pops": cdn_pops,
            "media_cdn_pops": media_cdn_pops,
        },
        "whats_new": whats_new,
    }

    # Save master catalog and daily snapshot atomically
    tmp_catalog = CATALOG_FILE.with_suffix(".json.tmp")
    tmp_catalog.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    tmp_catalog.replace(CATALOG_FILE)

    snapshot_file = SNAPSHOT_DIR / f"{today_str}.json"
    if not snapshot_file.exists() or force_refresh:
        snapshot_file.write_text(
            json.dumps(
                {
                    "date": today_str,
                    "generated_at": now_iso,
                    "regions": [r["region_id"] for r in serialized_regions],
                    "apis": [a["service_endpoint"] for a in serialized_apis],
                    "services": [
                        {"name": s["name"], "regions": s["regions"]}
                        for s in serialized_services
                    ],
                    "models": [
                        {"name": m["name"], "regions": m["regions"]}
                        for m in ai_models_list
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print(
        f"[Harvester] Completed in {elapsed}s! "
        f"Services={len(serialized_services)}, Regions={len(serialized_regions)} (+{len(future_regions_list)} future), "
        f"Zones={catalog['meta']['counts']['total_zones']}, AI Models={len(ai_models_list)}, "
        f"Discovery APIs={len(serialized_apis)}, REST Methods={total_harvested_methods}."
    )
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="GCP Services & Regional Capabilities Harvester")
    parser.add_argument("--force", action="store_true", help="Force re-harvest ignoring 24h cache TTL")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS, help="Cache TTL in seconds (default: 86400)")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent worker threads (default: 8)")
    parser.add_argument("--rate", type=float, default=15.0, help="Max requests per second (default: 15.0)")
    args = parser.parse_args()

    harvest_all(
        ttl_seconds=args.ttl,
        force_refresh=args.force,
        max_workers=args.workers,
        rate_per_sec=args.rate,
    )


if __name__ == "__main__":
    main()
