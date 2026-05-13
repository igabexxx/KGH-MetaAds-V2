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
    tbody.innerHTML = leads.map(l => `
      <tr>
        <td>${l.full_name || '-'}</td>
        <td>${l.phone || '-'}</td>
        <td><span class="status-badge ${l.score_label.toLowerCase()}">${l.score_label}</span></td>
        <td><span class="status-badge ${l.status.toLowerCase()}">${l.status}</span></td>
        <td>${formatDate(l.created_at)}</td>
      </tr>
    `).join('');
  } else {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center">Belum ada data leads</td></tr>`;
  }
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
