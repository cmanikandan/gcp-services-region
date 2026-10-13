# AGENTS.md — AI Coding Agent Instructions & Architectural Guide

This file defines the architectural invariants, coding standards, data pipelines, and operational workflows for AI coding agents working in the **`gcp-services-region`** repository (**Google Cloud Services & Regional Capabilities Explorer**).

---

## 1. Project Overview

**Google Cloud Services & Regional Capabilities Explorer** is a fast, zero-dependency web application, static HTML generator, and terminal CLI tool that maps and compares:
- **153+ Google Cloud Services** across Regional, Multi-Region (`US`, `EU`, `ASIA`), and Global scopes.
- **43+ Active Google Cloud Regions** (+ announced future regions) with Low CO₂ 🌱 sustainability indicators and launch years.
- **94+ AI & Foundation Models across 16 Families** (Gemini, Veo, Embeddings, Chirp, Anthropic Claude, Meta Llama, Mistral, DeepSeek, Grok, OpenAI `gpt-oss`, Qwen, Gemma, etc.) mapped across `global`, multi-region (`us`, `eu`), and regional endpoints.
- **130+ Availability Zones** with exact Compute machine series, CPU microarchitectures, GPU accelerators, and Confidential Computing support, plus **238+ Edge & CDN PoPs**.
- **204+ Google Discovery REST APIs** (`*.googleapis.com`) and **10,500+ REST API operations** (`GET`, `POST`, `PATCH`, `PUT`, `DELETE`).

---

## 2. Strict Engineering & Content Rules (MUST FOLLOW)

1. **Zero External Dependencies (Python Standard Library Only)**
   - All Python scripts ([`harvester.py`](harvester.py), [`generator.py`](generator.py), [`server.py`](server.py), [`cli.py`](cli.py)) **MUST** use only the Python 3.10+ standard library (`urllib.request`, `html.parser`, `json`, `http.server`, `concurrent.futures`, `threading`, `argparse`, `pathlib`, `re`, `time`).
   - Do **not** introduce third-party PyPI packages (`requests`, `beautifulsoup4`, `flask`, `fastapi`, etc.) or frontend npm build steps unless explicitly instructed by the user.

