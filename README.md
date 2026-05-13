# KGH Meta Ads Automation & Lead Management

Sistem end-to-end untuk manajemen Meta Ads dan Leads Property Kayana Green Hills, memadukan **FastAPI**, **N8N**, **OpenClaw AI**, dan **PostgreSQL**.

## Architecture Components

1. **Backend API (FastAPI)**: Menyediakan REST API, schema database, webhook endpoints, dan scoring leads secara lokal.
2. **N8N**: Mengorkestrasi workflow (sync data dari Meta API, menerima webhook, trigger notifikasi).
3. **OpenClaw AI**: Agent AI (menggunakan GPT-4o / Ollama) untuk query laporan dan trigger N8N.
4. **PostgreSQL**: Database utama untuk metrics campaign, lead data, dan automation logs.
5. **Frontend (Vanilla JS/CSS)**: Dashboard SPA premium (Dark mode) dengan Chart.js.

## 🚀 Deployment Instruction via Portainer

Sistem ini didesain untuk dijalankan via Docker Compose.

**Informasi Environment Anda:**
- **Portainer URL**: `https://192.168.101.226:9443/`
- **Portainer API Token**: `ptr_hPzUizSxcX3DK4M6ZGoiX0Si2PZLQgqrHTGv3mVhkdc=`

### Langkah Deploy:

1. Login ke Portainer di alamat di atas.
2. Masuk ke environment Anda (biasanya `local`).
3. Pilih **Stacks** -> **Add stack**.
4. Beri nama stack: `kgh-metads`.
5. Anda bisa menggunakan metode **Web editor** dan paste isi file `docker-compose.yml` dari repository ini, ATAU **Repository** jika ini terhubung ke Git.
6. Pada bagian **Environment variables**, Anda wajib mengisi variabel berikut:
   - `DB_PASSWORD` (password database)
   - `META_APP_ID`, `META_APP_SECRET`, `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`
   - `N8N_PASSWORD`
   - `LLM_API_KEY` (jika pakai OpenAI/Claude)
   - `MESSAGING_BOT_TOKEN` (Telegram Bot token)
7. Klik **Deploy the stack**.

> **Note:** Backend FastAPI akan berjalan di port `8000`, N8N di `5678`, dan OpenClaw di `3100`.

## ⚙️ N8N Setup

Setelah stack berjalan:
1. Buka N8N di `http://<SERVER_IP>:5678`.
2. Login menggunakan user/password yang diset.
3. Import workflow yang ada di folder `n8n/workflows/`.
4. Buat credential **PostgreSQL** di N8N:
   - Host: `postgres`
   - Database: `kgh_metads`
   - User: `kgh`
   - Password: `<sesuai .env>`
5. Aktifkan (Activate) workflow `01_lead_capture` dan `02_data_sync`.

## 🌐 Akses Dashboard

Dashboard dapat diakses via: `http://<SERVER_IP>:8000/`

Fitur Dashboard:
- KPI Overview
- Trend Charts (Spend & Leads)
- Campaign Management
- Lead Kanban/Table & Status Pipeline
- AI Analytics

## Support / Issues
Bila menemukan error CORS atau Webhook, pastikan `CORS_ORIGINS` di environment dan N8N webhook public URL tersetting dengan benar (via ngrok/Cloudflare Tunnel jika Meta membutuhkan HTTPS).
