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
