/**
 * KGH Meta Ads — API Client
 */
const API_BASE = '/api';

const api = {
  async get(endpoint, params = {}) {
    try {
      const url = new URL(API_BASE + endpoint, window.location.origin);
      Object.entries(params).forEach(([k, v]) => {
        if (v !== null && v !== undefined && v !== '') url.searchParams.append(k, v);
      });
      const res = await fetch(url);
      if (!res.ok) throw new Error(`API Error: ${res.status}`);
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error(`API Error: ${res.status}`);
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error(`API Error: ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('API PATCH Error:', err);
      return null;
    }
  },

  async delete(endpoint) {
    try {
      const res = await fetch(API_BASE + endpoint, { method: 'DELETE' });
      if (!res.ok) throw new Error(`API Error: ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('API DELETE Error:', err);
      return null;
    }
  }
};
