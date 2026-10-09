# GCP Services & Regional Capabilities Explorer

A fast, locally runnable web application, static HTML generator, and CLI tool for exploring **Google Cloud Platform (GCP) service availability by region**, **zone-level hardware/CPU/GPU capabilities**, **multi-region gap matrices**, and **API-level REST operations**.

Inspired by:
- [aws-services.info](https://www.aws-services.info/index.html) ([Regions](https://www.aws-services.info/regions.html), [Architecture](https://www.aws-services.info/arch.html))
- [AWS Builder Capabilities by Region](https://builder.aws.com/build/capabilities)

---

## ✨ Key Features

1. **Daily Refresh & Local Static/JSON Cache (24h TTL)**:
   - Queries official Google Cloud Location feeds, Compute Region/Zone & GPU matrices, and Google APIs Discovery REST specifications (`discovery.googleapis.com`) **once per day** (`86,400s` TTL).
   - All subsequent UI views, searches, region comparisons, and CLI queries are served **100% from local static HTML (`dist/`) and cached JSON (`data/cache/gcp_catalog.json`)** with zero external API calls.
2. **Quota & Rate-Limit Resilience (`ResilientFetcher` in `harvester.py`)**:
   - **Token-Bucket Rate Limiter**: Paces concurrent outbound requests (`15 req/sec` default) to prevent burst quota exhaustion.
   - **Exponential Backoff with Full Jitter**: Automatically retries HTTP `429 Too Many Requests`, `403 Rate Limit Exceeded`, and `5xx` errors while respecting `Retry-After` headers.
   - **Per-API Disk Checkpointing**: Checkpoints each of the 204+ Google Discovery REST specifications individually (`data/cache/discovery/{api}_{version}.json`) so interrupted runs resume instantaneously.
3. **Comprehensive Multi-Source GCP Dataset**:
   - **153 Unique GCP Services** across Regional, Multi-Region (`US`, `EU`, `ASIA`), and Global scopes.
   - **43 Available GCP Regions** + **4 Announced Future Regions** (`Phoenix`, `Kuwait`, `Ankara`, `Kuala Lumpur`), including Low CO₂ 🌱 indicators and launch years.
   - **130 Availability Zones** with exact Compute Machine Series (`E2`, `N4`, `C4`, `C4A`, `A4X`, `A3`, `G2`, `Z3`, `M4`, etc.), CPU microarchitectures (`Intel Granite Rapids`, `Emerald Rapids`, `Google Axion`, `AMD EPYC Turin`, `NVIDIA Grace`), Confidential Computing support (`AMD SEV`, `SEV-SNP`, `Intel TDX`, `NVIDIA Confidential Computing`), and **89 GPU-enabled zones**.
   - **204 Google Discovery REST APIs** (`*.googleapis.com`) with **10,501 harvested REST API methods/operations** (`id`, `httpMethod`, `path`, `scopes`, `description`).
   - **238 Global Network PoPs** (101 Edge PoPs, 75 Cloud CDN PoPs, 62 Media CDN PoPs).

---

## 🚀 Quick Start (Zero External Dependencies)

Requires only standard **Python 3.10+** (uses Python standard library only):

### 1. Run the Local Web Application Server
```bash
python3 server.py --port 8080
```
Then open:
- **Services Explorer**: [http://127.0.0.1:8080/index.html](http://127.0.0.1:8080/index.html)
- **Regions Explorer**: [http://127.0.0.1:8080/regions.html](http://127.0.0.1:8080/regions.html)
- **Capabilities & Multi-Region Matrix**: [http://127.0.0.1:8080/capabilities.html](http://127.0.0.1:8080/capabilities.html)
- **130 Zones & Edge PoPs**: [http://127.0.0.1:8080/pops.html](http://127.0.0.1:8080/pops.html)
- **What's New**: [http://127.0.0.1:8080/whatsnew.html](http://127.0.0.1:8080/whatsnew.html)
- **Architecture & Cost**: [http://127.0.0.1:8080/arch.html](http://127.0.0.1:8080/arch.html)
- **FAQs & CLI Guide**: [http://127.0.0.1:8080/faqs.html](http://127.0.0.1:8080/faqs.html)

*(Or open `dist/index.html` directly in your browser without a server!)*

### 2. Query via Terminal CLI (`cli.py`)
```bash
# View cache status & summary counts
python3 cli.py status

# Find all regions & API operations for a specific GCP service
python3 cli.py service "Vertex AI"
python3 cli.py service alloydb

# Find all services, zones, machine series & GPUs in a specific GCP region
python3 cli.py region us-central1
python3 cli.py region asia-south1

# Compare multiple GCP regions side-by-side (use --diff to show only gaps)
python3 cli.py compare us-central1 europe-west1 asia-south1 --diff

# Force an immediate refresh of the 24h cache & rebuild static HTML
python3 cli.py refresh --force
```
