#!/usr/bin/env python3
"""
Static HTML & Interactive Capabilities Generator (generator.py)

Generates a fast, zero-external-dependency static HTML website in `dist/` from
the harvested `data/cache/gcp_catalog.json` dataset:
  - dist/index.html              : Google Cloud Services Explorer (searchable/filterable table)
  - dist/regions.html            : Google Cloud Regions Explorer (43 available + 4 future regions)
  - dist/models.html             : Google Cloud AI & Foundation Models Regional Availability Explorer
  - dist/capabilities.html       : Multi-Region Comparison Matrix (Services & AI Models) + REST APIs
  - dist/pops.html               : 130 Availability Zones (Hardware/CPU/GPU) + Edge & CDN PoPs
  - dist/whatsnew.html           : What's New & Daily Snapshot Diffs
  - dist/arch.html               : Local & Serverless Google Cloud Architecture + Cost Breakdown
  - dist/faqs.html               : FAQs, Quota Resilience Details & CLI Reference
  - dist/services/<slug>.html    : Dedicated static page for every Google Cloud Service + REST API methods
  - dist/regions/<region>.html   : Dedicated static page for every Google Cloud Region + AI Models & Zone Hardware
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from enrichment import build_mobile_catalog
from harvester import CATALOG_FILE, harvest_all

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"


def esc(val: Any) -> str:
    return html.escape(str(val if val is not None else ""))


def write_shared_assets() -> None:
    """Write shared CSS and JS helpers to dist/assets/."""
    assets_dir = DIST_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    css = """
:root {
  --gcp-blue: #1a73e8;
  --gcp-blue-dark: #1557b0;
  --gcp-blue-light: #e8f0fe;
  --gcp-green: #137333;
  --gcp-green-light: #e6f4ea;
  --gcp-yellow: #b06000;
  --gcp-yellow-light: #fef7e0;
  --gcp-red: #c5221f;
  --gcp-red-light: #fce8e6;
  --gcp-purple: #681da8;
  --gcp-purple-light: #f3e8fd;
  --bg-page: #f4f6f9;
  --bg-card: #ffffff;
  --bg-header: rgba(255, 255, 255, 0.94);
  --bg-subtle: #f8fafd;
  --bg-row-even: #fafbfd;
  --bg-row-hover: #eef5ff;
  --bg-chip: #f1f3f4;
  --text-main: #1f2937;
  --text-muted: #5f6368;
  --border-color: #dadce0;
  --border-subtle: #e5e7eb;
  --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.07), 0 2px 4px rgba(15, 23, 42, 0.04);
}

html[data-theme="dark"] {
  --gcp-blue: #60a5fa;
  --gcp-blue-dark: #3b82f6;
  --gcp-blue-light: rgba(59, 130, 246, 0.18);
  --gcp-green: #4ade80;
  --gcp-green-light: rgba(34, 197, 94, 0.18);
  --gcp-yellow: #fbbf24;
  --gcp-yellow-light: rgba(245, 158, 11, 0.18);
  --gcp-red: #f87171;
  --gcp-red-light: rgba(239, 68, 68, 0.18);
  --gcp-purple: #c084fc;
  --gcp-purple-light: rgba(168, 85, 247, 0.18);
  --bg-page: #0b0f19;
  --bg-card: #111827;
  --bg-header: rgba(17, 24, 39, 0.94);
  --bg-subtle: #1e293b;
  --bg-row-even: #131c2e;
  --bg-row-hover: #1e293b;
  --bg-chip: #1e293b;
  --text-main: #f3f4f6;
  --text-muted: #9ca3af;
  --border-color: #374151;
  --border-subtle: #1f2937;
  --shadow-sm: 0 2px 6px rgba(0, 0, 0, 0.35);
  --shadow-md: 0 8px 20px rgba(0, 0, 0, 0.45);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: var(--bg-page);
  color: var(--text-main);
  line-height: 1.5;
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
  transition: background-color 0.15s ease, color 0.15s ease;
}

a {
  color: var(--gcp-blue);
  text-decoration: none;
  transition: color 0.15s ease;
}
a:hover {
  text-decoration: underline;
}

/* Header & Navigation */
.site-header {
  background: var(--bg-header);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-sm);
}
.header-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 10px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  font-size: 14px;
  font-weight: 400;
  color: var(--text-main);
  text-decoration: none !important;
  flex-shrink: 0;
}
.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: var(--gcp-blue-light);
  border: 1px solid rgba(26, 115, 232, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.2px;
  display: flex;
  align-items: center;
  gap: 7px;
}
.unofficial-tag {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--bg-chip);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}
.brand-subtitle {
  font-size: 11.5px;
  font-weight: 400;
  color: var(--text-muted);
  margin-top: 1px;
}

.nav-pills {
  display: flex;
  align-items: center;
  gap: 2px;
  list-style: none;
  margin: 0;
  padding: 3px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  overflow-x: auto;
  max-width: 100%;
}
.nav-link {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 7px;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  transition: all 0.15s ease;
  text-decoration: none !important;
}
.nav-link:hover {
  color: var(--text-main);
  background: var(--bg-card);
}
.nav-link.active {
  background: var(--gcp-blue);
  color: #ffffff;
  box-shadow: 0 1px 4px rgba(26, 115, 232, 0.3);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  flex-shrink: 0;
}
.cache-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 6px;
  background: var(--gcp-green-light);
  color: var(--gcp-green);
  font-weight: 600;
  font-size: 11.5px;
  white-space: nowrap;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border-radius: 7px;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-main);
  white-space: nowrap;
  transition: all 0.15s ease;
  text-decoration: none !important;
}
.btn:hover {
  border-color: var(--gcp-blue);
  background: var(--bg-subtle);
}
.btn-primary {
  background: var(--gcp-blue);
  color: #ffffff;
  border-color: var(--gcp-blue);
}
.btn-primary:hover {
  background: var(--gcp-blue-dark);
  color: #ffffff;
}

@media (max-width: 1180px) {
  .header-inner {
    flex-wrap: wrap;
  }
  .nav-pills {
    order: 3;
    width: 100%;
    justify-content: flex-start;
  }
}

/* Main Container */
.container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px 24px 56px;
}

/* Status & Summary Banner */
.status-bar {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-left: 4px solid var(--gcp-blue);
  border-radius: 10px;
  padding: 12px 18px;
  margin-bottom: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  font-size: 13px;
}

/* Interactive KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.kpi-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #4285f4, #34a853, #fbbc05, #ea4335);
  opacity: 0.85;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--gcp-blue);
}
.kpi-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.kpi-value {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: var(--gcp-blue);
}
.kpi-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
}

/* Filter & Search Bar */
.toolbar {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-sm);
}
.toolbar-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  flex: 1;
}
.search-input {
  min-width: 240px;
  flex: 1;
  max-width: 420px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 7px;
  font-size: 13px;
  background: var(--bg-subtle);
  color: var(--text-main);
  outline: none;
  transition: all 0.15s ease;
}
.search-input:focus {
  background: var(--bg-card);
  border-color: var(--gcp-blue);
  box-shadow: 0 0 0 3px var(--gcp-blue-light);
}
.select-input {
  padding: 8px 11px;
  border: 1px solid var(--border-color);
  border-radius: 7px;
  font-size: 13px;
  font-weight: 500;
  background: var(--bg-subtle);
  color: var(--text-main);
  outline: none;
  cursor: pointer;
}
.select-input:focus {
  border-color: var(--gcp-blue);
}
.count-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-subtle);
  padding: 5px 12px;
  border-radius: 16px;
  border: 1px solid var(--border-subtle);
  white-space: nowrap;
}

/* Data Tables */
.table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
.table-scroll {
  overflow-x: auto;
}
table.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 13px;
}
table.data-table thead tr {
  background: var(--bg-subtle);
  border-bottom: 2px solid var(--border-color);
}
table.data-table th {
  padding: 11px 14px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease;
}
table.data-table th:hover {
  color: var(--gcp-blue);
  background: var(--bg-row-hover);
}
table.data-table td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}
table.data-table tbody tr:nth-child(even) {
  background-color: var(--bg-row-even);
}
table.data-table tbody tr:hover {
  background-color: var(--bg-row-hover);
}

/* Badges & Pills */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.badge-blue { background: var(--gcp-blue-light); color: var(--gcp-blue); }
.badge-green { background: var(--gcp-green-light); color: var(--gcp-green); }
.badge-yellow { background: var(--gcp-yellow-light); color: var(--gcp-yellow); }
.badge-red { background: var(--gcp-red-light); color: var(--gcp-red); }
.badge-purple { background: var(--gcp-purple-light); color: var(--gcp-purple); }
.badge-gray { background: var(--bg-chip); color: var(--text-muted); }

.code-chip {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11.5px;
  background: var(--bg-chip);
  color: var(--text-main);
  padding: 2px 7px;
  border-radius: 5px;
  border: 1px solid var(--border-color);
  display: inline-block;
  margin: 1px 2px;
}
.code-chip-match {
  background: var(--gcp-green-light) !important;
  color: var(--gcp-green) !important;
  border-color: var(--gcp-green) !important;
  font-weight: 700 !important;
}

/* Progress bar */
.cov-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cov-bar {
  width: 84px;
  height: 6px;
  background: var(--border-subtle);
  border-radius: 4px;
  overflow: hidden;
}
.cov-fill {
  height: 100%;
  background: linear-gradient(90deg, #1a73e8, #34a853);
  border-radius: 4px;
}

/* HTTP Verb badges */
.verb {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  display: inline-block;
  min-width: 52px;
  text-align: center;
}
.verb-GET { background: var(--gcp-blue-light); color: var(--gcp-blue); }
.verb-POST { background: var(--gcp-green-light); color: var(--gcp-green); }
.verb-PATCH, .verb-PUT { background: var(--gcp-yellow-light); color: var(--gcp-yellow); }
.verb-DELETE { background: var(--gcp-red-light); color: var(--gcp-red); }

/* Section Cards */
.section-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 20px 22px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
}
.section-title {
  margin: 0 0 10px 0;
  font-size: 16.5px;
  font-weight: 700;
  letter-spacing: -0.2px;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Footer */
.site-footer {
  margin-top: 40px;
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
  background: var(--bg-card);
}
.footer-inner {
  max-width: 1100px;
  margin: 0 auto;
  line-height: 1.6;
}

/* Interactive Studio Grids & Responsive Mobile Form Factor */
.studio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}
.calc-metric-box {
  background: var(--bg-subtle);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.calc-big-num {
  font-size: 28px;
  font-weight: 800;
  color: var(--gcp-blue);
  letter-spacing: -0.02em;
}
@media (max-width: 960px) {
  .header-inner {
    flex-wrap: wrap;
    gap: 10px;
    padding: 10px 14px;
  }
  .nav-pills {
    order: 3;
    width: 100%;
    overflow-x: auto;
    padding-bottom: 4px;
    scrollbar-width: none;
  }
  .nav-pills::-webkit-scrollbar { display: none; }
  .container { padding: 14px 12px 32px; }
  .toolbar { flex-direction: column; align-items: stretch; }
  .toolbar-group { flex-direction: column; align-items: stretch; }
  .search-input, .select-input { width: 100% !important; min-width: 0 !important; }
  .status-bar { flex-direction: column; align-items: flex-start; gap: 8px; }
}
"""
    (assets_dir / "style.css").write_text(css.strip() + "\n", encoding="utf-8")

    js = """
// Theme initialization & toggle (Light / Dark mode)
(function initTheme() {
  try {
    const params = new URLSearchParams(window.location.search);
    const urlTheme = params.get('theme');
    const saved = urlTheme || localStorage.getItem('gcp_explorer_theme');
    if (saved === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else if (urlTheme === 'light') {
      document.documentElement.removeAttribute('data-theme');
    }
  } catch (e) {}
})();

function updateThemeButtonLabel() {
  const btn = document.getElementById('theme-toggle-btn');
  if (!btn) return;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  btn.innerHTML = isDark ? '☀️ Light' : '🌙 Dark';
}

window.toggleTheme = function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  if (next === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  try {
    localStorage.setItem('gcp_explorer_theme', next);
  } catch (e) {}
  updateThemeButtonLabel();
};

function updateConnectivityPill() {
  const pill = document.getElementById('offline-status-pill');
  if (!pill) return;
  if (navigator.onLine === false) {
    pill.textContent = '✈️ Offline Mode (Cached)';
    pill.className = 'badge badge-yellow';
  } else {
    pill.textContent = '✓ Offline PWA Ready';
    pill.className = 'badge badge-green';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  updateThemeButtonLabel();
  updateConnectivityPill();
  window.addEventListener('online', updateConnectivityPill);
  window.addEventListener('offline', updateConnectivityPill);

  // Register Offline Service Worker when served over HTTP(S)
  if ('serviceWorker' in navigator && (window.location.protocol === 'http:' || window.location.protocol === 'https:')) {
    const swPrefix = document.documentElement.getAttribute('data-root-prefix') || '';
    navigator.serviceWorker.register(swPrefix + 'sw.js').catch(() => {});
  }

  // Press '/' to quickly focus the primary search box on any page
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
      const search = document.querySelector('input[type="search"]');
      if (search) {
        e.preventDefault();
        search.focus();
      }
    }
  });
});

// Shared table sorting, filtering, and local refresh trigger
window.setupTableFilter = function setupTableFilter(config) {
  const searchInput = document.getElementById(config.searchId);
  const select1 = config.select1Id ? document.getElementById(config.select1Id) : null;
  const select2 = config.select2Id ? document.getElementById(config.select2Id) : null;
  const select3 = config.select3Id ? document.getElementById(config.select3Id) : null;
  const checkbox = config.checkboxId ? document.getElementById(config.checkboxId) : null;
  const resetBtn = config.resetId ? document.getElementById(config.resetId) : null;
  const table = document.getElementById(config.tableId);
  const countEl = document.getElementById(config.countId);
  if (!table) return;

  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const total = rows.length;

  try {
    const params = new URLSearchParams(window.location.search);
    if (searchInput && params.get('q')) searchInput.value = params.get('q');
    if (select1 && params.get('f1')) select1.value = params.get('f1');
    if (select2 && params.get('f2')) select2.value = params.get('f2');
    if (select3 && (params.get('region') || params.get('f3'))) select3.value = params.get('region') || params.get('f3');
    if (checkbox && params.get('flag') === '1') checkbox.checked = true;
  } catch (e) {}

  function applyFilter() {
    const q = (searchInput ? searchInput.value : '').trim().toLowerCase();
    const v1 = select1 ? select1.value : '';
    const v2 = select2 ? select2.value : '';
    const v3 = select3 ? select3.value : '';
    const cb = checkbox ? checkbox.checked : false;
    let visible = 0;

    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      const attr1 = row.getAttribute('data-filter1') || '';
      const attr2 = row.getAttribute('data-filter2') || '';
      const attr3 = row.getAttribute('data-filter3') || '';
      const attrCb = row.getAttribute('data-flag') === 'true';

      const tokens1 = attr1.split('|');
      const tokens2 = attr2.split('|');
      const tokens3 = attr3.split('|');

      const matchQ = !q || text.includes(q);
      const match1 = !v1 || attr1 === v1 || tokens1.includes(v1);
      const match2 = !v2 || attr2 === v2 || tokens2.includes(v2);
      const match3 = !v3 || attr3 === v3 || tokens3.includes(v3);
      const matchCb = !cb || attrCb;

      if (matchQ && match1 && match2 && match3 && matchCb) {
        row.style.display = '';
        visible++;
        if (config.highlightRegionAttr && v3) {
          row.querySelectorAll('[data-rid]').forEach(chip => {
            if (chip.getAttribute('data-rid') === v3) {
              chip.classList.add('code-chip-match');
              const extraWrap = chip.closest('.extra-rids');
              if (extraWrap) {
                extraWrap.style.display = 'inline';
                const toggleBtn = row.querySelector('.more-rids-toggle');
                if (toggleBtn) toggleBtn.style.display = 'none';
              }
            } else {
              chip.classList.remove('code-chip-match');
            }
          });
        } else if (config.highlightRegionAttr) {
          row.querySelectorAll('.code-chip-match').forEach(chip => chip.classList.remove('code-chip-match'));
        }
      } else {
        row.style.display = 'none';
      }
    });

    if (countEl) {
      countEl.textContent = `Showing ${visible} of ${total}`;
    }
  }

  if (searchInput) searchInput.addEventListener('input', applyFilter);
  if (select1) select1.addEventListener('change', applyFilter);
  if (select2) select2.addEventListener('change', applyFilter);
  if (select3) select3.addEventListener('change', applyFilter);
  if (checkbox) checkbox.addEventListener('change', applyFilter);
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (select1) select1.value = '';
      if (select2) select2.value = '';
      if (select3) select3.value = '';
      if (checkbox) checkbox.checked = false;
      applyFilter();
    });
  }

  // Column sorting
  const headers = table.querySelectorAll('th[data-sort]');
  headers.forEach((th, colIdx) => {
    let asc = true;
    th.addEventListener('click', () => {
      const sortType = th.getAttribute('data-sort');
      asc = !asc;
      rows.sort((a, b) => {
        const cellA = a.children[colIdx];
        const cellB = b.children[colIdx];
        const valA = cellA ? (cellA.getAttribute('data-val') || cellA.textContent.trim()) : '';
        const valB = cellB ? (cellB.getAttribute('data-val') || cellB.textContent.trim()) : '';
        if (sortType === 'num') {
          const nA = parseFloat(valA) || 0;
          const nB = parseFloat(valB) || 0;
          return asc ? nA - nB : nB - nA;
        }
        return asc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      });
      rows.forEach(r => tbody.appendChild(r));
    });
  });

  applyFilter();
};