2. **Branding, Naming & Disclaimer Standards**
   - Always use **"Google Cloud"** (never `"GCP"`) in all user-facing titles, headers, navigation bars, KPI cards, and documentation.
   - Always maintain a clear, professional notice that this is an **unofficial tool** and that users should refer to the [official Google Cloud documentation](https://cloud.google.com/docs) for the latest authoritative information.
   - **Never** add *"inspired by..."* references or comparisons to third-party/competitor websites in [`README.md`](README.md) or generated HTML pages.

3. **24-Hour Local Cache & Quota Resilience**
   - User-facing web requests ([`server.py`](server.py)) and CLI commands ([`cli.py`](cli.py)) must **never** trigger live outbound calls to Google Cloud endpoints during normal reads. They must read strictly from `data/cache/gcp_catalog.json` and `dist/`.
   - All outbound HTTP calls inside [`harvester.py`](harvester.py) must go through `ResilientFetcher`, which enforces:
     - Thread-safe **Token-Bucket rate limiting** (default `15 req/sec` across `8` bounded worker threads).
     - **Exponential backoff with full jitter** on HTTP `429`, `403`, and `5xx` responses, honoring `Retry-After` headers.
     - **Per-API disk checkpointing** (`data/cache/discovery/{api}_{version}.json`) and graceful fallback to stale cache on network errors.

4. **Zero-Touch Dynamic Discovery (Future-Proofing)**
   - Never replace dynamic feed parsing with static closed allowlists. When Google Cloud launches a new service, AI model, region, zone, machine series, GPU, or Discovery REST API, [`harvester.py`](harvester.py) must automatically ingest it on the next refresh:
     - New services in `data.json` are automatically linked to `*.googleapis.com` Discovery APIs via 3-tier matching: (1) explicit hints in `SERVICE_API_HINTS`, (2) documentation URL slug matching against API names, and (3) normalized title token similarity.
     - Daily snapshots in `data/cache/snapshots/YYYY-MM-DD.json` automatically compute diffs for [`dist/whatsnew.html`](dist/whatsnew.html).

5. **UI/UX, Header Layout & Browser Cache-Busting**
   - Keep `.site-header` in [`generator.py`](generator.py) as a clean, single-row navigation bar (SVG cloud icon, 2-line brand block with subtle `Unofficial` tag, single-line `.nav-pills`, snapshot badge, Dark/Light theme toggle, and Refresh button). Do **not** add noisy warning banners above `.site-header`.
   - Always append cache-busting query strings (`?v={asset_v}`) to `assets/style.css`, `assets/app.js`, and `data/matrix_data.js` in [`generator.py`](generator.py).
   - Keep `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` in `GCPExplorerHandler.end_headers()` inside [`server.py`](server.py) so local browsers never serve stale HTML/CSS/JS.

---

## 3. Repository Architecture & File Map

```text
gcp-services-region/
├── AGENTS.md                  # AI agent instructions & architectural invariants (this file)
├── README.md                  # Project documentation, visual tour screenshots & feature backlog
├── harvester.py               # Quota-resilient multi-source Google Cloud & Vertex AI data harvester
├── generator.py               # Static HTML5, CSS3 & vanilla JS generator (builds 204+ pages in dist/)
├── server.py                  # Local HTTP server + JSON REST API + 24h auto-refresh daemon thread
├── cli.py                     # Terminal CLI for querying services, regions, AI models & diffs
├── docs/
│   └── screenshots/           # High-resolution PNG screenshots embedded in README.md
├── data/
│   └── cache/
│       ├── gcp_catalog.json   # Unified master catalog (24-hour TTL)
│       ├── discovery/         # Per-API cached Google Discovery REST specs (*.json)
│       └── snapshots/         # Daily dated snapshots (YYYY-MM-DD.json) for What's New diffs
└── dist/                      # Pre-rendered static website (generated by generator.py)
    ├── index.html             # Google Cloud Services Explorer
    ├── regions.html           # Google Cloud Regions Explorer
    ├── models.html            # Google Cloud AI & Foundation Models Explorer
    ├── capabilities.html      # 4-Region Comparison Matrix (Services & AI Models) + Discovery APIs
    ├── pops.html              # 130 Availability Zones (Hardware/CPU/GPU) & 238 Edge/CDN PoPs
    ├── whatsnew.html          # What's New & Daily Snapshot Diffs
    ├── arch.html              # Architecture, Quota Protection & Cloud Hosting Cost Breakdown
    ├── faqs.html              # FAQs & CLI Reference
    ├── assets/                # Shared style.css and app.js
    ├── data/                  # Pre-computed matrix_data.js for 4-region comparisons
    ├── services/*.html        # 153 dedicated Google Cloud service detail pages
    └── regions/*.html         # 43 dedicated Google Cloud region detail pages
```

---

## 4. Common Workflows & Commands

### Rebuild Static HTML After Editing `generator.py`
```bash
python3 generator.py
```

### Force a Live Upstream Harvest & Rebuild Static Site
```bash
python3 harvester.py --force && python3 generator.py
```

### Run the Local Web Server (Default Port `8080`)
```bash
python3 server.py --port 8080
```
- **JSON REST Endpoints served by `server.py`**:
  - `GET /api/status` — Cache metadata, snapshot timestamp, and entity counts
  - `GET /api/services?q=&category=&region=` — Filterable services JSON
  - `GET /api/regions?q=` — Filterable regions & future regions JSON
  - `GET /api/models?q=&family=&region=` — Filterable AI & Foundation models JSON
  - `GET /api/compare?regions=us-central1,europe-west1,asia-south1` — Multi-region comparison JSON
  - `POST /api/refresh` — Triggers an on-demand harvest and static HTML regeneration

### Query via Terminal CLI (`cli.py`)
```bash
python3 cli.py status
python3 cli.py service "Vertex AI"
python3 cli.py models gemini
python3 cli.py models claude --region us-east5
python3 cli.py region asia-south1
python3 cli.py compare us-central1 europe-west1 asia-south1 --diff
```

### Supported URL Query Parameters in the Web UI
All table views and the comparison matrix in `dist/` support deep-linking via URL query parameters:
- `?theme=dark` or `?theme=light` — Override Dark / Light theme
- `?q=<search_term>` — Pre-fill search input on any table page
- `?f1=<value>` / `?f2=<value>` — Pre-select dropdown filters (e.g., Category / Modality)
- `?region=<region_id>` — Filter AI models by region or endpoint on `models.html` (e.g., `models.html?region=asia-south1`)
- `?mode=models&diff=1` — Switch `capabilities.html` into AI Models comparison mode showing differences/gaps only
- `?flag=1` — Enable checkbox filter (e.g., Low CO₂ regions on `regions.html` or GPU zones on `pops.html`)
