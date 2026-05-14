/**
 * KGH Meta Ads — Leads Page Logic
 */

let currentPage = 1;
let currentFilters = { status: '', score_label: '', assigned_to: '', search: '' };

async function loadLeads() {
  await loadLeadStats();
  
  const tbody = document.getElementById('tbody-leads');
  tbody.innerHTML = `<tr><td colspan="8" class="loading-row"><span class="spinner"></span> Memuat data...</td></tr>`;
  
  const params = { ...currentFilters, page: currentPage, limit: 20 };
  const leads = await api.get('/leads', params);
  
  if (!leads || leads.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="loading-row">Tidak ada lead ditemukan</td></tr>`;
    return;
  }

  tbody.innerHTML = leads.map((l, i) => {
    const safeName = (l.full_name || 'Tanpa Nama').replace(/'/g, "\\'");
    return `
    <tr>
      <td>${(currentPage - 1) * 20 + i + 1}</td>
      <td>
        <strong class="clickable-name" onclick="openChatModal(${l.id}, '${safeName}', '${l.phone}')" title="Lihat Riwayat Chat">${l.full_name || 'Tanpa Nama'}</strong><br>
        <small style="color:var(--text-muted)">${l.source}</small>
      </td>
      <td>${l.phone || '-'}<br><small style="color:var(--text-muted)">${l.email || '-'}</small></td>
      <td><span class="status-badge ${l.score_label.toLowerCase()}">${l.score_label} (${l.score})</span></td>
      <td>
        <select class="status-select" data-id="${l.id}" onchange="updateLeadStatus(${l.id}, this.value)">
          <option value="NEW" ${l.status === 'NEW' ? 'selected' : ''}>NEW</option>
          <option value="CONTACTED" ${l.status === 'CONTACTED' ? 'selected' : ''}>CONTACTED</option>
          <option value="QUALIFIED" ${l.status === 'QUALIFIED' ? 'selected' : ''}>QUALIFIED</option>
          <option value="PROPOSAL" ${l.status === 'PROPOSAL' ? 'selected' : ''}>PROPOSAL</option>
          <option value="WON" ${l.status === 'WON' ? 'selected' : ''}>WON</option>
          <option value="LOST" ${l.status === 'LOST' ? 'selected' : ''}>LOST</option>
        </select>
      </td>
      <td>${l.assigned_to && l.assigned_to !== 'Unassigned' ? `<span class="agent-badge" style="font-size:12px; font-weight:600; color:var(--accent-1)">${l.assigned_to}</span>` : '<span style="color:var(--text-muted); font-size:12px">Unassigned</span>'}</td>
      <td>${formatDate(l.created_at)}</td>
      <td>
        <button class="btn-icon" onclick="openLeadModal(${l.id})" title="Detail"><i data-lucide="eye" size="16"></i></button>
      </td>
    </tr>
  `}).join('');
  
  lucide.createIcons();
}

async function loadLeadStats() {
  const stats = await api.get('/leads/stats');
  if (stats) {
    document.getElementById('lstat-total').textContent = formatNumber(stats.total);
    document.getElementById('lstat-new').textContent = formatNumber(stats.new);
    document.getElementById('lstat-contacted').textContent = formatNumber(stats.contacted);
    document.getElementById('lstat-qualified').textContent = formatNumber(stats.qualified);
    document.getElementById('lstat-hot').textContent = formatNumber(stats.hot);
    document.getElementById('lstat-warm').textContent = formatNumber(stats.warm);
  }
  
  // Also populate the agent dropdown
  const agentData = await api.get('/leads/agents/summary');
  const agentFilter = document.getElementById('lead-agent-filter');
  if (agentData && agentFilter) {
    // Preserve current selection if any
    const currVal = agentFilter.value;
    
    let html = '<option value="">Semua Agen</option>';
    if (agentData.agents) {
      agentData.agents.forEach(a => {
        html += `<option value="${a.name}">${a.name} (${a.total})</option>`;
      });
    }
    if (agentData.unassigned > 0) {
      html += `<option value="__unassigned__">Belum Ditugaskan (${agentData.unassigned})</option>`;
    }
    
    agentFilter.innerHTML = html;
    if (currVal) agentFilter.value = currVal;
  }
}

async function updateLeadStatus(id, newStatus) {
  const res = await api.patch(`/leads/${id}`, { status: newStatus });
  if (res) {
    loadLeadStats(); // refresh stats
  }
}

async function openLeadModal(id) {
  const modal = document.getElementById('modal-lead');
  const body = document.getElementById('modal-lead-body');
  
  modal.style.display = 'flex';
  body.innerHTML = '<div style="text-align:center; padding:40px"><span class="spinner"></span></div>';
  
  const lead = await api.get(`/leads/${id}`);
  if (!lead) {
    body.innerHTML = 'Gagal memuat detail lead';
    return;
  }

  let customFieldsHtml = '';
  if (lead.custom_fields && Object.keys(lead.custom_fields).length > 0) {
    customFieldsHtml = `<h4 style="margin-top:16px; margin-bottom:8px">Form Data</h4><div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:8px">`;
    for (const [k, v] of Object.entries(lead.custom_fields)) {
      customFieldsHtml += `<div style="margin-bottom:8px"><strong style="color:var(--text-muted); text-transform:capitalize">${k.replace(/_/g, ' ')}:</strong> ${v}</div>`;
    }
    customFieldsHtml += `</div>`;
  }

  let activitiesHtml = '';
  if (lead.activities && lead.activities.length > 0) {
    activitiesHtml = `<h4 style="margin-top:24px; margin-bottom:8px">Activity Timeline</h4><div class="timeline">`;
    lead.activities.forEach(a => {
      activitiesHtml += `
        <div style="padding-left:16px; border-left:2px solid var(--border-color); margin-bottom:16px; position:relative">
          <div style="position:absolute; left:-6px; top:4px; width:10px; height:10px; border-radius:50%; background:var(--accent-1)"></div>
          <div style="font-size:12px; color:var(--text-muted)">${formatDate(a.timestamp)} — ${a.performed_by}</div>
          <div style="font-weight:500">${a.action_type}</div>
          <div style="font-size:13px">${a.description || ''}</div>
        </div>`;
    });
    activitiesHtml += `</div>`;
  }

  body.innerHTML = `
    <div style="display:flex; justify-content:space-between; margin-bottom:16px">
      <div>
        <h2 style="font-size:24px; margin-bottom:4px">${lead.full_name || 'Tanpa Nama'}</h2>
        <div style="color:var(--text-muted)">${lead.phone || '-'} | ${lead.email || '-'}</div>
      </div>
      <div style="text-align:right">
        <span class="status-badge ${lead.score_label.toLowerCase()}">${lead.score_label} (${lead.score})</span>
        <div style="margin-top:8px; font-size:12px; color:var(--text-muted)">${lead.score_reason}</div>
      </div>
    </div>
    ${customFieldsHtml}
    ${activitiesHtml}
  `;
}

