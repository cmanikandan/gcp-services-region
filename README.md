# Google Cloud Services & Regional Capabilities Explorer

> **⚠️ Unofficial Tool:** This is an unofficial tool — please refer to the [official Google Cloud documentation](https://cloud.google.com/docs) for the latest information.

> [!IMPORTANT]
> **⚠️ Unofficial Resource Disclaimer**
> This project is an **unofficial, independent community tool** and is **not** affiliated with, endorsed by, or sponsored by Google LLC or Google Cloud.
> While data is automatically harvested from public Google Cloud feeds, Vertex AI Model location matrices, and Google APIs Discovery specifications, it is provided **"as-is"** for informational and architectural exploration purposes only.
> **Always refer to the official Google Cloud documentation for the latest, authoritative information:**
> - **Official Google Cloud Locations & Regions**: [https://cloud.google.com/about/locations](https://cloud.google.com/about/locations)
> - **Vertex AI Generative AI Model Locations**: [https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)
> - **Compute Engine Regions & Availability Zones**: [https://cloud.google.com/compute/docs/regions-zones](https://cloud.google.com/compute/docs/regions-zones)
> - **GPU Regions & Zones Availability**: [https://cloud.google.com/compute/docs/gpus/gpu-regions-zones](https://cloud.google.com/compute/docs/gpus/gpu-regions-zones)
> - **Official Google Cloud Documentation**: [https://cloud.google.com/docs](https://cloud.google.com/docs)
> - **Google Cloud APIs & Discovery Reference**: [https://cloud.google.com/apis/docs/overview](https://cloud.google.com/apis/docs/overview)

---

A fast, locally runnable web application, static HTML generator, and terminal CLI tool for exploring **Google Cloud service availability by region**, **AI & Foundation Model regional availability**, **zone-level hardware/CPU/GPU capabilities**, **multi-region gap matrices**, and **API-level REST operations**.

---

## ✨ Key Features

1. **Daily Refresh & Local Static/JSON Cache (24h TTL)**:
   - Queries public Google Cloud Location feeds, Vertex AI Model regional availability tables, Compute Region/Zone & GPU matrices, and Google APIs Discovery REST specifications (`discovery.googleapis.com`) **once per day** (`86,400s` TTL).
   - All subsequent UI views, searches, AI model checks, region comparisons, and CLI queries are served **100% from local static HTML (`dist/`) and cached JSON (`data/cache/gcp_catalog.json`)** with zero external API calls.
2. **AI & Foundation Models Regional Availability (`dist/models.html` & `cli.py models`)**:
   - Check which **94+ First-Party and Partner AI Models across 16 Model Families** (Gemini, Veo Video, Embeddings, Chirp/TTS, Anthropic Claude, Meta Llama, Mistral/Codestral, DeepSeek, Grok, OpenAI `gpt-oss`, Qwen, Gemma, etc.) are available across `global`, Multi-Region (`us`, `eu`), and individual Google Cloud regions.
   - Filter simultaneously by **Model Name/ID**, **Model Family/Provider**, **Modality** (`Text & Multimodal`, `Video Generation`, `Audio, Speech & TTS`, `Image Generation`, `Embeddings`, `Code & Reasoning`, `Live Real-Time Streaming`), and **Google Cloud Region / Endpoint**.
   - Compare AI Model availability across up to 4 Google Cloud regions side-by-side in the **Capabilities & Multi-Region Matrix** (`dist/capabilities.html`).
3. **Quota & Rate-Limit Resilience (`ResilientFetcher` in `harvester.py`)**:
   - **Token-Bucket Rate Limiter**: Paces concurrent outbound requests (`15 req/sec` default across bounded workers) to prevent burst quota exhaustion.
   - **Exponential Backoff with Full Jitter**: Automatically retries HTTP `429 Too Many Requests`, `403 Rate Limit Exceeded`, and `5xx` errors while honoring `Retry-After` headers.
   - **Per-API Disk Checkpointing**: Checkpoints each of the 204+ Google Discovery REST specifications individually (`data/cache/discovery/{api}_{version}.json`) so interrupted runs resume instantaneously.
4. **Zero-Touch Discovery for Newly Launched Google Cloud Services, AI Models & Regions**:
   - Dynamically ingests any newly launched Google Cloud service, AI model, region, zone, machine series, GPU accelerator, or Discovery REST API on the next daily refresh without requiring code or dictionary updates.
   - Automatically links new services to their underlying `*.googleapis.com` Discovery REST APIs via documentation URL slug matching and title token similarity, and highlights newly launched services, AI models, regions, and APIs in **What's New** (`dist/whatsnew.html`).
5. **Comprehensive Multi-Source Google Cloud Dataset**:
   - **153 Unique Google Cloud Services** across Regional, Multi-Region (`US`, `EU`, `ASIA`), and Global scopes.
   - **94 AI & Foundation Models across 16 Families** with per-region and `global` / `us` / `eu` endpoint mapping.
   - **43 Available Google Cloud Regions** + **4 Announced Future Regions** (`Phoenix`, `Kuwait`, `Ankara`, `Kuala Lumpur`), including Low CO₂ 🌱 indicators and launch years.
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
Then open in your browser:
- **Services Explorer**: [http://127.0.0.1:8080/index.html](http://127.0.0.1:8080/index.html)
- **Regions Explorer**: [http://127.0.0.1:8080/regions.html](http://127.0.0.1:8080/regions.html)
- **AI Models Explorer**: [http://127.0.0.1:8080/models.html](http://127.0.0.1:8080/models.html)
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

# Check which AI & Foundation models are available (optionally filter by region)
python3 cli.py models gemini
python3 cli.py models claude --region us-east5
python3 cli.py models --region europe-west4

# Find all regions & API operations for a specific Google Cloud service
python3 cli.py service "Vertex AI"
python3 cli.py service alloydb

# Find all services, AI models, zones, machine series & GPUs in a specific Google Cloud region
python3 cli.py region us-central1
python3 cli.py region asia-south1

# Compare multiple Google Cloud regions side-by-side (use --diff to show only gaps)
python3 cli.py compare us-central1 europe-west1 asia-south1 --diff

# Force an immediate refresh of the 24h cache & rebuild static HTML
python3 cli.py refresh --force
```

---

## 📌 Disclaimer

This is an **unofficial tool** and is not affiliated with, maintained, authorized, endorsed, or sponsored by Google LLC. Please refer to the official Google Cloud documentation ([https://cloud.google.com/about/locations](https://cloud.google.com/about/locations) and [https://cloud.google.com/docs](https://cloud.google.com/docs)) for the latest information.

