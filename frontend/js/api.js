/**
 * KGH Meta Ads — API Client
 * Automatically includes JWT token in all requests.
 * Redirects to login.html if token is missing or expired.
 */
const API_BASE = '/api';

const api = {
  _token() {
    return localStorage.getItem('kgh_token') || '';
  },

  _headers() {
    const t = this._token();
    return {
      'Content-Type': 'application/json',
      ...(t ? { 'Authorization': `Bearer ${t}` } : {})
    };
  },

  _handleUnauth(status) {
    if (status === 401 || status === 403) {
      localStorage.removeItem('kgh_token');
      localStorage.removeItem('kgh_username');
      window.location.href = '/login.html';
    }
  },

  async get(endpoint, params = {}) {
    try {
      const url = new URL(API_BASE + endpoint, window.location.origin);
      Object.entries(params).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') url.searchParams.append(k, v);
      });
      const res = await fetch(url, { headers: this._headers() });
      if (!res.ok) { this._handleUnauth(res.status); throw new Error(`API Error: ${res.status}`); }
      return await res.json();
    } catch (err) {
      console.error('API GET Error:', err);
      return null;
    }
  },

  async post(endpoint, data) {
    try {
      const res = await fetch(API_BASE + endpoint, {
        method: 'POST',
        headers: this._headers(),
        body: JSON.stringify(data)
      });
      if (!res.ok) { this._handleUnauth(res.status); throw new Error(`API Error: ${res.status}`); }
      return await res.json();
    } catch (err) {
      console.error('API POST Error:', err);
      return null;
    }
  },

  async patch(endpoint, data) {
    try {
      const res = await fetch(API_BASE + endpoint, {
        method: 'PATCH',
        headers: this._headers(),
        body: JSON.stringify(data)
      });
      if (!res.ok) { this._handleUnauth(res.status); throw new Error(`API Error: ${res.status}`); }
      return await res.json();
    } catch (err) {
      console.error('API PATCH Error:', err);
      return null;
    }
  },

  async delete(endpoint) {
    try {
      const res = await fetch(API_BASE + endpoint, {
        method: 'DELETE',
        headers: this._headers()
      });
      if (!res.ok) { this._handleUnauth(res.status); throw new Error(`API Error: ${res.status}`); }
      return await res.json();
    } catch (err) {
      console.error('API DELETE Error:', err);
      return null;
    }
  }
};