window.triggerHarvestRefresh = async function triggerHarvestRefresh(btn) {
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '⏳ Refreshing...';
  try {
    const resp = await fetch('/api/refresh', { method: 'POST' });
    if (resp.ok) {
      window.location.reload();
      return;
    }
    alert('Static file mode detected. Run `python3 harvester.py --force && python3 generator.py` or start `python3 server.py` to refresh via UI.');
  } catch (e) {
    alert('Static file mode: Run `python3 server.py` or `python3 cli.py refresh` to trigger a live API harvest.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = orig;
  }
};
"""
    (assets_dir / "app.js").write_text(js.strip() + "\n", encoding="utf-8")


def write_pwa_offline_assets(catalog: dict[str, Any]) -> None:
    """Write mobile_catalog.json, manifest.webmanifest, icon.svg, and Service Worker sw.js for 100% offline PWA support."""
    assets_dir = DIST_DIR / "assets"
    data_dir = DIST_DIR / "data"
    assets_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    mobile_payload = build_mobile_catalog(catalog)
    (data_dir / "mobile_catalog.json").write_text(
        json.dumps(mobile_payload, separators=(",", ":")),
        encoding="utf-8",
    )

    icon_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="28" fill="#0b0f19"/>
  <path d="M88 86H44a24 24 0 1 1 23-31h6a16 16 0 1 1 15 31Z" fill="none" stroke="#60a5fa" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="88" cy="44" r="9" fill="#4ade80"/>
</svg>"""
    (assets_dir / "icon.svg").write_text(icon_svg, encoding="utf-8")

    manifest = {
        "name": "Google Cloud Services & Regions Explorer (Unofficial)",
        "short_name": "Cloud Explorer",
        "description": "Offline-capable explorer for Google Cloud service availability, AI models, regional pricing, SLAs, and release updates (Unofficial).",
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#0b0f19",
        "theme_color": "#1a73e8",
        "icons": [
            {
                "src": "assets/icon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any maskable",
            }
        ],
    }
    (DIST_DIR / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    cache_ver = f"gcp-explorer-pwa-{catalog.get('meta', {}).get('generated_epoch', 1)}"
    sw_js = f"""
const CACHE_NAME = '{cache_ver}';
const PRECACHE_URLS = [
  './',
  './index.html',
  './regions.html',
  './models.html',
  './pricing-sla.html',
  './capabilities.html',
  './pops.html',
  './whatsnew.html',
  './arch.html',
  './faqs.html',
  './manifest.webmanifest',
  './assets/icon.svg',
  './assets/style.css',
  './assets/app.js',
  './data/matrix_data.js',
  './data/mobile_catalog.json'
];

self.addEventListener('install', (event) => {{
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS).catch(() => {{}}))
  );
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', (event) => {{
  if (event.request.method !== 'GET') return;
  event.respondWith(
    fetch(event.request)
      .then((networkResp) => {{
        if (networkResp && networkResp.status === 200) {{
          const copy = networkResp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        }}
        return networkResp;
      }})
      .catch(() => caches.match(event.request, {{ ignoreSearch: true }}).then((cached) => cached || caches.match('./index.html')))
  );
}});
"""
    (DIST_DIR / "sw.js").write_text(sw_js.strip() + "\n", encoding="utf-8")


def render_layout(
    title: str,
    active_tab: str,
    body_html: str,
    meta: dict[str, Any],
    root_prefix: str = "",
) -> str:
    """Wrap page content in the standard navigation layout."""
    counts = meta.get("counts", {})
    gen_at = meta.get("generated_at", "")
    gen_date = gen_at.split(" ")[0] if gen_at else "Daily"
    asset_v = f"{meta.get('generated_epoch', 1)}-v3"
    tabs = [
        ("services", "Services", f"{root_prefix}index.html"),
        ("regions", "Regions", f"{root_prefix}regions.html"),
        ("models", "AI Models", f"{root_prefix}models.html"),
        ("pricing-sla", "Pricing & SLA", f"{root_prefix}pricing-sla.html"),
        ("capabilities", "Compare Matrix", f"{root_prefix}capabilities.html"),
        ("pops", "Zones & PoPs", f"{root_prefix}pops.html"),
        ("whatsnew", "What's New", f"{root_prefix}whatsnew.html"),
        ("arch", "Architecture", f"{root_prefix}arch.html"),
        ("faqs", "FAQs", f"{root_prefix}faqs.html"),
    ]
    nav_items = "\n".join(
        f'<li><a href="{href}" class="nav-link {"active" if key == active_tab else ""}">{label}</a></li>'
        for key, label, href in tabs
    )

    return f"""<!DOCTYPE html>
<html lang="en" data-root-prefix="{root_prefix}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#1a73e8">
  <title>{esc(title)} | Google Cloud Services &amp; Regional Capabilities (Unofficial)</title>
  <link rel="icon" type="image/svg+xml" href="{root_prefix}assets/icon.svg">
  <link rel="manifest" href="{root_prefix}manifest.webmanifest">
  <link rel="stylesheet" href="{root_prefix}assets/style.css?v={asset_v}">
  <script src="{root_prefix}assets/app.js?v={asset_v}"></script>
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="{root_prefix}index.html">
        <div class="brand-logo" title="Google Cloud Services &amp; Regions Explorer">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--gcp-blue)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
          </svg>
        </div>
        <div class="brand-text">
          <div class="brand-title">
            <span>Google Cloud Services &amp; Regions</span>
            <span class="unofficial-tag">Unofficial</span>
          </div>
          <span class="brand-subtitle">Availability, AI Models, Pricing, SLAs &amp; Updates Explorer</span>
        </div>
      </a>
      <ul class="nav-pills">
        {nav_items}
      </ul>
      <div class="header-actions">
        <span class="cache-pill" title="Snapshot generated at {esc(gen_at)}">⚡ Snapshot: {esc(gen_date)}</span>
        <button id="theme-toggle-btn" type="button" class="btn" onclick="toggleTheme()" title="Toggle Dark / Light Theme">🌙 Dark</button>
        <button type="button" class="btn" onclick="triggerHarvestRefresh(this)" title="Refresh from live Google Cloud APIs">↻ Refresh</button>
      </div>
    </div>
  </header>

  <main class="container">
    <div class="status-bar">
      <div>
        <div>
          <strong>Snapshot ({esc(gen_at)}):</strong>
          <strong>{counts.get('total_services', 0)}</strong> <a href="{root_prefix}index.html">Google Cloud Services</a> •
          <strong>{counts.get('available_regions', 0)}</strong> <a href="{root_prefix}regions.html">Regions</a> (+<strong>{counts.get('future_regions', 0)}</strong> upcoming) •
          <strong>{counts.get('ai_models', 0)}</strong> <a href="{root_prefix}models.html">AI Models</a> •
          <strong>{counts.get('formal_sla_services', counts.get('total_services', 0))}</strong> <a href="{root_prefix}pricing-sla.html">SLAs &amp; Pricing</a> •
          <strong>{counts.get('release_notes', 0)}</strong> <a href="{root_prefix}whatsnew.html">Release Updates</a>
        </div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
          Unofficial community tool — please refer to the <a href="https://cloud.google.com/docs" target="_blank" rel="noopener">official Google Cloud documentation</a> (<a href="https://cloud.google.com/about/locations" target="_blank" rel="noopener">Locations</a> • <a href="https://cloud.google.com/terms/sla" target="_blank" rel="noopener">SLAs</a> • <a href="https://cloud.google.com/pricing" target="_blank" rel="noopener">Pricing</a>) for the latest authoritative information.
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span id="offline-status-pill" class="badge badge-green">✓ Offline PWA Ready</span>
        <span class="badge badge-gray" title="Press / on your keyboard to jump to search">Press <code>/</code> to search</span>
        <span class="badge badge-blue">24h Cache</span>
      </div>
    </div>
    {body_html}
  </main>

  <footer class="site-footer">
    <div class="footer-inner">
      <div>
        <strong>Unofficial Tool Disclaimer:</strong> This is an unofficial tool and is not affiliated with, sponsored by, or endorsed by Google LLC or Google Cloud. Please refer to the official Google Cloud documentation for the latest information.
        Data is harvested once daily from public Google Cloud Location feeds, Vertex AI Model matrices, SLA &amp; Pricing documentation, Release Notes XML feeds, and Google APIs Discovery REST specifications and served locally via static HTML &amp; offline PWA cache.
      </div>
      <div style="margin-top:6px;">
        Official Google Cloud Documentation:
        <a href="https://cloud.google.com/about/locations" target="_blank" rel="noopener">Google Cloud Locations</a> •
        <a href="https://cloud.google.com/terms/sla" target="_blank" rel="noopener">Service Level Agreements</a> •
        <a href="https://cloud.google.com/pricing" target="_blank" rel="noopener">Cloud Pricing</a> •
        <a href="https://cloud.google.com/release-notes" target="_blank" rel="noopener">Release Notes</a> •
        <a href="https://cloud.google.com/docs" target="_blank" rel="noopener">Google Cloud Docs</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def generate_index_page(catalog: dict[str, Any]) -> None:
    """Generate dist/index.html (Services Explorer)."""
    meta = catalog["meta"]
    counts = meta["counts"]
    services = catalog["services"]
    categories = sorted({s["category"] for s in services if s.get("category")})
    scopes = sorted({s["scope"] for s in services if s.get("scope")})

    cat_opts = "\n".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in categories)
    scope_opts = "\n".join(f'<option value="{esc(sc)}">{esc(sc)}</option>' for sc in scopes)

    rows_html = []
    for s in services:
        slug = s["slug"]
        apis_chips = " ".join(
            f'<span class="code-chip">{esc(a)}</span>' for a in s.get("api_names", [])[:3]
        )
        if len(s.get("api_names", [])) > 3:
            apis_chips += f' <span class="badge badge-gray">+{len(s["api_names"]) - 3}</span>'
        if not apis_chips:
            apis_chips = '<span style="color:#9aa0a6;">—</span>'

        scope_badge_cls = "badge-blue"
        if "Global" in s["scope"]:
            scope_badge_cls = "badge-purple"
        elif "Multi-Region" in s["scope"]:
            scope_badge_cls = "badge-green"

        mr_badges = ""
        if s.get("multi_regions"):
            mr_codes = sorted({m["code"] for m in s["multi_regions"] if m.get("code")})
            mr_badges = " " + " ".join(f'<span class="badge badge-green">{esc(c)}</span>' for c in mr_codes[:3])

        reg_count = s["region_count"]
        cov_pct = s["coverage_pct"]
        reg_display = (
            f'<div class="cov-wrap">'
            f'<strong>{reg_count}</strong>'
            f'<div class="cov-bar"><div class="cov-fill" style="width:{min(100, cov_pct)}%"></div></div>'
            f'<span style="font-size:12px;color:#5f6368;">{cov_pct}%</span>'
            f'</div>'
            if reg_count > 0
            else '<span class="badge badge-purple">Global Endpoint</span>'
        )

        rows_html.append(
            f'<tr data-filter1="{esc(s["category"])}" data-filter2="{esc(s["scope"])}">'
            f'<td data-val="{esc(s["name"])}"><a href="services/{esc(slug)}.html" style="font-weight:600;">{esc(s["name"])}</a></td>'
            f'<td data-val="{esc(s["category"])}"><span class="badge badge-gray">{esc(s["category"])}</span></td>'
            f'<td data-val="{esc(s["scope"])}"><span class="badge {scope_badge_cls}">{esc(s["scope"])}</span>{mr_badges}</td>'
            f'<td>{apis_chips}</td>'
            f'<td data-val="{s.get("total_api_methods", 0)}">'
            f'<a href="services/{esc(slug)}.html#api-methods" class="badge badge-blue">{s.get("total_api_methods", 0)} ops</a>'
            f'</td>'
            f'<td><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["url"])}</a></td>'
            f'<td data-val="{reg_count}">{reg_display}</td>'
            f'</tr>'
        )

    body = f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Google Cloud Services</div>
        <div class="kpi-value">{counts['total_services']}</div>
        <div class="kpi-sub">{counts['regional_services']} Regional • {counts['global_services']} Global</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Google Cloud Regions</div>
        <div class="kpi-value">{counts['available_regions']} <span style="font-size:15px;color:#137333;">(+{counts['future_regions']} Future)</span></div>
        <div class="kpi-sub">{counts['low_co2_regions']} Low CO₂ Regions 🌱</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">AI &amp; Foundation Models</div>
        <div class="kpi-value"><a href="models.html" style="text-decoration:none;color:inherit;">{counts.get('ai_models', 0)}</a></div>
        <div class="kpi-sub"><a href="models.html">{counts.get('ai_model_families', 0)} Families (Gemini, Claude, Llama, Veo...) →</a></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Availability Zones</div>
        <div class="kpi-value">{counts['total_zones']}</div>
        <div class="kpi-sub">{counts['gpu_zones']} GPU Accelerator Zones</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Discovery REST APIs</div>
        <div class="kpi-value">{counts['discovery_apis']}</div>
        <div class="kpi-sub">{counts['total_api_methods']:,} Harvested API Methods</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Global Edge &amp; CDN PoPs</div>
        <div class="kpi-value">{counts['edge_pops']}</div>
        <div class="kpi-sub">{counts['cloud_cdn_pops']} Cloud CDN • {counts['media_cdn_pops']} Media CDN</div>
      </div>
    </div>

    <div class="toolbar">
      <div class="toolbar-group">
        <input id="svc-search" type="search" class="search-input" placeholder="Search Google Cloud service name, API (e.g. alloydb, aiplatform, compute), or category...">
        <select id="svc-cat" class="select-input">
          <option value="">All Categories ({len(categories)})</option>
          {cat_opts}
        </select>
        <select id="svc-scope" class="select-input">
          <option value="">All Scopes</option>
          {scope_opts}
        </select>
      </div>
      <div id="svc-count" class="count-label">Showing {len(services)} of {len(services)}</div>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table id="svc-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Service Name ⇅</th>
              <th data-sort="str">Category ⇅</th>
              <th data-sort="str">Deployment Scope ⇅</th>
              <th>Google Cloud Service API(s)</th>
              <th data-sort="num">API Operations ⇅</th>
              <th>Official Documentation</th>
              <th data-sort="num">No. of Regions ⇅</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows_html)}
          </tbody>
        </table>
      </div>
    </div>

    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        setupTableFilter({{
          searchId: 'svc-search',
          select1Id: 'svc-cat',
          select2Id: 'svc-scope',
          tableId: 'svc-table',
          countId: 'svc-count'
        }});
      }});
    </script>
    """
    (DIST_DIR / "index.html").write_text(
        render_layout("Google Cloud Services Explorer", "services", body, meta),
        encoding="utf-8",
    )


def generate_regions_page(catalog: dict[str, Any]) -> None:
    """Generate dist/regions.html (Regions Explorer)."""
    meta = catalog["meta"]
    regions = catalog["regions"]
    future_regions = catalog["future_regions"]
    total_reg_svcs = max(1, meta["counts"]["regional_services"])
    sub_regions = sorted({r["sub_region"] for r in regions if r.get("sub_region")})
    sub_opts = "\n".join(f'<option value="{esc(sr)}">{esc(sr)}</option>' for sr in sub_regions)

    rows_html = []
    for r in regions:
        rid = r["region_id"]
        co2_badge = '<span class="badge badge-green" title="Low Carbon Region">🌱 Low CO₂</span>' if r["is_low_co2"] else ""
        cov_pct = round((r["service_count"] / total_reg_svcs) * 100, 1)
        gpus = r.get("gpus", [])
        gpu_summary = (
            " ".join(f'<span class="badge badge-purple">{esc(g)}</span>' for g in gpus[:4])
            + (f' <span class="badge badge-gray">+{len(gpus)-4}</span>' if len(gpus) > 4 else "")
            if gpus
            else '<span style="color:#9aa0a6;">Standard CPU</span>'
        )
        mseries = r.get("machine_series", [])
        m_summary = f'{len(mseries)} series ({", ".join(mseries[:5])}{"..." if len(mseries) > 5 else ""})' if mseries else "Standard"
        ai_cnt = r.get("ai_model_count", len(r.get("ai_models", [])))

        rows_html.append(
            f'<tr data-filter1="{esc(r["sub_region"])}" data-flag="{str(r["is_low_co2"]).lower()}">'
            f'<td data-val="{esc(r["region_name"])}">'
            f'<a href="regions/{esc(rid)}.html" style="font-weight:600;">{esc(r["sub_region"])} ({esc(r["region_name"])})</a>'
            f'<div style="font-size:12px;color:#5f6368;">{esc(r["full_location"])}</div>'
            f'</td>'
            f'<td data-val="{esc(rid)}"><a href="regions/{esc(rid)}.html"><span class="code-chip" style="font-weight:700;color:#1a73e8;">{esc(rid)}</span></a></td>'
            f'<td data-val="{esc(r["sub_region"])}"><span class="badge badge-gray">{esc(r["sub_region"])}</span> {co2_badge}</td>'
            f'<td data-val="{r["service_count"]}">'
            f'<div class="cov-wrap"><strong>{r["service_count"]}</strong>'
            f'<div class="cov-bar"><div class="cov-fill" style="width:{min(100, cov_pct)}%"></div></div>'
            f'<span style="font-size:12px;color:#5f6368;">{cov_pct}%</span></div>'
            f'</td>'
            f'<td data-val="{ai_cnt}">'
            f'<a href="regions/{esc(rid)}.html#region-ai-models" class="badge {"badge-purple" if ai_cnt > 0 else "badge-gray"}">{ai_cnt} models</a>'
            f'</td>'
            f'<td data-val="{r["zone_count"]}"><strong>{r["zone_count"]}</strong> <span style="color:#5f6368;font-size:12px;">({", ".join(z.split("-")[-1] for z in r["zones"])})</span></td>'
            f'<td data-val="{len(mseries)}"><div style="font-size:12.5px;">{esc(m_summary)}</div><div>{gpu_summary}</div></td>'
            f'<td data-val="{esc(r["date_launched"])}">{esc(r["date_launched"])}</td>'
            f'</tr>'
        )

    future_rows = "\n".join(
        f'<tr>'
        f'<td><strong>{esc(fr["region_name"])}</strong></td>'
        f'<td><span class="badge badge-yellow">Announced / Future</span></td>'
        f'<td>{esc(fr["sub_region"])}</td>'
        f'<td>{esc(fr["lat"])}, {esc(fr["lng"])}</td>'
        f'<td>At launch: Compute Engine, GKE, Cloud Storage, Persistent Disk, Cloud SQL, VPC, Cloud VPN, KMS, Secret Manager</td>'
        f'</tr>'
        for fr in future_regions
    )

    body = f"""
    <div class="toolbar">
      <div class="toolbar-group">
        <input id="reg-search" type="search" class="search-input" placeholder="Search region code (e.g. us-central1, asia-south1), city, CPU (Axion, Turin), or GPU (A3, H100, L4)...">
        <select id="reg-sub" class="select-input">
          <option value="">All Geographies ({len(sub_regions)})</option>
          {sub_opts}
        </select>
        <label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;cursor:pointer;">
          <input id="reg-co2" type="checkbox"> 🌱 Low CO₂ Regions Only
        </label>
      </div>
      <div id="reg-count" class="count-label">Showing {len(regions)} of {len(regions)}</div>
    </div>

    <div class="table-card" style="margin-bottom:24px;">
      <div class="table-scroll">
        <table id="reg-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Region Name &amp; City ⇅</th>
              <th data-sort="str">Region Code ⇅</th>
              <th data-sort="str">Geography &amp; Sustainability ⇅</th>
              <th data-sort="num">Unique Services ⇅</th>
              <th data-sort="num">AI Models ⇅</th>
              <th data-sort="num">Availability Zones ⇅</th>
              <th data-sort="num">Machine Series &amp; GPU Accelerators ⇅</th>
              <th data-sort="str">Launch Year ⇅</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows_html)}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🚀 Announced Upcoming / Future Google Cloud Regions ({len(future_regions)})</h2>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Announced Region</th>
              <th>Status</th>
              <th>Geography</th>
              <th>Coordinates</th>
              <th>Minimum Day-1 Launch Services Commitment</th>
            </tr>
          </thead>
          <tbody>
            {future_rows}
          </tbody>
        </table>
      </div>
    </div>

    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        setupTableFilter({{
          searchId: 'reg-search',
          select1Id: 'reg-sub',
          checkboxId: 'reg-co2',
          tableId: 'reg-table',
          countId: 'reg-count'
        }});
      }});
    </script>
    """
    (DIST_DIR / "regions.html").write_text(
        render_layout("Google Cloud Regions Explorer", "regions", body, meta),
        encoding="utf-8",
    )


def generate_models_page(catalog: dict[str, Any]) -> None:
    """Generate dist/models.html (AI & Foundation Models Regional Availability Explorer)."""
    meta = catalog["meta"]
    models = catalog.get("models", [])
    regions = catalog.get("regions", [])
    regions_by_id = {r["region_id"]: r for r in regions}
    total_active_regions = max(1, len(regions))

    families = sorted({m["family"] for m in models if m.get("family")})
    modalities = sorted({m["modality"] for m in models if m.get("modality")})
    all_model_rids = sorted({rid for m in models for rid in m.get("regions", [])})

    family_opts = "\n".join(f'<option value="{esc(f)}">{esc(f)}</option>' for f in families)
    modality_opts = "\n".join(f'<option value="{esc(mod)}">{esc(mod)}</option>' for mod in modalities)

    loc_opts_list = [
        '<option value="GLOBAL">🌐 Global Endpoint (global)</option>',
        '<option value="MR_US">🇺🇸 US Multi-Region (us)</option>',
        '<option value="MR_EU">🇪🇺 EU Multi-Region (eu)</option>',
    ]
    for rid in all_model_rids:
        rname = regions_by_id.get(rid, {}).get("region_name", rid)
        sub = regions_by_id.get(rid, {}).get("sub_region", "")
        loc_opts_list.append(f'<option value="{esc(rid)}">{esc(rid)} — {esc(rname)} ({esc(sub)})</option>')
    loc_opts = "\n".join(loc_opts_list)

    global_models_count = sum(1 for m in models if m.get("global_endpoint"))
    mr_models_count = sum(1 for m in models if m.get("multi_regions"))

    model_rows = []
    for m in models:
        mid = m["model_id"]
        mname = m["model_name"]
        fam = m["family"]
        mod = m["modality"]
        m_regions = m.get("regions", [])
        reg_count = len(m_regions)
        cov_pct = round((reg_count / total_active_regions) * 100, 1)

        # Build filter3 pipe-delimited tokens for endpoints + regions
        filter3_tokens = list(m_regions)
        if m.get("global_endpoint"):
            filter3_tokens.append("GLOBAL")
        for mr in m.get("multi_regions", []):
            filter3_tokens.append(f"MR_{mr.upper()}")
        filter3_str = "|".join(filter3_tokens)

        ep_badges = []
        if m.get("global_endpoint"):
            ep_badges.append('<span class="badge badge-purple" title="Available on Vertex AI global endpoint">🌐 global</span>')
        for mr in m.get("multi_regions", []):
            ep_badges.append(f'<span class="badge badge-green" title="Multi-region endpoint">{esc(mr)}</span>')
        if not ep_badges:
            ep_badges.append('<span class="badge badge-gray">Regional Only</span>')

        primary_chips = " ".join(
            f'<a href="regions/{esc(rid)}.html#region-ai-models" data-rid="{esc(rid)}" class="code-chip" title="{esc(regions_by_id.get(rid, {}).get("region_name", rid))}">{esc(rid)}</a>'
            for rid in m_regions[:8]
        )
        if len(m_regions) > 8:
            extra_chips = " ".join(
                f'<a href="regions/{esc(rid)}.html#region-ai-models" data-rid="{esc(rid)}" class="code-chip" title="{esc(regions_by_id.get(rid, {}).get("region_name", rid))}">{esc(rid)}</a>'
                for rid in m_regions[8:]
            )
            extra_rids = ", ".join(m_regions[8:])
            reg_chips = (
                f'{primary_chips} '
                f'<span class="extra-rids" style="display:none;">{extra_chips}</span> '
                f'<span class="badge badge-blue more-rids-toggle" style="cursor:pointer;" '
                f'onclick="this.previousElementSibling.style.display=\'inline\';this.style.display=\'none\';" '
                f'title="Click to expand: {esc(extra_rids)}">+{len(m_regions) - 8} more</span>'
            )
        else:
            reg_chips = primary_chips
        if not reg_chips:
            reg_chips = '<span style="color:var(--text-muted);font-size:12px;">Global / Multi-Region Endpoint Only</span>'

        mod_badge_cls = "badge-blue"
        if "Video" in mod or "Image" in mod:
            mod_badge_cls = "badge-purple"
        elif "Audio" in mod or "Live" in mod:
            mod_badge_cls = "badge-green"
        elif "Embedding" in mod:
            mod_badge_cls = "badge-yellow"

        model_rows.append(
            f'<tr data-filter1="{esc(fam)}" data-filter2="{esc(mod)}" data-filter3="{esc(filter3_str)}" data-flag="{str(bool(m.get("global_endpoint"))).lower()}">'
            f'<td data-val="{esc(mname)}">'
            f'<strong>{esc(mname)}</strong>'
            f'<div style="font-size:11.5px;"><a href="{esc(m.get("docs_url", ""))}" target="_blank" rel="noopener">Official Model Docs ↗</a></div>'
            f'</td>'
            f'<td data-val="{esc(mid)}"><span class="code-chip" style="font-weight:700;color:var(--gcp-blue);">{esc(mid)}</span></td>'
            f'<td data-val="{esc(fam)}"><span class="badge badge-gray">{esc(fam)}</span></td>'
            f'<td data-val="{esc(mod)}"><span class="badge {mod_badge_cls}">{esc(mod)}</span></td>'
            f'<td>{" ".join(ep_badges)}</td>'
            f'<td data-val="{reg_count}">'
            f'<div class="cov-wrap"><strong>{reg_count}</strong>'
            f'<div class="cov-bar"><div class="cov-fill" style="width:{min(100, cov_pct)}%"></div></div>'
            f'<span style="font-size:12px;color:var(--text-muted);">{cov_pct}%</span></div>'
            f'</td>'
            f'<td><div style="max-width:460px;">{reg_chips}</div></td>'
            f'</tr>'
        )

    # Regional AI summary table
    reg_ai_rows = []
    for r in sorted(regions, key=lambda x: (-x.get("ai_model_count", 0), x["region_id"])):
        rid = r["region_id"]
        ai_list = r.get("ai_models", [])
        if not ai_list:
            continue
        fams_in_reg = sorted({am["family"] for am in ai_list})
        fam_chips = " ".join(f'<span class="badge badge-gray">{esc(f)}</span>' for f in fams_in_reg[:5])
        if len(fams_in_reg) > 5:
            fam_chips += f' <span class="badge badge-blue">+{len(fams_in_reg) - 5} families</span>'
        sample_models = " ".join(f'<span class="code-chip">{esc(am["model_id"])}</span>' for am in ai_list[:5])
        if len(ai_list) > 5:
            sample_models += f' <span class="badge badge-purple">+{len(ai_list) - 5} more</span>'
        reg_ai_rows.append(
            f'<tr>'
            f'<td data-val="{esc(rid)}"><a href="regions/{esc(rid)}.html#region-ai-models"><span class="code-chip" style="font-weight:700;color:var(--gcp-blue);">{esc(rid)}</span></a></td>'
            f'<td data-val="{esc(r["region_name"])}"><a href="regions/{esc(rid)}.html#region-ai-models" style="font-weight:600;">{esc(r["sub_region"])} ({esc(r["region_name"])})</a></td>'
            f'<td data-val="{len(ai_list)}"><strong>{len(ai_list)}</strong> models</td>'
            f'<td>{fam_chips}</td>'
            f'<td>{sample_models}</td>'
            f'</tr>'
        )

    body = f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Total AI &amp; Foundation Models</div>
        <div class="kpi-value">{len(models)}</div>
        <div class="kpi-sub">First-Party &amp; Partner Models on Vertex AI</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Model Families &amp; Providers</div>
        <div class="kpi-value">{len(families)}</div>
        <div class="kpi-sub">Gemini, Anthropic Claude, Llama, Mistral, Veo...</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Global Endpoint Models</div>
        <div class="kpi-value">{global_models_count}</div>
        <div class="kpi-sub">Available via <code>locations/global</code></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Multi-Region (US / EU) Models</div>
        <div class="kpi-value">{mr_models_count}</div>
        <div class="kpi-sub">Available via <code>us</code> or <code>eu</code> endpoints</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">AI-Enabled Google Cloud Regions</div>
        <div class="kpi-value">{len(all_model_rids)}</div>
        <div class="kpi-sub">Regional endpoints with model availability</div>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🤖 Google Cloud AI &amp; Foundation Models — Regional Availability Explorer</h2>
      <p style="margin:0 0 14px 0;color:var(--text-muted);font-size:13px;">
        Check which Generative AI, Foundation, Multimodal, Video, Speech, Embedding, and Partner models are available in each Google Cloud region, multi-region (<code>us</code>, <code>eu</code>), or <code>global</code> endpoint.
        <em>(Unofficial tool — refer to <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations" target="_blank" rel="noopener">Official Vertex AI Locations Documentation ↗</a> for the latest information.)</em>
      </p>

      <div class="toolbar">
        <div class="toolbar-group">
          <input id="mod-search" type="search" class="search-input" placeholder="Search model name or ID (e.g. gemini-2.5-pro, claude-sonnet-4-5, veo-3.0, llama-4, deepseek, chirp)...">
          <select id="mod-fam" class="select-input">
            <option value="">All Model Families ({len(families)})</option>
            {family_opts}
          </select>
          <select id="mod-type" class="select-input">
            <option value="">All Modalities ({len(modalities)})</option>
            {modality_opts}
          </select>
          <select id="mod-region" class="select-input">
            <option value="">Filter by Region / Endpoint (All)</option>
            {loc_opts}
          </select>
          <label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;cursor:pointer;">
            <input id="mod-global" type="checkbox"> 🌐 Global Endpoint Only
          </label>
          <button id="mod-reset" type="button" class="btn">Reset</button>
        </div>
        <div id="mod-count" class="count-label">Showing {len(models)} of {len(models)}</div>
      </div>

      <div class="table-scroll">
        <table id="mod-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Model Name ⇅</th>
              <th data-sort="str">Model ID ⇅</th>
              <th data-sort="str">Model Family / Provider ⇅</th>
              <th data-sort="str">Modality ⇅</th>
              <th>Global / Multi-Region</th>
              <th data-sort="num">Regions Count ⇅</th>
              <th>Available Google Cloud Regions</th>
            </tr>
          </thead>
          <tbody>
            {"".join(model_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🌍 AI Model Availability Breakdown by Google Cloud Region ({len(reg_ai_rows)} Regions)</h2>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Region Code</th>
              <th>Region Name</th>
              <th>Available AI Models</th>
              <th>Supported Model Families</th>
              <th>Sample Model IDs</th>
            </tr>
          </thead>
          <tbody>
            {"".join(reg_ai_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        setupTableFilter({{
          searchId: 'mod-search',
          select1Id: 'mod-fam',
          select2Id: 'mod-type',
          select3Id: 'mod-region',
          checkboxId: 'mod-global',
          resetId: 'mod-reset',
          highlightRegionAttr: true,
          tableId: 'mod-table',
          countId: 'mod-count'
        }});
      }});
    </script>
    """
    (DIST_DIR / "models.html").write_text(
        render_layout("AI & Foundation Models Availability", "models", body, meta),
        encoding="utf-8",
    )


def generate_service_detail_pages(catalog: dict[str, Any]) -> None:
    """Generate dist/services/<slug>.html for every Google Cloud service."""
    svc_dir = DIST_DIR / "services"
    svc_dir.mkdir(parents=True, exist_ok=True)

    meta = catalog["meta"]
    regions_by_id = {r["region_id"]: r for r in catalog["regions"]}
    all_region_ids = [r["region_id"] for r in catalog["regions"]]

    for s in catalog["services"]:
        slug = s["slug"]
        avail_set = set(s["regions"])
        missing_rids = [rid for rid in all_region_ids if rid not in avail_set]

        reg_rows = []
        for rid in s["regions"]:
            r = regions_by_id.get(rid, {})
            co2 = '<span class="badge badge-green">🌱 Low CO₂</span>' if r.get("is_low_co2") else ""
            endpoint_ex = (
                f"{rid}-{s['apis'][0]['service_endpoint']}"
                if s.get("apis")
                else f"locations/{rid}"
            )
            reg_rows.append(
                f'<tr>'
                f'<td><a href="../regions/{esc(rid)}.html"><span class="code-chip" style="font-weight:700;color:#1a73e8;">{esc(rid)}</span></a></td>'
                f'<td><a href="../regions/{esc(rid)}.html" style="font-weight:600;">{esc(r.get("sub_region", ""))} ({esc(r.get("region_name", rid))})</a></td>'
                f'<td>{esc(r.get("full_location", ""))} {co2}</td>'
                f'<td>{r.get("zone_count", 3)} zones ({", ".join(r.get("zones", []))})</td>'
                f'<td><span class="code-chip">{esc(endpoint_ex)}</span></td>'
                f'<td>{esc(r.get("date_launched", ""))}</td>'
                f'</tr>'
            )

        missing_chips = " ".join(
            f'<a href="../regions/{esc(rid)}.html" class="code-chip" style="color:#c5221f;background:#fce8e6;border-color:#f5c2c0;">{esc(rid)} ({esc(regions_by_id.get(rid, {}).get("region_name", ""))})</a>'
            for rid in missing_rids
        ) or '<span class="badge badge-green">Available in 100% of active Google Cloud regions!</span>'

        api_cards = []
        for api in s.get("apis", []):
            vers = ", ".join(api.get("all_versions", []))
            res_chips = " ".join(f'<span class="code-chip">{esc(r)}</span>' for r in api.get("resources", [])[:15])
            api_cards.append(
                f'<div style="padding:14px;border:1px solid var(--border-subtle);border-radius:8px;margin-bottom:10px;background:var(--bg-subtle);">'
                f'<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">'
                f'<div><strong>{esc(api["title"])}</strong> <span class="code-chip" style="color:var(--gcp-blue);font-weight:700;">{esc(api["service_endpoint"])}</span></div>'
                f'<div><span class="badge badge-blue">Preferred: {esc(api["preferred_version"])}</span> '
                f'<span class="badge badge-gray">Versions: {esc(vers)}</span> '
                f'<span class="badge badge-green">{api["method_count"]} REST Methods ({api["regional_method_count"]} regional)</span></div>'
                f'</div>'
                f'<div style="margin-top:8px;font-size:12.5px;color:var(--text-muted);">Top-Level Resources: {res_chips or "Root"}</div>'
                f'</div>'
            )

        method_rows = []
        for m in s.get("methods", []):
            verb = m.get("httpMethod", "GET")
            reg_badge = '<span class="badge badge-green">Regional</span>' if m.get("isRegional") else '<span class="badge badge-gray">Global/Project</span>'
            method_rows.append(
                f'<tr>'
                f'<td><span class="verb verb-{esc(verb)}">{esc(verb)}</span></td>'
                f'<td><span class="code-chip" style="font-weight:600;">{esc(m["id"])}</span></td>'
                f'<td><span class="code-chip">{esc(m["path"])}</span></td>'
                f'<td>{reg_badge}</td>'
                f'<td style="font-size:12.5px;color:var(--text-muted);">{esc(m.get("description", ""))}</td>'
                f'</tr>'
            )

        sla = s.get("sla", {})
        prc = s.get("pricing", {})
        sla_tiers_html = "".join(
            f'<tr><td><strong>{esc(t["tier_name"])}</strong></td>'
            f'<td><span class="badge badge-green">{esc(t["uptime_display"])}</span></td>'
            f'<td><code>{esc(t["max_monthly_downtime"])}</code> • <code>{esc(t["max_annual_downtime"])}</code></td>'
            f'<td style="color:var(--text-muted);font-size:12.5px;">{esc(t["topology"])}</td></tr>'
            for t in sla.get("tiers", [])
        )
        sla_reqs_html = "".join(f"<li>{esc(req)}</li>" for req in sla.get("ha_requirements", []))
        cost_drivers_html = "".join(f"<li>{esc(cd)}</li>" for cd in prc.get("cost_drivers", []))

        body = f"""
        <div class="section-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
            <div>
              <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">
                <a href="../index.html">← Back to All Google Cloud Services</a> • Category: <strong>{esc(s["category"])}</strong>
              </div>
              <h1 style="margin:0 0 8px 0;font-size:24px;color:var(--gcp-blue);">{esc(s["name"])}</h1>
              <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
                <span class="badge badge-blue">{esc(s["scope"])}</span>
                <span class="badge badge-green">{s["region_count"]} / {len(all_region_ids)} Regions ({s["coverage_pct"]}%)</span>
                <span class="badge badge-yellow">SLA: {esc(sla.get("headline_display", "N/A"))}</span>
                <span class="badge badge-purple">{s.get("total_api_methods", 0)} API Operations</span>
                <a href="{esc(s["url"])}" target="_blank" rel="noopener" class="btn">Official Documentation ↗</a>
                <a href="{esc(sla.get("sla_url", "https://cloud.google.com/terms/sla"))}" target="_blank" rel="noopener" class="btn">Official SLA ↗</a>
                <a href="{esc(prc.get("pricing_url", "https://cloud.google.com/pricing"))}" target="_blank" rel="noopener" class="btn">Official Pricing ↗</a>
              </div>
            </div>
          </div>
        </div>

        <div class="studio-grid">
          <div class="section-card" style="margin-bottom:0;">
            <h2 class="section-title">🛡️ Service Level Agreement (SLA) &amp; HA Architecture</h2>
            {f'''
            <div class="table-scroll" style="margin-bottom:10px;">
              <table class="data-table">
                <thead><tr><th>Deployment Tier</th><th>Target SLA</th><th>Max Downtime</th><th>Topology</th></tr></thead>
                <tbody>{sla_tiers_html}</tbody>
              </table>
            </div>
            ''' if sla_tiers_html else '<p style="color:var(--text-muted);">No formal uptime SLA published (developer/management tooling).</p>'}
            <div style="font-size:12.5px;">
              <strong>HA Qualification Prerequisites:</strong>
              <ul style="margin:6px 0 0 18px;padding:0;">{sla_reqs_html}</ul>
            </div>
          </div>

          <div class="section-card" style="margin-bottom:0;">
            <h2 class="section-title">💰 FinOps Pricing Model, Free Tier &amp; CUDs</h2>
            <div style="display:grid;gap:8px;font-size:13px;">
              <div><strong>Billing Model:</strong> {esc(prc.get("billing_model", ""))}</div>
              <div><strong>Metered Units:</strong> <code>{esc(prc.get("primary_units", ""))}</code></div>
              <div><strong>Free Tier:</strong> <span class="badge {'badge-green' if prc.get('has_free_tier') else 'badge-gray'}">{'Eligible' if prc.get('has_free_tier') else 'Standard Metering'}</span> {esc(prc.get("free_tier_note", ""))}</div>
              <div><strong>Committed Use Discounts:</strong> {esc(prc.get("cud_support", ""))}</div>
              <div><strong>Key Cost Watchouts:</strong><ul style="margin:4px 0 0 18px;padding:0;">{cost_drivers_html}</ul></div>
            </div>
          </div>
        </div>

        <div class="section-card">
          <h2 class="section-title">🌍 Regional Availability for "{esc(s["name"])}" ({s["region_count"]} Regions)</h2>
          <div class="toolbar" style="margin-bottom:12px;">
            <input id="svc-reg-search" type="search" class="search-input" placeholder="Filter regions for {esc(s["name"])}...">
            <div id="svc-reg-count" class="count-label">Showing {len(reg_rows)} of {len(reg_rows)}</div>
          </div>
          <div class="table-scroll">
            <table id="svc-reg-table" class="data-table">
              <thead>
                <tr>
                  <th data-sort="str">Region Code ⇅</th>
                  <th data-sort="str">Region Name ⇅</th>
                  <th data-sort="str">Geographic Location ⇅</th>
                  <th>Availability Zones</th>
                  <th>Regional API Target / Location</th>
                  <th data-sort="str">Region Launch Year ⇅</th>
                </tr>
              </thead>
              <tbody>
                {"".join(reg_rows) if reg_rows else '<tr><td colspan="6">This is a Global / Multi-Region Google Cloud Service served across Google Cloud global edge & control plane endpoints.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>

        <div class="section-card">
          <h2 class="section-title">⚠️ Regions Where "{esc(s["name"])}" Is Not Listed ({len(missing_rids)} Regions)</h2>
          <div>{missing_chips}</div>
        </div>

        <div class="section-card" id="api-methods">
          <h2 class="section-title">⚙️ Google Cloud Discovery APIs &amp; Capabilities ({s.get("total_api_methods", 0)} Operations)</h2>
          {"".join(api_cards) if api_cards else '<p style="color:var(--text-muted);">Managed via integrated Google Cloud Console / Parent Service APIs.</p>'}
          {f'''
          <div class="toolbar" style="margin-top:14px;margin-bottom:12px;">
            <input id="api-m-search" type="search" class="search-input" placeholder="Search REST API method ID, HTTP verb (POST, GET, DELETE), path, or description...">
            <div id="api-m-count" class="count-label">Showing {len(method_rows)} of {len(method_rows)}</div>
          </div>
          <div class="table-scroll">
            <table id="api-m-table" class="data-table">
              <thead>
                <tr>
                  <th data-sort="str">HTTP ⇅</th>
                  <th data-sort="str">Method ID ⇅</th>
                  <th data-sort="str">REST Endpoint Path ⇅</th>
                  <th data-sort="str">Scope ⇅</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {"".join(method_rows)}
              </tbody>
            </table>
          </div>
          ''' if method_rows else ''}
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', () => {{
            setupTableFilter({{ searchId: 'svc-reg-search', tableId: 'svc-reg-table', countId: 'svc-reg-count' }});
            setupTableFilter({{ searchId: 'api-m-search', tableId: 'api-m-table', countId: 'api-m-count' }});
          }});
        </script>
        """
        (svc_dir / f"{slug}.html").write_text(
            render_layout(f"{s['name']} - Google Cloud Regional Availability", "services", body, meta, root_prefix="../"),
            encoding="utf-8",
        )


def generate_region_detail_pages(catalog: dict[str, Any]) -> None:
    """Generate dist/regions/<region_id>.html for every Google Cloud region."""
    reg_dir = DIST_DIR / "regions"
    reg_dir.mkdir(parents=True, exist_ok=True)

    meta = catalog["meta"]
    services_by_name = {s["name"]: s for s in catalog["services"]}
    regional_services_all = [s["name"] for s in catalog["services"] if s["region_count"] > 0]
    models_by_id = {m["model_id"]: m for m in catalog.get("models", [])}

    for r in catalog["regions"]:
        rid = r["region_id"]
        avail_set = set(r["services"])
        missing_svcs = [sname for sname in regional_services_all if sname not in avail_set]

        zone_rows = []
        for z in r.get("zone_details", []):
            m_chips = " ".join(f'<span class="code-chip">{esc(m)}</span>' for m in z.get("machine_types", []))
            c_chips = " ".join(f'<span class="badge badge-gray">{esc(c)}</span>' for c in z.get("cpus", []))
            g_chips = " ".join(f'<span class="badge badge-purple">{esc(g)}</span>' for g in z.get("gpus", [])) or '<span style="color:#9aa0a6;">—</span>'
            o_chips = " ".join(f'<span class="badge badge-blue">{esc(o)}</span>' for o in z.get("options", [])) or '<span style="color:#9aa0a6;">Standard</span>'
            zone_rows.append(
                f'<tr>'
                f'<td><span class="code-chip" style="font-weight:700;color:var(--gcp-blue);">{esc(z["zone"])}</span></td>'
                f'<td>{esc(z.get("location", r["full_location"]))}</td>'
                f'<td>{m_chips}</td>'
                f'<td>{c_chips}</td>'
                f'<td>{g_chips}</td>'
                f'<td>{o_chips}</td>'
                f'</tr>'
            )

        svc_rows = []
        for sname in r["services"]:
            s = services_by_name.get(sname, {})
            slug = s.get("slug", "")
            cat = s.get("category", "Cloud")
            apis_chips = " ".join(f'<span class="code-chip">{esc(a)}</span>' for a in s.get("api_names", [])[:2])
            svc_rows.append(
                f'<tr data-filter1="{esc(cat)}">'
                f'<td data-val="{esc(sname)}"><a href="../services/{esc(slug)}.html" style="font-weight:600;">{esc(sname)}</a></td>'
                f'<td data-val="{esc(cat)}"><span class="badge badge-gray">{esc(cat)}</span></td>'
                f'<td>{apis_chips or "—"}</td>'
                f'<td data-val="{s.get("total_api_methods", 0)}"><a href="../services/{esc(slug)}.html#api-methods" class="badge badge-blue">{s.get("total_api_methods", 0)} ops</a></td>'
                f'<td><a href="{esc(s.get("url", ""))}" target="_blank" rel="noopener">{esc(s.get("url", ""))}</a></td>'
                f'</tr>'
            )

        reg_ai_models = r.get("ai_models", [])
        ai_fams_in_reg = sorted({am["family"] for am in reg_ai_models if am.get("family")})
        ai_fam_opts = "\n".join(f'<option value="{esc(f)}">{esc(f)}</option>' for f in ai_fams_in_reg)
        ai_rows = []
        for am in reg_ai_models:
            full_m = models_by_id.get(am["model_id"], am)
            ep_tags = []
            if full_m.get("global_endpoint"):
                ep_tags.append('<span class="badge badge-purple">🌐 global</span>')
            for mr in full_m.get("multi_regions", []):
                ep_tags.append(f'<span class="badge badge-green">{esc(mr)}</span>')
            ep_tags.append(f'<span class="badge badge-blue">{esc(rid)}</span>')
            ai_rows.append(
                f'<tr data-filter1="{esc(am.get("family", ""))}">'
                f'<td data-val="{esc(am.get("model_name", ""))}"><strong>{esc(am.get("model_name", ""))}</strong></td>'
                f'<td data-val="{esc(am.get("model_id", ""))}"><span class="code-chip" style="font-weight:700;color:var(--gcp-blue);">{esc(am.get("model_id", ""))}</span></td>'
                f'<td data-val="{esc(am.get("family", ""))}"><span class="badge badge-gray">{esc(am.get("family", ""))}</span></td>'
                f'<td data-val="{esc(am.get("modality", ""))}"><span class="badge badge-blue">{esc(am.get("modality", ""))}</span></td>'
                f'<td>{" ".join(ep_tags)}</td>'
                f'</tr>'
            )

        missing_chips = " ".join(
            f'<a href="../services/{esc(services_by_name[sn]["slug"])}.html" class="code-chip" style="color:#c5221f;background:#fce8e6;border-color:#f5c2c0;">{esc(sn)}</a>'
            for sn in missing_svcs
            if sn in services_by_name
        ) or '<span class="badge badge-green">All regional services available!</span>'

        cats_in_reg = sorted({services_by_name.get(sn, {}).get("category", "Cloud") for sn in r["services"]})
        cat_opts = "\n".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in cats_in_reg)
        co2_badge = '<span class="badge badge-green">🌱 Low CO₂ Region</span>' if r["is_low_co2"] else ""
        r_pricing = r.get("pricing", {})
        c_idx = r_pricing.get("relative_compute_index", 1.0)
        s_idx = r_pricing.get("relative_storage_index", 1.0)
        p_tier = r_pricing.get("tier", "Tier 1 — Baseline Cost")
        cost_badge_cls = "badge-green" if c_idx <= 1.05 else ("badge-blue" if c_idx <= 1.15 else "badge-yellow")
        cost_badge = f'<a href="../pricing-sla.html#regional-cost" class="badge {cost_badge_cls}">💰 {c_idx:.2f}x Compute ({esc(r_pricing.get("delta_vs_baseline", "Baseline"))})</a>'

        body = f"""
        <div class="section-card">
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">
            <a href="../regions.html">← Back to All Google Cloud Regions</a> • Geography: <strong>{esc(r["sub_region"])}</strong>
          </div>
          <h1 style="margin:0 0 8px 0;font-size:24px;color:var(--gcp-blue);">
            {esc(r["sub_region"])} — {esc(r["region_name"])} (<code>{esc(rid)}</code>)
          </h1>
          <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
            <span class="badge badge-blue">{r["service_count"]} Regional Services Available</span>
            <a href="#region-ai-models" class="badge badge-purple">{len(reg_ai_models)} AI &amp; Foundation Models</a>
            <span class="badge badge-gray">{r["zone_count"]} Availability Zones ({", ".join(r["zones"])})</span>
            <span class="badge badge-blue">{len(r.get("machine_series", []))} Compute Machine Series</span>
            <span class="badge badge-gray">Launched: {esc(r["date_launched"])}</span>
            {cost_badge}
            {co2_badge}
          </div>
          {f'<div style="margin-top:12px;padding:10px 14px;background:var(--bg-subtle);border:1px solid var(--border-subtle);border-radius:8px;font-size:12.5px;color:var(--text-muted);"><strong>FinOps Regional Cost Profile ({esc(p_tier)}):</strong> Relative Compute Multiplier <code>{c_idx:.2f}x</code> • Relative Storage Multiplier <code>{s_idx:.2f}x</code> vs. <code>us-central1 (1.00x)</code> • Inter-Region Egress Band: <code>{esc(r_pricing.get("inter_region_egress_band", "Standard"))}</code> • CUD 1Y/3Y Savings: up to <code>{r_pricing.get("cud_1yr_discount_pct", 37)}%</code> / <code>{r_pricing.get("cud_3yr_discount_pct", 55)}%</code>.</div>' if r_pricing else ''}
        </div>

        <div class="section-card">
          <h2 class="section-title">🖥️ Zone Hardware, Machine Series, CPUs &amp; GPU Accelerators in <code>{esc(rid)}</code></h2>
          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Zone ID</th>
                  <th>Location</th>
                  <th>Available Compute Machine Series</th>
                  <th>CPU Microarchitectures</th>
                  <th>GPU / AI Accelerators</th>
                  <th>Confidential Computing &amp; Features</th>
                </tr>
              </thead>
              <tbody>
                {"".join(zone_rows)}
              </tbody>
            </table>
          </div>
        </div>

        <div class="section-card" id="region-ai-models">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
            <h2 class="section-title" style="margin:0;">🤖 Available AI &amp; Foundation Models in <code>{esc(rid)}</code> ({len(reg_ai_models)} Models)</h2>
            <a href="../models.html" class="btn">Explore All Google Cloud AI Models →</a>
          </div>
          {f'''
          <div class="toolbar" style="margin-bottom:12px;">
            <div class="toolbar-group">
              <input id="reg-ai-search" type="search" class="search-input" placeholder="Search AI models in {esc(rid)} (e.g. gemini, claude, llama, veo, embeddings)...">
              <select id="reg-ai-fam" class="select-input">
                <option value="">All Model Families ({len(ai_fams_in_reg)})</option>
                {ai_fam_opts}
              </select>
            </div>
            <div id="reg-ai-count" class="count-label">Showing {len(ai_rows)} of {len(ai_rows)}</div>
          </div>
          <div class="table-scroll">
            <table id="reg-ai-table" class="data-table">
              <thead>
                <tr>
                  <th data-sort="str">Model Name ⇅</th>
                  <th data-sort="str">Model ID ⇅</th>
                  <th data-sort="str">Model Family / Provider ⇅</th>
                  <th data-sort="str">Modality ⇅</th>
                  <th>Supported Endpoints</th>
                </tr>
              </thead>
              <tbody>
                {"".join(ai_rows)}
              </tbody>
            </table>
          </div>
          ''' if ai_rows else f'<p style="color:var(--text-muted);margin:0;">No region-specific Vertex AI generative model endpoints listed for <code>{esc(rid)}</code>. You can still invoke models via the <a href="../models.html">Vertex AI Global Endpoint (<code>global</code>) or Multi-Region Endpoints (<code>us</code> / <code>eu</code>)</a>.</p>'}
        </div>

        <div class="section-card">
          <h2 class="section-title">✅ Available Google Cloud Services in <code>{esc(rid)}</code> ({r["service_count"]} Services)</h2>
          <div class="toolbar" style="margin-bottom:12px;">
            <div class="toolbar-group">
              <input id="reg-svc-search" type="search" class="search-input" placeholder="Search services available in {esc(rid)}...">
              <select id="reg-svc-cat" class="select-input">
                <option value="">All Categories ({len(cats_in_reg)})</option>
                {cat_opts}
              </select>
            </div>
            <div id="reg-svc-count" class="count-label">Showing {len(svc_rows)} of {len(svc_rows)}</div>
          </div>
          <div class="table-scroll">
            <table id="reg-svc-table" class="data-table">
              <thead>
                <tr>
                  <th data-sort="str">Service Name ⇅</th>
                  <th data-sort="str">Category ⇅</th>
                  <th>Google Cloud Service API(s)</th>
                  <th data-sort="num">API Operations ⇅</th>
                  <th>Official Documentation</th>
                </tr>
              </thead>
              <tbody>
                {"".join(svc_rows)}
              </tbody>
            </table>
          </div>
        </div>

        <div class="section-card">
          <h2 class="section-title">⚠️ Regional Services Not Currently Available in <code>{esc(rid)}</code> ({len(missing_svcs)} Services)</h2>
          <p style="margin:0 0 10px 0;font-size:13px;color:var(--text-muted);">Use this gap list when planning multi-region failover or workload placement in <code>{esc(rid)}</code>:</p>
          <div>{missing_chips}</div>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', () => {{
            setupTableFilter({{
              searchId: 'reg-svc-search',
              select1Id: 'reg-svc-cat',
              tableId: 'reg-svc-table',
              countId: 'reg-svc-count'
            }});
            setupTableFilter({{
              searchId: 'reg-ai-search',
              select1Id: 'reg-ai-fam',
              tableId: 'reg-ai-table',
              countId: 'reg-ai-count'
            }});
          }});
        </script>
        """
        (reg_dir / f"{rid}.html").write_text(
            render_layout(f"{rid} ({r['region_name']}) - Google Cloud Region Services & AI Models", "regions", body, meta, root_prefix="../"),
            encoding="utf-8",
        )


def generate_capabilities_page(catalog: dict[str, Any]) -> None:
    """Generate dist/capabilities.html (Multi-Region Matrix Comparison + API Capabilities Explorer)."""
    meta = catalog["meta"]
    regions = catalog["regions"]
    services = [s for s in catalog["services"] if s["region_count"] > 0]
    models = catalog.get("models", [])
    apis = catalog["apis"]

    # Create lightweight JS data bundle for client-side dynamic 4-region comparison matrix
    matrix_data = {
        "regions": [
            {
                "id": r["region_id"],
                "name": f"{r['region_id']} — {r['region_name']} ({r['sub_region']})",
                "is_low_co2": r["is_low_co2"],
                "zones": r["zone_count"],
                "service_count": r["service_count"],
                "ai_model_count": r.get("ai_model_count", len(r.get("ai_models", []))),
                "machine_series": r["machine_series"],
                "gpus": r["gpus"],
                "cost_index": r.get("pricing", {}).get("relative_compute_index", 1.0),
                "cost_delta": r.get("pricing", {}).get("delta_vs_baseline", "Baseline (0%)"),
            }
            for r in regions
        ],
        "services": [
            {
                "name": s["name"],
                "slug": s["slug"],
                "category": s["category"],
                "apis": s["api_names"],
                "ops": s["total_api_methods"],
                "sla": s.get("sla", {}).get("headline_display", "—"),
                "regions": s["regions"],
            }
            for s in services
        ],
        "models": [
            {
                "name": m["model_name"],
                "id": m["model_id"],
                "family": m["family"],
                "modality": m["modality"],
                "global": m.get("global_endpoint", False),
                "regions": m.get("regions", []),
            }
            for m in models
        ],
    }
    data_dir = DIST_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "matrix_data.js").write_text(
        f"window.GCP_MATRIX_DATA = {json.dumps(matrix_data)};\n",
        encoding="utf-8",
    )

    api_rows = []
    for a in apis:
        vers = ", ".join(a.get("all_versions", []))
        res_chips = " ".join(f'<span class="code-chip">{esc(r)}</span>' for r in a.get("resources", [])[:8])
        if len(a.get("resources", [])) > 8:
            res_chips += f' <span class="badge badge-gray">+{len(a["resources"]) - 8}</span>'
        sample_ops = " ".join(
            f'<span class="code-chip">{esc(m["httpMethod"])} {esc(m["id"].split(".")[-1])}</span>'
            for m in a.get("methods", [])[:4]
        )
        api_rows.append(
            f'<tr>'
            f'<td data-val="{esc(a["service_endpoint"])}"><span class="code-chip" style="font-weight:700;color:var(--gcp-blue);">{esc(a["service_endpoint"])}</span></td>'
            f'<td data-val="{esc(a["title"])}"><strong>{esc(a["title"])}</strong><div style="font-size:12px;color:var(--text-muted);">{esc(a.get("description", "")[:140])}</div></td>'
            f'<td data-val="{esc(a["preferred_version"])}"><span class="badge badge-blue">{esc(a["preferred_version"])}</span> <span style="font-size:11.5px;color:var(--text-muted);">({esc(vers)})</span></td>'
            f'<td data-val="{a["method_count"]}"><strong>{a["method_count"]}</strong> <span style="font-size:12px;color:var(--gcp-green);">({a["regional_method_count"]} regional)</span></td>'
            f'<td>{res_chips or "—"}<div style="margin-top:4px;">{sample_ops}</div></td>'
            f'<td><a href="{esc(a.get("documentation_link", ""))}" target="_blank" rel="noopener">Docs ↗</a></td>'
            f'</tr>'
        )

    categories = sorted({s["category"] for s in services})
    cat_opts = "\n".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in categories)

    body = f"""
    <div class="section-card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:14px;">
        <div>
          <h2 class="section-title" style="margin-bottom:4px;">🔍 Multi-Region Capabilities, AI Models &amp; Gap Comparison Matrix</h2>
          <p style="margin:0;color:var(--text-muted);font-size:13px;">
            Compare up to 4 Google Cloud Regions side-by-side across Regional Services, AI &amp; Foundation Models, Relative Cost Multipliers, Hardware Machine Series, GPU Accelerators, and Discovery REST API Operations.
          </p>
        </div>
        <button class="btn btn-primary" onclick="exportComparisonCSV()">⬇ Export Matrix CSV</button>
      </div>

      <div class="toolbar">
        <div class="toolbar-group">
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">COMPARE MODE</label>
            <select id="cmp-mode" class="select-input" style="font-weight:700;color:var(--gcp-blue);">
              <option value="services">☁️ Google Cloud Services ({len(services)})</option>
              <option value="models">🤖 AI &amp; Foundation Models ({len(models)})</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">PRIMARY REGION (A)</label>
            <select id="cmp-r1" class="select-input"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">REGION (B)</label>
            <select id="cmp-r2" class="select-input"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">REGION (C)</label>
            <select id="cmp-r3" class="select-input"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">REGION (D)</label>
            <select id="cmp-r4" class="select-input"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">CATEGORY / FAMILY</label>
            <select id="cmp-cat" class="select-input">
              <option value="">All Categories</option>
              {cat_opts}
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">SEARCH SERVICE / MODEL</label>
            <input id="cmp-search" type="search" class="select-input" placeholder="Filter matrix..." style="min-width:190px;">
          </div>
          <label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;margin-top:16px;cursor:pointer;">
            <input id="cmp-diff-only" type="checkbox"> Show Differences / Gaps Only
          </label>
        </div>
      </div>

      <div id="cmp-hardware-summary" style="margin-bottom:14px;"></div>

      <div class="table-scroll">
        <table id="cmp-table" class="data-table">
          <thead>
            <tr id="cmp-thead-row"></tr>
          </thead>
          <tbody id="cmp-tbody"></tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">⚡ Google Cloud Discovery REST API Catalog ({len(apis)} Service APIs)</h2>
      <div class="toolbar" style="margin-bottom:12px;">
        <input id="disc-search" type="search" class="search-input" placeholder="Search API endpoint (e.g. aiplatform.googleapis.com), resource, or REST method...">
        <div id="disc-count" class="count-label">Showing {len(apis)} of {len(apis)}</div>
      </div>
      <div class="table-scroll">
        <table id="disc-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Service Endpoint ⇅</th>
              <th data-sort="str">API Title &amp; Description ⇅</th>
              <th data-sort="str">Versions ⇅</th>
              <th data-sort="num">REST Operations ⇅</th>
              <th>Top Resources &amp; Sample Operations</th>
              <th>Docs</th>
            </tr>
          </thead>
          <tbody>
            {"".join(api_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <script src="data/matrix_data.js?v={meta.get('generated_epoch', 1)}-v2"></script>
    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        setupTableFilter({{ searchId: 'disc-search', tableId: 'disc-table', countId: 'disc-count' }});

        const data = window.GCP_MATRIX_DATA;
        if (!data) return;
        const selects = ['cmp-r1', 'cmp-r2', 'cmp-r3', 'cmp-r4'].map(id => document.getElementById(id));
        const defaults = ['us-central1', 'us-east4', 'europe-west1', 'asia-south1'];

        selects.forEach((sel, idx) => {{
          data.regions.forEach(r => {{
            const opt = document.createElement('option');
            opt.value = r.id;
            opt.textContent = r.name;
            if (r.id === defaults[idx]) opt.selected = true;
            sel.appendChild(opt);
          }});
          sel.addEventListener('change', renderMatrix);
        }});

        const modeEl = document.getElementById('cmp-mode');
        const catEl = document.getElementById('cmp-cat');

        function populateCategoryDropdown() {{
          const mode = modeEl.value;
          const items = mode === 'models'
            ? Array.from(new Set((data.models || []).map(m => m.family))).sort()
            : Array.from(new Set((data.services || []).map(s => s.category))).sort();
          catEl.innerHTML = `<option value="">All ${{mode === 'models' ? 'Model Families' : 'Categories'}}</option>` +
            items.map(c => `<option value="${{c}}">${{c}}</option>`).join('');
        }}

        modeEl.addEventListener('change', () => {{
          populateCategoryDropdown();
          renderMatrix();
        }});
        catEl.addEventListener('change', renderMatrix);
        document.getElementById('cmp-search').addEventListener('input', renderMatrix);
        document.getElementById('cmp-diff-only').addEventListener('change', renderMatrix);

        try {{
          const params = new URLSearchParams(window.location.search);
          if (params.get('mode') === 'models') {{
            modeEl.value = 'models';
            populateCategoryDropdown();
          }}
          if (params.get('diff') === '1') {{
            document.getElementById('cmp-diff-only').checked = true;
          }}
        }} catch (e) {{}}

        function renderMatrix() {{
          const mode = modeEl.value;
          const rids = selects.map(s => s.value);
          const cat = catEl.value;
          const q = document.getElementById('cmp-search').value.trim().toLowerCase();
          const diffOnly = document.getElementById('cmp-diff-only').checked;

          const regMap = Object.fromEntries(data.regions.map(r => [r.id, r]));

          // Render Hardware, Cost, GPU & AI Model Comparison Header
          const hwHtml = rids.map(rid => {{
            const r = regMap[rid] || {{}};
            const cIdx = (r.cost_index || 1.0).toFixed(2);
            return `<div style="flex:1;min-width:220px;background:var(--bg-subtle);border:1px solid var(--border-subtle);border-radius:8px;padding:10px 14px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:700;color:var(--gcp-blue);"><a href="regions/${{rid}}.html">${{rid}}</a> ${{r.is_low_co2 ? '🌱' : ''}}</span>
                <span class="badge badge-blue">💰 ${{cIdx}}x</span>
              </div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;"><strong>${{r.service_count || 0}}</strong> Services • <strong>${{r.ai_model_count || 0}}</strong> AI Models • <strong>${{r.zones || 3}}</strong> Zones</div>
              <div style="font-size:11.5px;margin-top:4px;"><strong>Machine Series (${{(r.machine_series||[]).length}}):</strong> ${{(r.machine_series||[]).slice(0,8).join(', ')}}</div>
              <div style="font-size:11.5px;margin-top:2px;"><strong>GPUs (${{(r.gpus||[]).length}}):</strong> ${{(r.gpus||[]).join(', ') || 'CPU Only'}}</div>
            </div>`;
          }}).join('');
          document.getElementById('cmp-hardware-summary').innerHTML = `<div style="display:flex;flex-wrap:wrap;gap:10px;">${{hwHtml}}</div>`;

          if (mode === 'models') {{
            document.getElementById('cmp-thead-row').innerHTML = `
              <th>AI Model Name &amp; ID</th>
              <th>Family / Provider</th>
              <th>Modality &amp; Global Endpoint</th>
              ${{rids.map(rid => `<th><a href="regions/${{rid}}.html#region-ai-models">${{rid}}</a></th>`).join('')}}
            `;
            const rows = [];
            (data.models || []).forEach(m => {{
              if (cat && m.family !== cat) return;
              if (q && !(m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q) || m.family.toLowerCase().includes(q) || m.modality.toLowerCase().includes(q))) return;
              const flags = rids.map(rid => (m.regions || []).includes(rid));
              if (diffOnly && (flags.every(Boolean) || flags.every(f => !f))) return;
              rows.push(`<tr>
                <td><a href="models.html" style="font-weight:600;">${{m.name}}</a> <div><span class="code-chip">${{m.id}}</span></div></td>
                <td><span class="badge badge-gray">${{m.family}}</span></td>
                <td><span class="badge badge-blue">${{m.modality}}</span> ${{m.global ? '<span class="badge badge-purple">🌐 global</span>' : ''}}</td>
                ${{flags.map(ok => ok
                  ? '<td><span class="badge badge-green">✔ Available</span></td>'
                  : '<td><span class="badge badge-red">✖ Not Available</span></td>'
                ).join('')}}
              </tr>`);
            }});
            document.getElementById('cmp-tbody').innerHTML = rows.join('') || '<tr><td colspan="7">No matching AI models found for current filter.</td></tr>';
            return;
          }}

          document.getElementById('cmp-thead-row').innerHTML = `
            <th>Service Name</th>
            <th>Category &amp; Target SLA</th>
            <th>API Endpoint &amp; Ops</th>
            ${{rids.map(rid => `<th><a href="regions/${{rid}}.html">${{rid}}</a></th>`).join('')}}
          `;

          const rows = [];
          data.services.forEach(s => {{
            if (cat && s.category !== cat) return;
            if (q && !(s.name.toLowerCase().includes(q) || s.category.toLowerCase().includes(q) || (s.apis||[]).join(' ').toLowerCase().includes(q))) return;
            const flags = rids.map(rid => s.regions.includes(rid));
            if (diffOnly && (flags.every(Boolean) || flags.every(f => !f))) return;

            rows.push(`<tr>
              <td><a href="services/${{s.slug}}.html" style="font-weight:600;">${{s.name}}</a></td>
              <td><span class="badge badge-gray">${{s.category}}</span> ${{s.sla && s.sla !== '—' ? `<span class="badge badge-green">🛡️ ${{s.sla}}</span>` : ''}}</td>
              <td><span class="code-chip">${{(s.apis||[])[0] || 'google-cloud'}}</span> <span class="badge badge-blue">${{s.ops}} ops</span></td>
              ${{flags.map(ok => ok
                ? '<td><span class="badge badge-green">✔ Available</span></td>'
                : '<td><span class="badge badge-red">✖ Not Available</span></td>'
              ).join('')}}
            </tr>`);
          }});

          document.getElementById('cmp-tbody').innerHTML = rows.join('') || '<tr><td colspan="7">No matching services found for current filter.</td></tr>';
        }}

        window.exportComparisonCSV = function() {{
          const rids = selects.map(s => s.value);
          const mode = modeEl.value;
          if (mode === 'models') {{
            const lines = [['Model Name', 'Model ID', 'Family', 'Modality', 'Global Endpoint', ...rids].join(',')];
            (data.models || []).forEach(m => {{
              const row = [
                `"${{m.name.replace(/"/g, '""')}}"`,
                `"${{m.id}}"`,
                `"${{m.family}}"`,
                `"${{m.modality}}"`,
                m.global ? 'Yes' : 'No',
                ...rids.map(rid => (m.regions || []).includes(rid) ? 'Available' : 'Not Available')
              ];
              lines.push(row.join(','));
            }});
            const blob = new Blob([lines.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `google_cloud_ai_models_${{rids.join('_vs_')}}.csv`;
            a.click();
            return;
          }}
          const lines = [['Service Name', 'Category', 'API Endpoint', 'API Operations', ...rids].join(',')];
          data.services.forEach(s => {{
            const row = [
              `"${{s.name.replace(/"/g, '""')}}"`,
              `"${{s.category}}"`,
              `"${{(s.apis||[]).join(';')}}"`,
              s.ops,
              ...rids.map(rid => s.regions.includes(rid) ? 'Available' : 'Not Available')
            ];
            lines.push(row.join(','));
          }});
          const blob = new Blob([lines.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }});
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `google_cloud_region_comparison_${{rids.join('_vs_')}}.csv`;
          a.click();
        }};

        renderMatrix();
      }});
    </script>
    """
    (DIST_DIR / "capabilities.html").write_text(
        render_layout("Capabilities & Multi-Region Matrix", "capabilities", body, meta),
        encoding="utf-8",
    )


def generate_pops_page(catalog: dict[str, Any]) -> None:
    """Generate dist/pops.html (130 Availability Zones + Edge & CDN PoPs)."""
    meta = catalog["meta"]
    regions = catalog["regions"]
    pops = catalog["pops"]

    zone_rows = []
    for r in regions:
        for z in r.get("zone_details", []):
            m_chips = " ".join(f'<span class="code-chip">{esc(m)}</span>' for m in z.get("machine_types", []))
            c_chips = ", ".join(z.get("cpus", []))
            g_chips = " ".join(f'<span class="badge badge-purple">{esc(g)}</span>' for g in z.get("gpus", [])) or "—"
            o_chips = " ".join(f'<span class="badge badge-blue">{esc(o)}</span>' for o in z.get("options", [])) or "Standard"
            zone_rows.append(
                f'<tr data-filter1="{esc(r["sub_region"])}" data-flag="{str(bool(z.get("gpus"))).lower()}">'
                f'<td data-val="{esc(z["zone"])}"><a href="regions/{esc(r["region_id"])}.html"><span class="code-chip" style="font-weight:700;color:#1a73e8;">{esc(z["zone"])}</span></a></td>'
                f'<td data-val="{esc(r["region_id"])}"><a href="regions/{esc(r["region_id"])}.html">{esc(r["region_id"])}</a></td>'
                f'<td data-val="{esc(z.get("location", ""))}">{esc(z.get("location", ""))}</td>'
                f'<td data-val="{len(z.get("machine_types", []))}"><div style="max-width:340px;">{m_chips}</div></td>'
                f'<td style="font-size:12px;color:#5f6368;max-width:260px;">{esc(c_chips)}</td>'
                f'<td>{g_chips}</td>'
                f'<td>{o_chips}</td>'
                f'</tr>'
            )

    pop_rows = []
    for ptype, plist in [
        ("Edge Point of Presence (PoP)", pops.get("edge_pops", [])),
        ("Cloud CDN Point of Presence", pops.get("cloud_cdn_pops", [])),
        ("Media CDN Point of Presence", pops.get("media_cdn_pops", [])),
    ]:
        for p in plist:
            pop_rows.append(
                f'<tr>'
                f'<td><strong>{esc(p.get("label", ""))}</strong></td>'
                f'<td><span class="badge badge-blue">{esc(ptype)}</span></td>'
                f'<td>{esc(p.get("lat", ""))}, {esc(p.get("lng", ""))}</td>'
                f'</tr>'
            )

    body = f"""
    <div class="section-card">
      <h2 class="section-title">🏢 All 130 Google Cloud Availability Zones — Hardware, CPU Platforms &amp; GPU Matrix</h2>
      <div class="toolbar" style="margin-bottom:12px;">
        <div class="toolbar-group">
          <input id="z-search" type="search" class="search-input" placeholder="Search zone (us-central1-a), CPU (Axion, Turin, Sapphire Rapids), or GPU (A4X, A3 Mega, L4)...">
          <label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;cursor:pointer;">
            <input id="z-gpu" type="checkbox"> GPU-Enabled Zones Only ({meta['counts']['gpu_zones']})
          </label>
        </div>
        <div id="z-count" class="count-label">Showing {len(zone_rows)} of {len(zone_rows)}</div>
      </div>
      <div class="table-scroll">
        <table id="z-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Zone ID ⇅</th>
              <th data-sort="str">Region ⇅</th>
              <th data-sort="str">City &amp; Country ⇅</th>
              <th data-sort="num">Machine Series ⇅</th>
              <th>Supported CPU Microarchitectures</th>
              <th>GPU Accelerators</th>
              <th>Confidential VM &amp; Options</th>
            </tr>
          </thead>
          <tbody>
            {"".join(zone_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🌐 Global Network Edge, Cloud CDN &amp; Media CDN Points of Presence ({len(pop_rows)} PoPs)</h2>
      <div class="toolbar" style="margin-bottom:12px;">
        <input id="pop-search" type="search" class="search-input" placeholder="Search city or country for Edge / CDN PoP...">
        <div id="pop-count" class="count-label">Showing {len(pop_rows)} of {len(pop_rows)}</div>
      </div>
      <div class="table-scroll">
        <table id="pop-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Metro / City Location ⇅</th>
              <th data-sort="str">PoP Type ⇅</th>
              <th>Coordinates (Lat, Lng)</th>
            </tr>
          </thead>
          <tbody>
            {"".join(pop_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        setupTableFilter({{ searchId: 'z-search', checkboxId: 'z-gpu', tableId: 'z-table', countId: 'z-count' }});
        setupTableFilter({{ searchId: 'pop-search', tableId: 'pop-table', countId: 'pop-count' }});
      }});
    </script>
    """
    (DIST_DIR / "pops.html").write_text(
        render_layout("Zones & Edge PoPs", "pops", body, meta),
        encoding="utf-8",
    )


def generate_whatsnew_page(catalog: dict[str, Any]) -> None:
    """Generate dist/whatsnew.html (Official Release Notes + Regional Launches & Daily Snapshot Diffs)."""
    meta = catalog["meta"]
    items = catalog.get("whats_new", [])
    rel_notes = catalog.get("release_notes", [])
    svcs_by_slug = {s["slug"]: s["name"] for s in catalog.get("services", [])}

    rel_types = sorted({n.get("release_type", "Announcement") for n in rel_notes if n.get("release_type")})
    rel_type_opts = "\n".join(f'<option value="{esc(rt)}">{esc(rt)}</option>' for rt in rel_types)
    rel_rows = []
    for n in rel_notes:
        rt = n.get("release_type", "Announcement")
        rt_up = rt.upper()
        rt_cls = (
            "badge-green" if rt_up in ("FEATURE", "LAUNCH")
            else ("badge-red" if rt_up in ("DEPRECATED", "SECURITY", "BREAKING")
            else ("badge-yellow" if rt_up in ("FIXED", "CHANGED") else "badge-blue"))
        )
        slug = n.get("service_slug", "")
        prod = n.get("product_name", "Google Cloud")
        prod_html = f'<a href="services/{esc(slug)}.html" style="font-weight:600;">{esc(svcs_by_slug.get(slug, prod))}</a>' if slug in svcs_by_slug else f'<strong>{esc(prod)}</strong>'
        link = n.get("url", n.get("link", "https://cloud.google.com/release-notes"))
        pub_date = n.get("date", n.get("published_date", ""))
        rel_rows.append(
            f'<tr data-filter1="{esc(rt)}">'
            f'<td data-val="{esc(pub_date)}"><strong>{esc(pub_date)}</strong></td>'
            f'<td data-val="{esc(rt)}"><span class="badge {rt_cls}">{esc(rt)}</span></td>'
            f'<td data-val="{esc(prod)}">{prod_html}</td>'
            f'<td><div style="font-size:12.5px;color:var(--text-primary);">{esc(n.get("summary", ""))}</div></td>'
            f'<td><a href="{esc(link)}" target="_blank" rel="noopener">Note ↗</a></td>'
            f'</tr>'
        )

    rows = []
    for item in items:
        rid = item.get("region_id", "")
        rlink = f'<a href="regions/{esc(rid)}.html"><code>{esc(rid)}</code></a>' if rid and not rid.startswith("future-") else f'<code>{esc(rid)}</code>'
        badge_cls = "badge-green" if item.get("type") == "Regional Expansion" else ("badge-blue" if item.get("type") == "Region Launch" else "badge-yellow")
        rows.append(
            f'<tr>'
            f'<td data-val="{esc(item.get("date", ""))}"><strong>{esc(item.get("date", ""))}</strong></td>'
            f'<td><span class="badge {badge_cls}">{esc(item.get("type", ""))}</span></td>'
            f'<td><strong>{esc(item.get("service", ""))}</strong></td>'
            f'<td>{esc(item.get("region_name", ""))} ({rlink})</td>'
            f'<td>{esc(item.get("details", ""))}</td>'
            f'</tr>'
        )

    body = f"""
    <div class="section-card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:8px;">
        <h2 class="section-title" style="margin:0;">📰 Official Google Cloud Release Notes Feed ({len(rel_rows)} Recent Entries)</h2>
        <a href="https://cloud.google.com/release-notes" target="_blank" rel="noopener" class="btn">Official Release Notes Portal ↗</a>
      </div>
      <p style="margin:0 0 14px 0;color:var(--text-muted);font-size:13px;">
        Harvested once daily from the official Google Cloud Release Notes Atom XML feed and cached locally for offline inspection.
      </p>
      <div class="toolbar" style="margin-bottom:12px;">
        <div class="toolbar-group">
          <input id="rn-search" type="search" class="search-input" placeholder="Search release notes by service, feature, CVE, or deprecation...">
          <select id="rn-type" class="select-input">
            <option value="">All Release Types ({len(rel_types)})</option>
            {rel_type_opts}
          </select>
        </div>
        <div id="rn-count" class="count-label">Showing {len(rel_rows)} of {len(rel_rows)}</div>
      </div>
      <div class="table-scroll">
        <table id="rn-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str" style="width:110px;">Published ⇅</th>
              <th data-sort="str" style="width:130px;">Release Type ⇅</th>
              <th data-sort="str" style="width:190px;">Service / Product ⇅</th>
              <th>Release Summary</th>
              <th style="width:80px;">Source</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rel_rows) if rel_rows else '<tr><td colspan="5">No cached release notes available.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🆕 Regional Launches &amp; Daily Snapshot Diffs</h2>
      <p style="margin:0 0 14px 0;color:var(--text-muted);font-size:13px;">
        Every daily run of <code>harvester.py</code> saves a dated snapshot to <code>data/cache/snapshots/YYYY-MM-DD.json</code> and automatically computes newly added services and AI models per region, alongside chronological Google Cloud region launches and announced future regions.
      </p>
      <div class="toolbar" style="margin-bottom:12px;">
        <input id="wn-search" type="search" class="search-input" placeholder="Search recent region launches, upcoming regions, AI models, or service expansions...">
        <div id="wn-count" class="count-label">Showing {len(rows)} of {len(rows)}</div>
      </div>
      <div class="table-scroll">
        <table id="wn-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Date / Year ⇅</th>
              <th data-sort="str">Change Type ⇅</th>
              <th data-sort="str">Service / Scope ⇅</th>
              <th data-sort="str">Region ⇅</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {"".join(rows)}
          </tbody>
        </table>
      </div>
    </div>
    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        setupTableFilter({{ searchId: 'rn-search', select1Id: 'rn-type', tableId: 'rn-table', countId: 'rn-count' }});
        setupTableFilter({{ searchId: 'wn-search', tableId: 'wn-table', countId: 'wn-count' }});
      }});
    </script>
    """
    (DIST_DIR / "whatsnew.html").write_text(
        render_layout("What's New & Release Notes", "whatsnew", body, meta),
        encoding="utf-8",
    )


def generate_pricing_sla_page(catalog: dict[str, Any]) -> None:
    """Generate dist/pricing-sla.html (Interactive SLA Architecture Calculator + FinOps Regional Cost & Service Pricing)."""
    meta = catalog["meta"]
    services = catalog.get("services", [])
    regions = catalog.get("regions", [])

    formal_sla_count = sum(1 for s in services if s.get("sla", {}).get("has_formal_sla"))
    free_tier_count = sum(1 for s in services if s.get("pricing", {}).get("has_free_tier"))
    tier1_regions = sum(1 for r in regions if (r.get("pricing", {}).get("relative_compute_index", 1.0) <= 1.02))

    categories = sorted({s.get("category", "Cloud") for s in services})
    cat_opts = "\n".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in categories)

    svc_calc_list = []
    svc_rows = []
    for s in services:
        sla = s.get("sla", {})
        prc = s.get("pricing", {})
        has_sla = bool(sla.get("has_formal_sla"))
        uptime_num = sla.get("headline_uptime_pct") or 99.9
        uptime_disp = sla.get("headline_display", "No formal SLA")
        downtime = sla.get("max_monthly_downtime", "N/A")
        tiers_summary = " • ".join(f"{t.get('tier_name', 'Standard')}: {t.get('uptime_display', str(t.get('uptime_pct', '')) + '%')}" for t in sla.get("tiers", [])[:3]) or "Preview / Best-effort"
        billing_model = prc.get("billing_model", "Pay-as-you-go")
        raw_units = prc.get("primary_units", "")
        units_str = raw_units if isinstance(raw_units, str) else ", ".join(raw_units[:2])
        cud = prc.get("cud_support", "Varies")
        has_free = bool(prc.get("has_free_tier"))
        free_badge = '<span class="badge badge-green">✔ Free Tier</span>' if has_free else '<span class="badge badge-gray">Paid Usage</span>'
        sla_badge_cls = "badge-green" if (sla.get("headline_uptime_pct") or 0) >= 99.99 else ("badge-blue" if has_sla else "badge-gray")

        if has_sla and sla.get("headline_uptime_pct"):
            svc_calc_list.append({
                "slug": s["slug"],
                "name": s["name"],
                "uptime": float(sla["headline_uptime_pct"]),
                "tiers": sla.get("tiers", []),
            })

        svc_rows.append(
            f'<tr data-filter1="{esc(s["category"])}" data-flag="{str(has_free).lower()}">'
            f'<td data-val="{esc(s["name"])}"><a href="services/{esc(s["slug"])}.html" style="font-weight:600;">{esc(s["name"])}</a></td>'
            f'<td data-val="{esc(s["category"])}"><span class="badge badge-gray">{esc(s["category"])}</span></td>'
            f'<td data-val="{sla.get("headline_uptime_pct") or 0}"><span class="badge {sla_badge_cls}">🛡️ {esc(uptime_disp)}</span><div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">Max/mo: {esc(downtime)}</div></td>'
            f'<td style="font-size:12px;max-width:280px;">{esc(tiers_summary)}</td>'
            f'<td data-val="{esc(billing_model)}"><strong>{esc(billing_model)}</strong><div style="font-size:11.5px;color:var(--text-muted);">{esc(units_str)}</div></td>'
            f'<td style="font-size:12px;">{esc(cud)}</td>'
            f'<td>{free_badge}</td>'
            f'<td><a href="{esc(sla.get("sla_url", "https://cloud.google.com/terms/sla"))}" target="_blank" rel="noopener">SLA ↗</a> · <a href="{esc(prc.get("pricing_url", "https://cloud.google.com/pricing"))}" target="_blank" rel="noopener">Pricing ↗</a></td>'
            f'</tr>'
        )

    reg_calc_list = [
        {
            "id": r["region_id"],
            "name": f"{r['region_id']} — {r['region_name']} ({r['sub_region']})",
            "compute": float(r.get("pricing", {}).get("relative_compute_index", 1.0)),
            "storage": float(r.get("pricing", {}).get("relative_storage_index", 1.0)),
            "tier": r.get("pricing", {}).get("tier", "Tier 1"),
            "egress": r.get("pricing", {}).get("inter_region_egress_band", "Standard"),
            "low_co2": bool(r.get("is_low_co2")),
        }
        for r in regions
    ]

    reg_rows = []
    for r in regions:
        rp = r.get("pricing", {})
        c_idx = rp.get("relative_compute_index", 1.0)
        s_idx = rp.get("relative_storage_index", 1.0)
        tier = rp.get("tier", "Tier 1")
        b_cls = "badge-green" if c_idx <= 1.05 else ("badge-blue" if c_idx <= 1.15 else "badge-yellow")
        co2 = ' <span class="badge badge-green">🌱 Low CO₂</span>' if r.get("is_low_co2") else ""
        reg_rows.append(
            f'<tr>'
            f'<td data-val="{esc(r["region_id"])}"><a href="regions/{esc(r["region_id"])}.html"><span class="code-chip" style="font-weight:700;color:var(--gcp-blue);">{esc(r["region_id"])}</span></a>{co2}</td>'
            f'<td data-val="{esc(r["region_name"])}"><strong>{esc(r["region_name"])}</strong> <span style="color:var(--text-muted);font-size:12px;">({esc(r["sub_region"])})</span></td>'
            f'<td data-val="{c_idx}"><span class="badge {b_cls}">{c_idx:.2f}x ({esc(rp.get("delta_vs_baseline", "Baseline"))})</span></td>'
            f'<td data-val="{s_idx}"><code>{s_idx:.2f}x</code></td>'
            f'<td data-val="{esc(tier)}">{esc(tier)}</td>'
            f'<td style="font-size:12px;"><code>{esc(rp.get("inter_region_egress_band", "Standard"))}</code></td>'
            f'<td><span class="badge badge-green">1Y: ~{rp.get("cud_1y_discount_pct", 37)}%</span> <span class="badge badge-purple">3Y: ~{rp.get("cud_3y_discount_pct", 55)}%</span></td>'
            f'</tr>'
        )

    calc_json = json.dumps({"services": svc_calc_list, "regions": reg_calc_list})

    body = f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Services with Formal SLA</div>
        <div class="kpi-value">{formal_sla_count}</div>
        <div class="kpi-sub">Out of {len(services)} cataloged Google Cloud services</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Peak Multi-Region Uptime</div>
        <div class="kpi-value">99.999%</div>
        <div class="kpi-sub">Spanner, Bigtable &amp; Global LB (≤ 26s/mo)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Baseline Cost Regions (1.00x)</div>
        <div class="kpi-value">{tier1_regions} / {len(regions)}</div>
        <div class="kpi-sub">Relative to <code>us-central1</code> baseline</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Free Tier Eligible Services</div>
        <div class="kpi-value">{free_tier_count}</div>
        <div class="kpi-sub">+ Up to 55% 3-Year CUD compute savings</div>
      </div>
    </div>

    <div class="studio-grid">
      <div class="section-card" style="margin-bottom:0;">
        <h2 class="section-title">🛡️ Interactive Composite Workload SLA Calculator</h2>
        <p style="margin:0 0 12px 0;font-size:13px;color:var(--text-muted);">
          Model end-to-end architecture availability across up to 4 dependent Google Cloud services in <strong>Serial</strong> (single-region critical path) vs. <strong>Active-Active Multi-Region</strong> deployment topologies.
        </p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">COMPONENT 1 (INGRESS / EDGE)</label>
            <select id="sla-s1" class="select-input" style="width:100%;"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">COMPONENT 2 (COMPUTE / APP)</label>
            <select id="sla-s2" class="select-input" style="width:100%;"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">COMPONENT 3 (DATABASE / STATE)</label>
            <select id="sla-s3" class="select-input" style="width:100%;"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">COMPONENT 4 (OPTIONAL AI / BUS)</label>
            <select id="sla-s4" class="select-input" style="width:100%;"></select>
          </div>
        </div>
        <div style="margin-bottom:12px;">
          <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">TOPOLOGY ARCHITECTURE PATTERN</label>
          <select id="sla-topo" class="select-input" style="width:100%;font-weight:600;color:var(--gcp-blue);">
            <option value="serial">🔗 Single-Region Serial Critical Path (A × B × C × D)</option>
            <option value="dual_active">🌐 Dual-Region Active-Active Redundant Stack (1 − (1 − R_stack)²)</option>
          </select>
        </div>
        <div class="calc-metric-box" id="sla-result-box"></div>
      </div>

      <div class="section-card" id="regional-cost" style="margin-bottom:0;">
        <h2 class="section-title">💰 Regional FinOps Cost Multiplier &amp; CUD Estimator</h2>
        <p style="margin:0 0 12px 0;font-size:13px;color:var(--text-muted);">
          Compare relative compute/storage spend across Google Cloud regions against <code>us-central1 (1.00x)</code> and model 1-Year / 3-Year Committed Use Discount (CUD) impact.
        </p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">BASELINE MONTHLY SPEND (USD)</label>
            <input id="cost-base" type="number" min="100" step="500" value="10000" class="select-input" style="width:100%;font-weight:700;">
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">COMMITMENT DISCOUNT TIER</label>
            <select id="cost-cud" class="select-input" style="width:100%;font-weight:600;">
              <option value="1.0">On-Demand Pay-As-You-Go (0% CUD)</option>
              <option value="0.63">1-Year Committed Use (~37% Compute Savings)</option>
              <option value="0.45">3-Year Committed Use (~55% Compute Savings)</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">PRIMARY REGION (A)</label>
            <select id="cost-r1" class="select-input" style="width:100%;"></select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;">TARGET / DR REGION (B)</label>
            <select id="cost-r2" class="select-input" style="width:100%;"></select>
          </div>
        </div>
        <div class="calc-metric-box" id="cost-result-box"></div>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🛡️ Google Cloud Service SLA Targets, Billing Models &amp; FinOps Catalog ({len(services)} Services)</h2>
      <div class="toolbar" style="margin-bottom:12px;">
        <div class="toolbar-group">
          <input id="ps-search" type="search" class="search-input" placeholder="Search service SLA or billing model (e.g. Spanner, 99.999%, Cloud Run, BigQuery, CUD)...">
          <select id="ps-cat" class="select-input">
            <option value="">All Categories ({len(categories)})</option>
            {cat_opts}
          </select>
          <label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;cursor:pointer;">
            <input id="ps-free" type="checkbox"> Free Tier Eligible Only ({free_tier_count})
          </label>
        </div>
        <div id="ps-count" class="count-label">Showing {len(svc_rows)} of {len(svc_rows)}</div>
      </div>
      <div class="table-scroll">
        <table id="ps-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Service Name ⇅</th>
              <th data-sort="str">Category ⇅</th>
              <th data-sort="num">Headline SLA &amp; Budget ⇅</th>
              <th>Architecture SLA Tiers</th>
              <th data-sort="str">Billing Model &amp; Units ⇅</th>
              <th>CUD / Commitment</th>
              <th>Free Tier</th>
              <th>Official Links</th>
            </tr>
          </thead>
          <tbody>
            {"".join(svc_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🌍 All {len(regions)} Google Cloud Regions — Relative Cost Multipliers &amp; Egress Tiers</h2>
      <p style="margin:0 0 12px 0;font-size:13px;color:var(--text-muted);">
        Relative compute and storage price indices normalized against <code>us-central1 = 1.00x</code>. Actual SKU pricing varies by machine family and storage class; always verify exact figures in the <a href="https://cloud.google.com/products/calculator" target="_blank" rel="noopener">Official Google Cloud Pricing Calculator</a>.
      </p>
      <div class="toolbar" style="margin-bottom:12px;">
        <input id="rc-search" type="search" class="search-input" placeholder="Search region ID, city, or cost tier (e.g. us-central1, europe-west4, asia-south1, Tier 1)...">
        <div id="rc-count" class="count-label">Showing {len(reg_rows)} of {len(reg_rows)}</div>
      </div>
      <div class="table-scroll">
        <table id="rc-table" class="data-table">
          <thead>
            <tr>
              <th data-sort="str">Region ID ⇅</th>
              <th data-sort="str">Location ⇅</th>
              <th data-sort="num">Compute Cost Index ⇅</th>
              <th data-sort="num">Storage Index ⇅</th>
              <th data-sort="str">FinOps Price Tier ⇅</th>
              <th>Inter-Region Egress Band</th>
              <th>Standard CUD Discounts</th>
            </tr>
          </thead>
          <tbody>
            {"".join(reg_rows)}
          </tbody>
        </table>
      </div>
    </div>

    <script>
      window.GCP_PRICING_SLA_DATA = {calc_json};
      document.addEventListener('DOMContentLoaded', () => {{
        setupTableFilter({{ searchId: 'ps-search', select1Id: 'ps-cat', checkboxId: 'ps-free', tableId: 'ps-table', countId: 'ps-count' }});
        setupTableFilter({{ searchId: 'rc-search', tableId: 'rc-table', countId: 'rc-count' }});

        const d = window.GCP_PRICING_SLA_DATA;
        const slaSelects = ['sla-s1', 'sla-s2', 'sla-s3', 'sla-s4'].map(id => document.getElementById(id));
        const slaDefaults = ['cloud-load-balancing', 'cloud-run', 'spanner', ''];

        slaSelects.forEach((sel, idx) => {{
          if (idx === 3) {{
            const noneOpt = document.createElement('option');
            noneOpt.value = '';
            noneOpt.textContent = '— None (3-Component Stack) —';
            sel.appendChild(noneOpt);
          }}
          d.services.forEach(s => {{
            const opt = document.createElement('option');
            opt.value = s.slug;
            opt.textContent = `${{s.name}} (${{s.uptime}}%)`;
            if (s.slug === slaDefaults[idx]) opt.selected = true;
            sel.appendChild(opt);
          }});
          sel.addEventListener('change', computeSLA);
        }});
        document.getElementById('sla-topo').addEventListener('change', computeSLA);

        function fmtDuration(sec) {{
          if (sec < 1) return '< 1s';
          if (sec < 60) return `${{Math.round(sec)}}s`;
          if (sec < 3600) {{
            const m = Math.floor(sec / 60), s = Math.round(sec % 60);
            return s > 0 ? `${{m}}m ${{s}}s` : `${{m}}m`;
          }}
          const h = Math.floor(sec / 3600), m = Math.round((sec % 3600) / 60);
          return `${{h}}h ${{m}}m`;
        }}

        function computeSLA() {{
          const svcMap = Object.fromEntries(d.services.map(s => [s.slug, s]));
          const picked = slaSelects.map(el => svcMap[el.value]).filter(Boolean);
          let serialProb = picked.reduce((acc, s) => acc * (s.uptime / 100.0), 1.0);
          const topo = document.getElementById('sla-topo').value;
          let finalProb = topo === 'dual_active' ? (1.0 - Math.pow(1.0 - serialProb, 2)) : serialProb;
          const pct = Math.min(99.9999, finalProb * 100.0);
          const monthlySec = (1.0 - finalProb) * 30 * 86400;
          const annualSec = (1.0 - finalProb) * 365 * 86400;
          document.getElementById('sla-result-box').innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:10px;">
              <div>
                <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--text-muted);">Composite Workload SLA</div>
                <div style="font-size:28px;font-weight:800;color:var(--gcp-green);">${{pct.toFixed(pct >= 99.995 ? 4 : 3)}}%</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:12px;"><strong>Max Monthly Downtime:</strong> <code>${{fmtDuration(monthlySec)}}</code></div>
                <div style="font-size:12px;color:var(--text-muted);"><strong>Max Annual Downtime:</strong> <code>${{fmtDuration(annualSec)}}</code></div>
              </div>
            </div>
            <div style="margin-top:8px;font-size:12px;color:var(--text-muted);">
              Active Stack (${{picked.length}} services): ${{picked.map(s => `<code>${{s.name}} (${{s.uptime}}%)</code>`).join(' → ')}}
            </div>
          `;
        }}

        const r1El = document.getElementById('cost-r1');
        const r2El = document.getElementById('cost-r2');
        d.regions.forEach(r => {{
          [r1El, r2El].forEach((sel, idx) => {{
            const opt = document.createElement('option');
            opt.value = r.id;
            opt.textContent = `${{r.id}} (${{r.compute.toFixed(2)}}x)${{r.low_co2 ? ' 🌱' : ''}}`;
            if ((idx === 0 && r.id === 'us-central1') || (idx === 1 && r.id === 'asia-south1')) opt.selected = true;
            sel.appendChild(opt);
          }});
        }});
        [r1El, r2El, document.getElementById('cost-base'), document.getElementById('cost-cud')].forEach(el => {{
          el.addEventListener('input', computeCost);
          el.addEventListener('change', computeCost);
        }});

        function computeCost() {{
          const regMap = Object.fromEntries(d.regions.map(r => [r.id, r]));
          const base = Math.max(0, parseFloat(document.getElementById('cost-base').value || '10000'));
          const cudFactor = parseFloat(document.getElementById('cost-cud').value || '1.0');
          const ra = regMap[r1El.value] || d.regions[0];
          const rb = regMap[r2El.value] || d.regions[0];
          const costA = base * ra.compute * cudFactor;
          const costB = base * rb.compute * cudFactor;
          const diffMonthly = costB - costA;
          const sign = diffMonthly >= 0 ? '+' : '−';
          const fmt = n => '$' + Math.round(Math.abs(n)).toLocaleString();
          document.getElementById('cost-result-box').innerHTML = `
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
              <div>
                <div style="font-size:11px;font-weight:700;color:var(--text-muted);">${{ra.id}} / MO</div>
                <div style="font-size:21px;font-weight:800;color:var(--gcp-blue);">${{fmt(costA)}}</div>
                <div style="font-size:11px;color:var(--text-muted);">${{ra.compute.toFixed(2)}}x Compute</div>
              </div>
              <div>
                <div style="font-size:11px;font-weight:700;color:var(--text-muted);">${{rb.id}} / MO</div>
                <div style="font-size:21px;font-weight:800;color:var(--text-primary);">${{fmt(costB)}}</div>
                <div style="font-size:11px;color:var(--text-muted);">${{rb.compute.toFixed(2)}}x Compute</div>
              </div>
              <div>
                <div style="font-size:11px;font-weight:700;color:var(--text-muted);">ANNUAL DELTA</div>
                <div style="font-size:21px;font-weight:800;color:${{diffMonthly <= 0 ? 'var(--gcp-green)' : 'var(--gcp-yellow)'}};">${{sign}}${{fmt(diffMonthly * 12)}}/yr</div>
                <div style="font-size:11px;color:var(--text-muted);">${{sign}}${{fmt(diffMonthly)}}/mo</div>
              </div>
            </div>
            <div style="margin-top:8px;font-size:12px;color:var(--text-muted);">
              Inter-Region Egress Band (<code>${{rb.id}}</code>): <code>${{rb.egress}}</code>
            </div>
          `;
        }}

        computeSLA();
        computeCost();
      }});
    </script>
    """
    (DIST_DIR / "pricing-sla.html").write_text(
        render_layout("Pricing & SLA Intelligence", "pricing-sla", body, meta),
        encoding="utf-8",
    )


