---
name: lead_management
description: Skill untuk memonitor, mencari, dan memperbarui status leads.
---

# Intent
User ingin melihat lead baru, mencari lead spesifik, atau update status lead ke CONTACTED/QUALIFIED.

# Action
Query endpoint backend FastAPI:
- Mencari lead: `GET /api/leads?search={nama}`
- Update status: `PATCH /api/leads/{id}` dengan payload status.

# Response
Berikan detail lead yang ditemukan beserta score-nya (HOT/WARM/COLD). Konfirmasi jika status berhasil diupdate.