async function openChatModal(leadId, name, phone) {
  let modal = document.getElementById('modal-chat');
  if (!modal) {
    console.error('modal-chat element not found');
    return;
  }

  const body = document.getElementById('modal-chat-body');
  document.getElementById('modal-chat-title').textContent = name || 'Tanpa Nama';
  document.getElementById('modal-chat-subtitle').textContent = phone || '';

  modal.style.display = 'flex';
  body.innerHTML = '<div style="text-align:center; padding:40px"><span class="spinner"></span> Memuat percakapan...</div>';

  try {
    // Use backend proxy — avoids CORS issues with SocialChat API
    const data = await api.get(`/leads/${leadId}/messages`);

    const messages = (data && data.messages) || [];
    if (data && data.error && messages.length === 0) {
      body.innerHTML = `<div style="text-align:center;padding:20px;color:var(--warning)">&#9888; ${data.error}</div>`;
      return;
    }
    if (messages.length === 0) {
      body.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted)">Belum ada riwayat percakapan.</div>';
      return;
    }

    let html = '';
    messages.forEach(msg => {
      const isMe = msg.sendBy === 'agent' || (msg.senderName && msg.senderName !== name);
      const sender = isMe ? (msg.senderName || 'Agent') : (name || 'Lead');
      const rawTime = msg.sendAt || msg.createdAt || '';
      const time = rawTime ? new Date(rawTime).toLocaleTimeString('id-ID', {hour:'2-digit', minute:'2-digit'}) : '';
      const rawDate = rawTime ? new Date(rawTime).toLocaleDateString('id-ID', {day:'2-digit', month:'short'}) : '';
      const txt = msg.text || (msg.media ? '[Media]' : '[Sistem]');

      html += `
        <div class="chat-message ${isMe ? 'me' : 'them'}">
          <div class="chat-bubble">${txt}</div>
          <div class="chat-meta">
            <span>${sender}</span> &bull; <span>${rawDate} ${time}</span>
          </div>
        </div>
      `;
    });

    body.innerHTML = html;
    setTimeout(() => { body.scrollTop = body.scrollHeight; }, 100);

  } catch (e) {
    console.error('openChatModal error:', e);
    body.innerHTML = '<div style="text-align:center;padding:20px;color:var(--danger)">Gagal memuat percakapan. Periksa koneksi.</div>';
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('lead-status-filter')?.addEventListener('change', (e) => {
    currentFilters.status = e.target.value;
    currentPage = 1;
    loadLeads();
  });
  
  document.getElementById('lead-score-filter')?.addEventListener('change', (e) => {
    currentFilters.score_label = e.target.value;
    currentPage = 1;
    loadLeads();
  });
  
  document.getElementById('lead-agent-filter')?.addEventListener('change', (e) => {
    currentFilters.assigned_to = e.target.value;
    currentPage = 1;
    loadLeads();
  });

  let searchTimeout;
  document.getElementById('lead-search')?.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentFilters.search = e.target.value;
      currentPage = 1;
      loadLeads();
    }, 500);
  });

  document.getElementById('modal-lead-close')?.addEventListener('click', () => {
    document.getElementById('modal-lead').style.display = 'none';
  });
  
  document.getElementById('modal-chat-close')?.addEventListener('click', () => {
    document.getElementById('modal-chat').style.display = 'none';
  });
});
