/**
 * KGH Meta Ads — AI Filter Page (aiconfig.js)
 * Dedicated page to manage AI skip phrases
 */

// ─── In-memory cache of all phrases ───────────────────────
let _allPhrases = [];

// Called by SPA router when aifilter page is opened
function loadAifilter() {
  afLoad();
}

// Also for backwards compat with Settings page hook
function loadSettings() { /* settings page has no phrases anymore */ }

// ─── Load all phrases ──────────────────────────────────────
async function afLoad() {
  document.getElementById('af-list').innerHTML =
    '<div class="loading-row"><span class="spinner"></span> Memuat kalimat...</div>';

  try {
    const phrases = await api.get('/ai-config/skip-phrases');
    _allPhrases = phrases || [];
    afRender(_allPhrases);
    afUpdateStats(_allPhrases);
    // Update sidebar badge
    const badge = document.getElementById('badge-aifilter');
    if (badge) badge.textContent = _allPhrases.filter(p => p.is_active).length;
  } catch (e) {
    document.getElementById('af-list').innerHTML =
      '<div class="empty-state" style="color:var(--danger)">Gagal memuat data. Coba refresh.</div>';
  }
}

// ─── Update stats bar ──────────────────────────────────────
function afUpdateStats(phrases) {
  const total    = phrases.length;
  const active   = phrases.filter(p => p.is_active).length;
  const inactive = total - active;
  const contains = phrases.filter(p => p.match_type === 'contains').length;

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('stat-total',    total);
  set('stat-active',   active);
  set('stat-inactive', inactive);
  set('stat-contains', contains);
}

// ─── Render phrase list ────────────────────────────────────
function afRender(phrases) {
  const list = document.getElementById('af-list');
  if (!phrases || phrases.length === 0) {
    list.innerHTML = '<div class="empty-state">Belum ada kalimat. Tambahkan di form atas.</div>';
    return;
  }

  list.innerHTML = phrases.map(p => `
    <div class="af-row ${p.is_active ? '' : 'af-row-inactive'}" id="af-row-${p.id}">
      <div class="af-row-main">
        <div class="af-row-phrase">${escHtml(p.phrase)}</div>
        <div class="af-row-meta">
          <span class="match-badge match-${p.match_type}">${matchLabel(p.match_type)}</span>
          ${p.description ? `<span class="af-row-desc">${escHtml(p.description)}</span>` : ''}
          <span class="af-row-status ${p.is_active ? 'af-status-on' : 'af-status-off'}">
            ${p.is_active ? 'Aktif' : 'Nonaktif'}
          </span>
        </div>
      </div>
      <div class="af-row-actions">
        <button class="af-btn-toggle ${p.is_active ? 'on' : 'off'}"
          onclick="afToggle(${p.id})" title="${p.is_active ? 'Nonaktifkan' : 'Aktifkan'}">
          ${p.is_active ? 'ON' : 'OFF'}
        </button>
        <button class="af-btn-del" onclick="afDelete(${p.id})" title="Hapus">
          <i data-lucide="trash-2" size="14"></i>
        </button>
      </div>
    </div>
  `).join('');

  if (window.lucide) lucide.createIcons();
}

// ─── Search / filter (client-side, fast) ──────────────────
function afSearch() {
  const q      = (document.getElementById('af-search')?.value || '').toLowerCase();
  const mType  = document.getElementById('af-filter-match')?.value || '';
  const status = document.getElementById('af-filter-status')?.value || '';

  const filtered = _allPhrases.filter(p => {
    const matchQ = !q || p.phrase.toLowerCase().includes(q) ||
                   (p.description || '').toLowerCase().includes(q);
    const matchT = !mType || p.match_type === mType;
    const matchS = !status
      || (status === 'active'   &&  p.is_active)
      || (status === 'inactive' && !p.is_active);
    return matchQ && matchT && matchS;
  });

  afRender(filtered);
}

