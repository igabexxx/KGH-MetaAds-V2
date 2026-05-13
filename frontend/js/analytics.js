/**
 * KGH Meta Ads — Analytics Page Logic
 */

let spendDailyChart = null;
let ctrChart = null;
let funnelAnalyticsChart = null;

async function loadAnalytics() {
  const trends = await api.get('/analytics/trends', { days: currentDateRange });
  if (!trends) return;

  const dates = trends.map(t => t.date.substring(5));
  const spend = trends.map(t => t.spend);
  const ctr = trends.map(t => t.ctr);

  // 1. Spend Daily Chart
  const ctxSpend = document.getElementById('chart-spend-daily').getContext('2d');
  if (spendDailyChart) spendDailyChart.destroy();
  spendDailyChart = new Chart(ctxSpend, {
    type: 'bar',
    data: {
      labels: dates,
      datasets: [{
        label: 'Spend (Rp)',
        data: spend,
        backgroundColor: '#667eea',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' } }
      }
    }
  });

  // 2. CTR Chart
  const ctxCtr = document.getElementById('chart-ctr').getContext('2d');
  if (ctrChart) ctrChart.destroy();
  ctrChart = new Chart(ctxCtr, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        label: 'CTR (%)',
        data: ctr,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        fill: true,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' } }
      }
    }
  });

  // 3. Funnel Chart
  const funnel = await api.get('/analytics/funnel');
  if (funnel) {
    const ctxFunnel = document.getElementById('chart-funnel-analytics').getContext('2d');
    if (funnelAnalyticsChart) funnelAnalyticsChart.destroy();
    funnelAnalyticsChart = new Chart(ctxFunnel, {
      type: 'doughnut',
      data: {
        labels: ['New', 'Contacted', 'Qualified', 'Proposal', 'Won', 'Lost'],
        datasets: [{
          data: [funnel.new, funnel.contacted, funnel.qualified, funnel.proposal, funnel.won, funnel.lost],
          backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b', '#ec4899', '#10b981', '#ef4444'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { color: '#e2e8f0' } }
        },
        cutout: '70%'
      }
    });
  }

  // 4. Compare Table
  const compare = await api.get('/analytics/campaigns/compare', { days: currentDateRange });
  const tbody = document.getElementById('tbody-compare');
  
  if (compare && compare.length > 0) {
    tbody.innerHTML = compare.map(c => `
      <tr>
        <td><strong>${c.campaign_name}</strong></td>
        <td>${formatCurrency(c.spend)}</td>
        <td>${formatNumber(c.impressions)}</td>
        <td>${formatNumber(c.clicks)}</td>
        <td>${c.ctr.toFixed(2)}%</td>
        <td><strong>${c.leads}</strong></td>
        <td>${formatCurrency(c.cpl)}</td>
        <td><span style="color:${c.roas >= 1 ? 'var(--success)' : 'var(--danger)'}">${c.roas.toFixed(2)}x</span></td>
      </tr>
    `).join('');
  } else {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center">Data tidak tersedia</td></tr>`;
  }
}
