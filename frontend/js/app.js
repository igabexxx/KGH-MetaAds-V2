/**
 * KGH Meta Ads — Main App Logic & SPA Router
 */

// Formatters
const formatCurrency = (val) => new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(val);
const formatNumber = (val) => new Intl.NumberFormat('id-ID').format(val);
const formatDate = (val) => new Date(val).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

// Global State
let currentDateRange = 30;

// SPA Router
function switchPage(pageId) {
  document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  
  const page = document.getElementById(`page-${pageId}`);
  const nav = document.getElementById(`nav-${pageId}`);
  
  if (page) page.classList.add('active');
  if (nav) nav.classList.add('active');

  const titleMap = {
    'dashboard': 'Dashboard',
    'campaigns': 'Campaigns',
    'leads': 'Lead Management',
    'analytics': 'Analytics',
    'automation': 'Automation Rules',
    'settings': 'Settings'
  };
  document.getElementById('page-title').textContent = titleMap[pageId] || 'KGH Ads';

  // Trigger page specific load
  if (window[`load${pageId.charAt(0).toUpperCase() + pageId.slice(1)}`]) {
    window[`load${pageId.charAt(0).toUpperCase() + pageId.slice(1)}`]();
  }
}

// Initializer
document.addEventListener('DOMContentLoaded', () => {
  // Navigation
  document.querySelectorAll('.nav-item').forEach(nav => {
    nav.addEventListener('click', (e) => {
      e.preventDefault();
      const pageId = nav.getAttribute('data-page');
      window.location.hash = pageId;
      switchPage(pageId);
      
      // Close mobile sidebar
      if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
      }
    });
  });

  // Handle Hash
  const hash = window.location.hash.replace('#', '') || 'dashboard';
  switchPage(hash);

  // Global Date Range
  const dateSelect = document.getElementById('date-range');
  if (dateSelect) {
    dateSelect.addEventListener('change', (e) => {
      currentDateRange = parseInt(e.target.value);
      const activePage = document.querySelector('.page.active').id.replace('page-', '');
      if (window[`load${activePage.charAt(0).toUpperCase() + activePage.slice(1)}`]) {
        window[`load${activePage.charAt(0).toUpperCase() + activePage.slice(1)}`]();
      }
    });
  }

  // Check system status
  checkSystemStatus();
});

async function checkSystemStatus() {
  const status = await api.get('/status');
  if (status) {
    document.getElementById('dot-api').style.background = 'var(--success)';
    document.getElementById('label-api').textContent = 'API Online';
    document.getElementById('dot-meta').style.background = status.meta_configured ? 'var(--success)' : 'var(--warning)';
    document.getElementById('label-meta').textContent = status.meta_configured ? 'Meta Active' : 'Meta Config Needed';
    
    // Fill settings page
    if (document.getElementById('s-backend')) document.getElementById('s-backend').textContent = 'Online';
    if (document.getElementById('info-llm')) document.getElementById('info-llm').textContent = status.llm_provider;
    if (document.getElementById('info-model')) document.getElementById('info-model').textContent = status.llm_model;
  }
}

/**
 * Navigate to Leads page with score filter pre-selected
 * Called from dashboard HOT/WARM/COLD pills
 */
function filterLeadsByScore(scoreLabel) {
  // Set score filter in leads page
  currentFilters = currentFilters || { status: '', score_label: '', search: '' };
  currentFilters.score_label = scoreLabel;
  currentFilters.status = '';
  currentFilters.search = '';
  currentPage = 1;

  // Navigate to leads page
  window.location.hash = 'leads';
  switchPage('leads');

  // Set the dropdown value after page switch
  setTimeout(() => {
    const scoreFilter = document.getElementById('lead-score-filter');
    if (scoreFilter) scoreFilter.value = scoreLabel;
    const statusFilter = document.getElementById('lead-status-filter');
    if (statusFilter) statusFilter.value = '';
    const searchInput = document.getElementById('lead-search');
    if (searchInput) searchInput.value = '';
  }, 100);
}