// ─── Add phrase ────────────────────────────────────────────
async function afAddPhrase() {
  const phraseInput = document.getElementById('af-phrase');
  const descInput   = document.getElementById('af-desc');
  const matchSel    = document.getElementById('af-match');
  const errEl       = document.getElementById('af-add-error');
  const btn         = document.getElementById('af-add-btn');

  const phrase = phraseInput.value.trim();
  if (!phrase) {
    phraseInput.focus();
    phraseInput.style.borderColor = 'var(--danger)';
    setTimeout(() => phraseInput.style.borderColor = '', 1800);
    return;
  }

  errEl.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-sm"></span> Menambahkan...';

  try {
    await api.post('/ai-config/skip-phrases', {
      phrase,
      description: descInput.value.trim() || null,
      match_type: matchSel.value
    });
    phraseInput.value = '';
    descInput.value   = '';
    matchSel.value    = 'contains';
    showToast('Kalimat berhasil ditambahkan', 'success');
    await afLoad();
  } catch (e) {
    errEl.textContent = 'Gagal menambahkan. Kalimat mungkin sudah ada.';
    errEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="plus" size="14"></i> Tambah';
    if (window.lucide) lucide.createIcons();
  }
}

// ─── Toggle active ────────────────────────────────────────
async function afToggle(id) {
  try {
    const res = await api.patch(`/ai-config/skip-phrases/${id}`);
    // Update in-memory cache
    const p = _allPhrases.find(x => x.id === id);
    if (p) p.is_active = res.is_active;

    // Update DOM row
    const row = document.getElementById(`af-row-${id}`);
    const toggleBtn = row?.querySelector('.af-btn-toggle');
    const statusEl  = row?.querySelector('.af-row-status');
    if (res.is_active) {
      row?.classList.remove('af-row-inactive');
      if (toggleBtn) { toggleBtn.textContent = 'ON';  toggleBtn.classList.replace('off', 'on'); }
      if (statusEl)  { statusEl.textContent = 'Aktif'; statusEl.className = 'af-row-status af-status-on'; }
    } else {
      row?.classList.add('af-row-inactive');
      if (toggleBtn) { toggleBtn.textContent = 'OFF'; toggleBtn.classList.replace('on', 'off'); }
      if (statusEl)  { statusEl.textContent = 'Nonaktif'; statusEl.className = 'af-row-status af-status-off'; }
    }

    afUpdateStats(_allPhrases);
    const badge = document.getElementById('badge-aifilter');
    if (badge) badge.textContent = _allPhrases.filter(x => x.is_active).length;

  } catch (e) {
    showToast('Gagal mengubah status', 'error');
  }
}

// ─── Delete phrase ────────────────────────────────────────
async function afDelete(id) {
  const phrase = _allPhrases.find(x => x.id === id);
  const label  = phrase ? `"${phrase.phrase.substring(0, 40)}..."` : 'kalimat ini';
  if (!confirm(`Hapus ${label}?`)) return;

  try {
    await api.delete(`/ai-config/skip-phrases/${id}`);
    _allPhrases = _allPhrases.filter(x => x.id !== id);
    document.getElementById(`af-row-${id}`)?.remove();
    afUpdateStats(_allPhrases);
    if (_allPhrases.length === 0) {
      document.getElementById('af-list').innerHTML =
        '<div class="empty-state">Belum ada kalimat. Tambahkan di form atas.</div>';
    }
    const badge = document.getElementById('badge-aifilter');
    if (badge) badge.textContent = _allPhrases.filter(x => x.is_active).length;
    showToast('Kalimat dihapus', 'success');
  } catch (e) {
    showToast('Gagal menghapus', 'error');
  }
}

// ─── Helpers ──────────────────────────────────────────────
function escHtml(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function matchLabel(type) {
  return { contains: 'Mengandung', exact: 'Sama Persis', startswith: 'Diawali' }[type] || type;
}

// Enter key on phrase input → submit
document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && document.getElementById('af-phrase') === document.activeElement) {
      afAddPhrase();
    }
  });
});