def generate_arch_page(catalog: dict[str, Any]) -> None:
    """Generate dist/arch.html (Architecture & Cost Breakdown)."""
    meta = catalog["meta"]
    body = """
    <div class="section-card">
      <h2 class="section-title">🏗️ Solution Architecture (Offline Web PWA, Native SwiftUI iOS App &amp; Google Cloud Mode)</h2>
      <p>
        This unofficial tool is engineered across two dedicated offline-first form factors—an <strong>Analytical Offline Web PWA</strong> (<code>dist/</code>) and a <strong>Modern Native Universal SwiftUI iOS/iPadOS App</strong> (<code>ios/GoogleCloudExplorer</code>)—backed by a once-a-day local cache or serverless Google Cloud backend (~$0.30/month).
      </p>

      <div style="background:#f8f9fa;border:1px solid #dadce0;border-radius:10px;padding:20px;margin:18px 0;overflow-x:auto;">
        <svg viewBox="0 0 1050 320" width="100%" height="auto" style="min-width:780px;font-family:sans-serif;">
          <!-- Background Groups -->
          <rect x="15" y="15" width="250" height="290" rx="10" fill="#e8f0fe" stroke="#1a73e8" stroke-width="1.5"/>
          <text x="30" y="42" font-size="13" font-weight="bold" fill="#1a73e8">1. Google Cloud Upstream Sources</text>

          <rect x="305" y="15" width="380" height="290" rx="10" fill="#e6f4ea" stroke="#137333" stroke-width="1.5"/>
          <text x="320" y="42" font-size="13" font-weight="bold" fill="#137333">2. Quota-Resilient Harvester (Daily 24h Refresh)</text>

          <rect x="725" y="15" width="310" height="290" rx="10" fill="#fef7e0" stroke="#b06000" stroke-width="1.5"/>
          <text x="740" y="42" font-size="13" font-weight="bold" fill="#b06000">3. Offline-First Web PWA, CLI &amp; Native iOS</text>

          <!-- Upstream Boxes -->
          <rect x="30" y="60" width="220" height="48" rx="6" fill="#fff" stroke="#1a73e8"/>
          <text x="42" y="82" font-size="12" font-weight="bold" fill="#202124">Locations &amp; Vertex AI Models</text>
          <text x="42" y="98" font-size="10.5" fill="#5f6368">data.json, locations_map.json, AI models</text>

          <rect x="30" y="122" width="220" height="48" rx="6" fill="#fff" stroke="#1a73e8"/>
          <text x="42" y="144" font-size="12" font-weight="bold" fill="#202124">Compute Zones, GPUs &amp; SLAs</text>
          <text x="42" y="160" font-size="10.5" fill="#5f6368">130 Zones, GPUs, SLA Index, Release XML</text>

          <rect x="30" y="184" width="220" height="48" rx="6" fill="#fff" stroke="#1a73e8"/>
          <text x="42" y="206" font-size="12" font-weight="bold" fill="#202124">Google Discovery REST API</text>
          <text x="42" y="222" font-size="10.5" fill="#5f6368">200+ $discovery/rest Specs (10.5k+ Methods)</text>

          <rect x="30" y="246" width="220" height="44" rx="6" fill="#fff" stroke="#1a73e8"/>
          <text x="42" y="267" font-size="12" font-weight="bold" fill="#202124">Edge &amp; CDN PoP Feeds</text>
          <text x="42" y="281" font-size="10.5" fill="#5f6368">101 Edge PoPs • 75 Cloud CDN • 62 Media CDN</text>

          <!-- Harvester Boxes -->
          <rect x="325" y="62" width="340" height="58" rx="6" fill="#fff" stroke="#137333"/>
          <text x="340" y="84" font-size="12" font-weight="bold" fill="#202124">ResilientFetcher + enrichment.py</text>
          <text x="340" y="101" font-size="10.5" fill="#5f6368">• Token-Bucket Rate Limiter (15 req/s cap)</text>
          <text x="340" y="114" font-size="10.5" fill="#5f6368">• SLA Tiers, FinOps Indices &amp; Release Notes XML</text>

          <rect x="325" y="136" width="340" height="54" rx="6" fill="#fff" stroke="#137333"/>
          <text x="340" y="158" font-size="12" font-weight="bold" fill="#202124">24h Cache &amp; Compact Mobile Bundle</text>
          <text x="340" y="175" font-size="10.5" fill="#5f6368">gcp_catalog.json + mobile_catalog.json (~130KB gz)</text>

          <rect x="325" y="206" width="340" height="80" rx="6" fill="#fff" stroke="#137333"/>
          <text x="340" y="228" font-size="12" font-weight="bold" fill="#202124">Static Site &amp; PWA Generator (generator.py)</text>
          <text x="340" y="246" font-size="10.5" fill="#5f6368">• Compiles 205+ static HTML pages + sw.js into dist/</text>
          <text x="340" y="262" font-size="10.5" fill="#5f6368">• Pre-computes Matrix JS + SLA/Pricing Calculators</text>
          <text x="340" y="276" font-size="10.5" fill="#5f6368">• ETag / Gzip delta sync for Native iOS clients</text>

          <!-- Delivery Boxes -->
          <rect x="745" y="65" width="270" height="65" rx="6" fill="#fff" stroke="#b06000"/>
          <text x="760" y="88" font-size="12" font-weight="bold" fill="#202124">Offline Web PWA + server.py</text>
          <text x="760" y="105" font-size="10.5" fill="#5f6368">• Service Worker offline cache + &lt;2ms reads</text>
          <text x="760" y="120" font-size="10.5" fill="#5f6368">• ETag + Gzip REST API (/api/mobile-catalog)</text>

          <rect x="745" y="145" width="270" height="65" rx="6" fill="#fff" stroke="#b06000"/>
          <text x="760" y="168" font-size="12" font-weight="bold" fill="#202124">Modern Native SwiftUI iOS App</text>
          <text x="760" y="185" font-size="10.5" fill="#5f6368">• Bento Hub, 3D MapKit Globe, Swift Charts</text>
          <text x="760" y="200" font-size="10.5" fill="#5f6368">• Bundled offline JSON + CoreSpotlight</text>

          <rect x="745" y="225" width="270" height="65" rx="6" fill="#fff" stroke="#b06000"/>
          <text x="760" y="248" font-size="12" font-weight="bold" fill="#202124">Terminal CLI &amp; Serverless Cloud</text>
          <text x="760" y="265" font-size="10.5" fill="#5f6368">• cli.py (service, models, sla, pricing, updates)</text>
          <text x="760" y="280" font-size="10.5" fill="#5f6368">• Optional Cloud Run + Cloud CDN (~$0.30/mo)</text>

          <!-- Arrows -->
          <line x1="250" y1="90" x2="325" y2="90" stroke="#3c4043" stroke-width="2"/>
          <line x1="250" y1="150" x2="325" y2="150" stroke="#3c4043" stroke-width="2"/>
          <line x1="250" y1="210" x2="325" y2="210" stroke="#3c4043" stroke-width="2"/>
          <line x1="665" y1="160" x2="745" y2="160" stroke="#3c4043" stroke-width="2"/>
        </svg>
      </div>
    </div>

    <div class="section-card">
      <h2 class="section-title">🛡️ Quota &amp; Rate-Limit Protection Architecture</h2>
      <ul>
        <li><strong>Daily 24-Hour Cache TTL (<code>data/cache/gcp_catalog.json</code>):</strong> All user searches, region lookups, AI model checks, SLA calculations, pricing comparisons, and CLI queries are served 100% from local static HTML and cached JSON. Upstream Google Cloud endpoints are only queried once every 24 hours (or when explicitly forced via <code>--force</code>).</li>
        <li><strong>Token-Bucket Rate Limiting:</strong> Outbound requests during the daily harvest are paced through a thread-safe token-bucket rate limiter (default 15 requests/sec across 8 bounded worker threads) to prevent burst quota exhaustion on <code>discovery.googleapis.com</code>.</li>
        <li><strong>Exponential Backoff with Full Jitter &amp; <code>Retry-After</code> Parsing:</strong> Any HTTP <code>429 Too Many Requests</code>, <code>403 Rate Limit Exceeded</code>, or <code>5xx</code> response automatically honors the server's <code>Retry-After</code> header or backs off using <code>random.uniform(0.5 * base * 2^attempt, base * 2^attempt)</code> up to 5 attempts.</li>
        <li><strong>Per-API Disk Checkpointing &amp; Offline Sync:</strong> Every Discovery REST spec is atomically written to disk, while the Web PWA Service Worker (<code>sw.js</code>) and Native iOS app bundle (<code>mobile_catalog.json</code>) provide full Airplane-Mode offline capability.</li>
      </ul>
    </div>

    <div class="section-card">
      <h2 class="section-title">☁️ Serverless Google Cloud Hosting Architecture &amp; Monthly Cost Breakdown</h2>
      <p>If deployed to Google Cloud in addition to running locally, the daily harvester and static site can be hosted serverlessly at near-zero cost:</p>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Component Role</th>
              <th>Google Cloud Native Service</th>
              <th>Configuration &amp; Sizing</th>
              <th>Monthly Google Cloud Cost Estimate (Excl. Free Tier)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Container Registry</strong></td>
              <td><strong>Artifact Registry</strong></td>
              <td>1 GB container image storage</td>
              <td><code>1 GB × $0.10/GB = $0.10 / month</code></td>
            </tr>
            <tr>
              <td><strong>Daily Harvester Runtime</strong></td>
              <td><strong>Cloud Run Jobs + Cloud Scheduler</strong></td>
              <td>1 run/day × 30s × 1 vCPU / 1 GiB RAM</td>
              <td><code>900 vCPU-s &amp; 900 GiB-s = $0.03 / month</code></td>
            </tr>
            <tr>
              <td><strong>Static Site Object Storage</strong></td>
              <td><strong>Cloud Storage (Standard Bucket)</strong></td>
              <td>1 GB storage + 10k PUT/GET operations</td>
              <td><code>$0.020 + $0.054 = $0.08 / month</code></td>
            </tr>
            <tr>
              <td><strong>Global Edge Caching</strong></td>
              <td><strong>Cloud CDN + Global External Application LB</strong></td>
              <td>1 GB cache egress + 10k HTTPS requests</td>
              <td><code>1 GB × $0.08 + requests = $0.09 / month</code></td>
            </tr>
            <tr>
              <td><strong>Edge Security / WAF (Optional)</strong></td>
              <td><strong>Google Cloud Armor Standard</strong></td>
              <td>1 Security Policy + Rules + 1M requests</td>
              <td><code>$5.00 policy + rules (Optional)</code></td>
            </tr>
            <tr style="background:var(--gcp-blue-light);font-weight:700;">
              <td colspan="3">Total Monthly Cost (Local Workstation Mode / Cloud Serverless Mode without optional WAF)</td>
              <td>$0.00 Locally / ~$0.30/month on Google Cloud</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    """
    (DIST_DIR / "arch.html").write_text(
        render_layout("Architecture & Cost", "arch", body, meta),
        encoding="utf-8",
    )


