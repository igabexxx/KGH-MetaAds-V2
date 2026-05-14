/**
 * KGH Meta Ads — Dashboard Page Logic
 */

let trendChart = null;
let funnelChart = null;

async function loadDashboard() {
  document.getElementById('dash-date-range').textContent = `${currentDateRange} hari terakhir`;
  
  // 1. Fetch Overview Data
  const overview = await api.get('/analytics/overview', { days: currentDateRange });
  if (overview) {
    document.querySelector('#kpi-spend .kpi-value').textContent = formatCurrency(overview.total_spend);
    document.querySelector('#kpi-leads .kpi-value').textContent = formatNumber(overview.total_leads);
    document.querySelector('#kpi-cpl .kpi-value').textContent = formatCurrency(overview.average_cpl);
    document.querySelector('#kpi-ctr .kpi-value').textContent = overview.average_ctr + '%';
    
    document.getElementById('pill-hot').textContent = overview.hot_leads;
    document.getElementById('pill-warm').textContent = overview.warm_leads;
    document.getElementById('pill-cold').textContent = overview.cold_leads;
    document.getElementById('pill-campaigns').textContent = overview.active_campaigns;

    // Update Sidebar Badges
    document.getElementById('badge-leads-hot').textContent = overview.hot_leads;
    document.getElementById('badge-campaigns').textContent = overview.active_campaigns;
  }

  // 2. Load Charts
  await loadDashboardCharts();

  // 3. Load Recent Leads
  const leads = await api.get('/leads', { limit: 5 });
  const tbody = document.getElementById('tbody-recent-leads');
  if (leads && leads.length > 0) {
    tbody.innerHTML = leads.map(l => {
      const safeName = (l.full_name || '-').replace(/'/g, "\\'");
      return `
      <tr>
        <td>
          <strong class="clickable-name" onclick="openChatModal('${l.phone}', '${safeName}')" title="Lihat Riwayat Chat">${l.full_name || '-'}</strong>
        </td>
        <td>${l.phone || '-'}</td>
        <td><span class="status-badge ${l.score_label.toLowerCase()}">${l.score_label}</span></td>
        <td><span class="status-badge ${l.status.toLowerCase()}">${l.status}</span></td>
        <td>${formatDate(l.created_at)}</td>
      </tr>
    `}).join('');
  } else {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center">Belum ada data leads</td></tr>`;
  }

  // 4. Load Agent Distribution
  await loadAgentDistribution();
}

async function loadAgentDistribution() {
  const container = document.getElementById('agent-distribution');
  if (!container) return;

  const data = await api.get('/leads/agents/summary');
  if (!data || !data.agents) {
    container.innerHTML = '<div style="text-align:center; color:var(--text-muted); padding:16px">Tidak ada data agen</div>';
    return;
  }

  const agents = data.agents;
  const unassigned = data.unassigned || 0;

  let html = '<div class="agent-grid">';

  agents.forEach(a => {
    const total = a.total || 1;
    const hotPct = Math.round((a.hot / total) * 100);
    const warmPct = Math.round((a.warm / total) * 100);
    const coldPct = 100 - hotPct - warmPct;
    const safeName = a.name.replace(/'/g, "\\'");

    html += `
      <div class="agent-card" onclick="filterLeadsByAgent('${safeName}')" title="Klik untuk filter leads ${a.name}">
        <div class="agent-card-name">${a.name}</div>
        <div class="agent-card-total">${a.total}</div>
        <div class="agent-card-breakdown">
          <span class="ab-hot">\ud83d\udd25 ${a.hot}</span>
          <span class="ab-warm">\ud83c\udf21\ufe0f ${a.warm}</span>
          <span class="ab-cold">\u2744\ufe0f ${a.cold}</span>
        </div>
        <div class="agent-bar">
          <span class="bar-hot" style="width:${hotPct}%"></span>
          <span class="bar-warm" style="width:${warmPct}%"></span>
          <span class="bar-cold" style="width:${coldPct}%"></span>
        </div>
      </div>
    `;
  });

  if (unassigned > 0) {
    html += `
      <div class="agent-card" onclick="filterLeadsByAgent('__unassigned__')" title="Leads belum di-assign" style="opacity:0.7">
        <div class="agent-card-name" style="color:var(--text-muted)">Belum Ditugaskan</div>
        <div class="agent-card-total">${unassigned}</div>
        <div class="agent-card-breakdown">
          <span style="color:var(--text-muted)">Leads tanpa agen</span>
        </div>
      </div>
    `;
  }

  html += '</div>';
  container.innerHTML = html;
}

function filterLeadsByAgent(agentName) {
  window.location.hash = '#leads';
  setTimeout(() => {
    const agentFilter = document.getElementById('lead-agent-filter');
    if (agentFilter) {
      // Set value if option exists, otherwise add it
      let found = false;
      for (const opt of agentFilter.options) {
        if (opt.value === agentName) { found = true; break; }
      }
      if (!found) {
        const opt = document.createElement('option');
        opt.value = agentName;
        opt.textContent = agentName === '__unassigned__' ? 'Belum Ditugaskan' : agentName;
        agentFilter.appendChild(opt);
      }
      agentFilter.value = agentName;
      agentFilter.dispatchEvent(new Event('change'));
    }
  }, 200);
}

async function loadDashboardCharts() {
  const trends = await api.get('/analytics/trends', { days: currentDateRange });
  if (!trends) return;

  const dates = trends.map(t => t.date.substring(5)); // MM-DD
  const spend = trends.map(t => t.spend);
  const leads = trends.map(t => t.leads);

  // Trend Chart
  const ctxTrend = document.getElementById('chart-trend').getContext('2d');
  if (trendChart) trendChart.destroy();
  
  trendChart = new Chart(ctxTrend, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [
        {
          label: 'Spend (Rp)',
          data: spend,
          borderColor: '#667eea',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          yAxisID: 'y',
          fill: true,
          tension: 0.4
        },
        {
          label: 'Leads',
          data: leads,
          borderColor: '#10b981',
          yAxisID: 'y1',
          type: 'bar',
          barPercentage: 0.5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { type: 'linear', display: true, position: 'left', grid: { color: 'rgba(255,255,255,0.05)' } },
        y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
      }
    }
  });

  // Funnel Chart
  const funnel = await api.get('/analytics/funnel');
  const ctxFunnel = document.getElementById('chart-funnel').getContext('2d');
  if (funnelChart) funnelChart.destroy();

  if (funnel) {
    funnelChart = new Chart(ctxFunnel, {
      type: 'bar',
      data: {
        labels: ['New', 'Contacted', 'Qualified', 'Proposal', 'Won'],
        datasets: [{
          data: [funnel.new, funnel.contacted, funnel.qualified, funnel.proposal, funnel.won],
          backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899', '#10b981'],
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false } }, y: { grid: { display: false } } }
      }
    });
  }
}
