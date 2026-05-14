/**
 * KGH Meta Ads — AI Config Page Logic
 * Manages skip phrases for AI conversation analysis
 */

// Called by SPA router when settings page is opened
function loadSettings() {
  loadSkipPhrases();
}

async function loadSkipPhrases() {
  const list = document.getElementById('skip-phrases-list');
  list.innerHTML = '<div class="loading-row"><span class="spinner"></span> Memuat...</div>';

  try {
    const phrases = await api.get('/ai-config/skip-phrases');
    if (!phrases || phrases.length === 0) {
      list.innerHTML = '<div class="empty-state">Belum ada kalimat yang ditambahkan.</div>';
      return;
    }

    list.innerHTML = phrases.map(p => `
      <div class="skip-phrase-row ${p.is_active ? '' : 'inactive'}" id="spr-${p.id}">
        <div class="skip-phrase-main">
          <div class="skip-phrase-text">${escapeHtml(p.phrase)}</div>
          <div class="skip-phrase-meta">
            <span class="match-badge match-${p.match_type}">${p.match_type}</span>
            ${p.description ? `<span class="skip-desc">${escapeHtml(p.description)}</span>` : ''}
          </div>
        </div>
        <div class="skip-phrase-actions">
          <button class="btn-toggle-phrase ${p.is_active ? 'active' : ''}"
            onclick="toggleSkipPhrase(${p.id})"
            title="${p.is_active ? 'Nonaktifkan' : 'Aktifkan'}">
            ${p.is_active ? '✓ Aktif' : '✗ Nonaktif'}
          </button>
          <button class="btn-delete-phrase" onclick="deleteSkipPhrase(${p.id})" title="Hapus">
            <i data-lucide="trash-2" size="14"></i>
          </button>
        </div>
      </div>
    `).join('');

    lucide.createIcons();
  } catch (e) {
    list.innerHTML = '<div class="empty-state" style="color:var(--danger)">Gagal memuat data.</div>';
  }
}

async function addSkipPhrase() {
  const phraseInput = document.getElementById('new-skip-phrase');
  const descInput   = document.getElementById('new-skip-desc');
  const matchSelect = document.getElementById('new-skip-match');

  const phrase = phraseInput.value.trim();
  if (!phrase) {
    phraseInput.focus();
    phraseInput.style.borderColor = 'var(--danger)';
    setTimeout(() => phraseInput.style.borderColor = '', 1500);
    return;
  }

  const btn = document.getElementById('btn-add-skip-phrase');
  btn.disabled = true;
  btn.textContent = 'Menambahkan...';

  try {
    await api.post('/ai-config/skip-phrases', {
      phrase,
      description: descInput.value.trim() || null,
      match_type: matchSelect.value
    });
    phraseInput.value = '';
    descInput.value   = '';
    matchSelect.value = 'contains';
    showToast('Kalimat berhasil ditambahkan', 'success');
    await loadSkipPhrases();
  } catch (e) {
    showToast('Gagal menambahkan kalimat', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '+ Tambah';
  }
}

async function toggleSkipPhrase(id) {
  try {
    const res = await api.patch(`/ai-config/skip-phrases/${id}`);
    const row = document.getElementById(`spr-${id}`);
    const btn = row.querySelector('.btn-toggle-phrase');
    if (res.is_active) {
      row.classList.remove('inactive');
      btn.classList.add('active');
      btn.textContent = '✓ Aktif';
      btn.title = 'Nonaktifkan';
    } else {
      row.classList.add('inactive');
      btn.classList.remove('active');
      btn.textContent = '✗ Nonaktif';
      btn.title = 'Aktifkan';
    }
  } catch (e) {
    showToast('Gagal mengubah status', 'error');
  }
}

async function deleteSkipPhrase(id) {
  if (!confirm('Hapus kalimat ini?')) return;
  try {
    await api.delete(`/ai-config/skip-phrases/${id}`);
    document.getElementById(`spr-${id}`)?.remove();
    showToast('Kalimat dihapus', 'success');
    // If list is now empty, reload to show empty state
    if (!document.querySelector('.skip-phrase-row')) {
      loadSkipPhrases();
    }
  } catch (e) {
    showToast('Gagal menghapus', 'error');
  }
}

function escapeHtml(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Auto-load when settings page is shown
document.addEventListener('DOMContentLoaded', () => {
  const settingsLink = document.querySelector('[data-page="settings"]');
  if (settingsLink) {
    settingsLink.addEventListener('click', () => {
      setTimeout(loadSkipPhrases, 100);
    });
  }
  // Also load if settings is the default active page
  if (document.getElementById('page-settings')?.classList.contains('active')) {
    loadSkipPhrases();
  }
});