def generate_faqs_page(catalog: dict[str, Any]) -> None:
    """Generate dist/faqs.html (FAQs & CLI Reference)."""
    meta = catalog["meta"]
    body = """
    <div class="section-card">
      <h2 class="section-title">❓ Frequently Asked Questions (FAQs), Offline Mode &amp; CLI Guide</h2>

      <p><strong>Q: Is this an official Google Cloud website or mobile app?</strong></p>
      <ul>
        <li><strong>No.</strong> Both the Web PWA and the Native SwiftUI iOS/iPadOS App are <strong>unofficial tools</strong> and are not affiliated with, endorsed by, or sponsored by Google LLC or Google Cloud.</li>
        <li>While data is automatically harvested from public Google Cloud feeds, SLA indexes, release notes, and Discovery APIs, it is provided "as-is" without warranty. Always refer to the <a href="https://cloud.google.com/about/locations" target="_blank" rel="noopener">Official Google Cloud Locations Page</a>, <a href="https://cloud.google.com/terms/sla" target="_blank" rel="noopener">Official Google Cloud SLAs</a>, <a href="https://cloud.google.com/pricing" target="_blank" rel="noopener">Official Google Cloud Pricing</a>, and <a href="https://cloud.google.com/docs" target="_blank" rel="noopener">Official Google Cloud Documentation</a> for authoritative information.</li>
      </ul>

      <p><strong>Q: How do Offline Mode and the Native SwiftUI iOS/iPadOS App work?</strong></p>
      <ul>
        <li><strong>Offline-Ready Web PWA:</strong> Opening the web app over <code>http://localhost:8080</code> (or HTTPS) registers <code>sw.js</code>, pre-caching all core views, stylesheets, scripts, and <code>data/mobile_catalog.json</code> so you can browse offline in Airplane Mode.</li>
        <li><strong>Modern Native SwiftUI App (<code>ios/GoogleCloudExplorer</code>):</strong> Built natively for iOS 17+ (iPhone &amp; iPad) with Bento dashboards, a 3D interactive Apple MapKit Globe, Swift Charts SLA/FinOps scrubbers, Customer Stack blueprints, and CoreSpotlight. It embeds <code>mobile_catalog.json</code> directly inside the app bundle for instant 0ms offline launch and delta-syncs via ETag/Gzip against <code>/api/mobile-catalog</code> when online.</li>
      </ul>

      <p><strong>Q: How do I run the Web App and CLI locally?</strong></p>
      <pre style="background:var(--bg-subtle);border:1px solid var(--border-color);padding:14px;border-radius:8px;overflow-x:auto;font-family:ui-monospace,monospace;font-size:12.5px;"># 1. Start the local web server (serves dist/ + ETag/Gzip REST API + daily auto-refresh thread)
python3 server.py --port 8080

# 2. Query Services, Regions, AI Models, SLAs, Pricing &amp; Release Notes via cli.py:
python3 cli.py service "Vertex AI"
python3 cli.py sla "Cloud Spanner"
python3 cli.py pricing asia-south1
python3 cli.py pricing "BigQuery"
python3 cli.py updates --type FEATURE
python3 cli.py models claude --region us-east5
python3 cli.py compare us-central1 europe-west1 asia-south1 --diff

# 3. Force an immediate live re-harvest &amp; static site rebuild:
python3 cli.py refresh --force</pre>
    </div>
    """
    (DIST_DIR / "faqs.html").write_text(
        render_layout("FAQs & CLI Usage", "faqs", body, meta),
        encoding="utf-8",
    )


def generate_all(catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate the entire static site & offline PWA bundle in dist/ from the catalog."""
    if catalog is None:
        if CATALOG_FILE.exists():
            catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        else:
            catalog = harvest_all()

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    write_shared_assets()
    write_pwa_offline_assets(catalog)
    generate_index_page(catalog)
    generate_regions_page(catalog)
    generate_models_page(catalog)
    generate_service_detail_pages(catalog)
    generate_region_detail_pages(catalog)
    generate_capabilities_page(catalog)
    generate_pops_page(catalog)
    generate_pricing_sla_page(catalog)
    generate_whatsnew_page(catalog)
    generate_arch_page(catalog)
    generate_faqs_page(catalog)

    total_pages = (
        9
        + len(catalog.get("services", []))
        + len(catalog.get("regions", []))
    )
    print(f"[Generator] Built {total_pages} static HTML pages + PWA offline bundle in {DIST_DIR}")
    return catalog


if __name__ == "__main__":
    generate_all()

