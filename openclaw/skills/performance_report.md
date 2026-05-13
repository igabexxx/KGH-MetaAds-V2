---
name: performance_report
description: Skill untuk menganalisis performa dan memberikan rekomendasi optimasi iklan.
---

# Intent
User meminta analisis performa harian/mingguan atau alasan mengapa metrik tertentu (misal CPL) naik.

# Action
1. Ambil data tren dari `GET /api/analytics/trends`.
2. Lakukan perbandingan menggunakan `GET /api/analytics/campaigns/compare`.
3. LLM (Anda) harus menyimpulkan tren dan memberikan 2-3 rekomendasi konkrit (misal: "Matikan campaign A karena CPL > 150rb", atau "Scale up campaign B karena ROAS tinggi").

# Response
Gunakan markdown. Berikan paragraf ringkasan, daftar poin-poin anomali/temuan, lalu diakhiri dengan Rekomendasi Tindakan.
