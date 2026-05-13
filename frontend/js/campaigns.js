/**
 * KGH Meta Ads — Campaigns Page Logic
 */

let campaignFilter = 'ALL';

async function loadCampaigns() {
  const tbody = document.getElementById('tbody-campaigns');
  tbody.innerHTML = `<tr><td colspan="9" class="loading-row"><span class="spinner"></span> Memuat data...</td></tr>`;
  
  const params = campaignFilter === 'ALL' ? {} : { status: campaignFilter };
  const campaigns = await api.get('/campaigns', params);
  
  if (!campaigns || campaigns.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="loading-row">Tidak ada campaign ditemukan</td></tr>`;
    return;
  }

  tbody.innerHTML = campaigns.map(c => {
    const m = c.latest_metrics || {};
    const spend = m.spend || 0;
    const leads = m.conversions || 0;
    const cpl = leads > 0 ? (spend / leads) : 0;
    
    return `
      <tr>
        <td>
          <strong>${c.name}</strong><br>
          <small style="color:var(--text-muted)">ID: ${c.meta_id}</small>
        </td>
        <td><span class="status-badge ${c.status.toLowerCase()}">${c.status}</span></td>
        <td>${formatCurrency(c.daily_budget || 0)}</td>
        <td>${formatCurrency(spend)}</td>
        <td>${formatNumber(m.impressions || 0)}</td>
        <td>${(m.ctr || 0)}%</td>
        <td><strong>${leads}</strong></td>
        <td>${formatCurrency(cpl)}</td>
        <td>
          <button class="btn-icon" title="View AdSets"><i data-lucide="layers" size="16"></i></button>
        </td>
      </tr>
    `;
  }).join('');
  
  lucide.createIcons();
}

document.addEventListener('DOMContentLoaded', () => {
  // Campaign Filters
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      campaignFilter = e.target.getAttribute('data-filter');
      loadCampaigns();
    });
  });

  // Sync Button
  const btnSync = document.getElementById('btn-sync-campaigns');
  if (btnSync) {
    btnSync.addEventListener('click', async () => {
      btnSync.innerHTML = '<span class="spinner" style="width:14px;height:14px"></span> Syncing...';
      btnSync.disabled = true;
      await api.post('/campaigns/sync', {});
      setTimeout(() => {
        btnSync.innerHTML = '<i data-lucide="refresh-cw" size="14"></i> Sync Meta';
        btnSync.disabled = false;
        lucide.createIcons();
        loadCampaigns(); // Refresh data after a few seconds assuming n8n finishes
      }, 5000);
    });
  }
});
