---
name: campaign_control
description: Skill untuk memicu action pada campaign (pause, ubah budget) melalui N8N.
---

# Intent
User meminta untuk mematikan (pause) campaign tertentu atau menyesuaikan budget.

# Action
Trigger N8N webhook untuk campaign automation. Saat ini bisa memanggil `POST /api/campaigns/sync` jika butuh sinkronisasi data instan.

# Response
Konfirmasi bahwa action telah diproses oleh sistem orchestrator (N8N).
