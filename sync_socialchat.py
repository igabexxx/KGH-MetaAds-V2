"""
SocialChat → KGH Lead Sync + AI Scoring
Strategi hybrid:
1. Pull conversations dari SocialChat Partner API
2. Pull messages per conversation (jika available)
3. Kirim ke AI untuk scoring 18 dimensi
4. Fallback: import lead data tanpa scoring jika messages tidak tersedia

Sinkronisasi AI scoring dilakukan oleh n8n workflow yang sudah berjalan
(SocialChat LEADS AI Report - Daily) dan diteruskan ke KGH via API.
"""
import urllib.request
import json
import sys
import io
import os
import re
import time
from datetime import datetime, timedelta, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

SOCIALCHAT_API_KEY = os.environ.get("SOCIALCHAT_API_KEY", "MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg==")
SOCIALCHAT_BASE = os.environ.get("SOCIALCHAT_BASE_URL", "https://api.socialchat.id/partner")

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")

KGH_API = os.environ.get("KGH_API", "http://192.168.101.226:8005")
DAYS_BACK = int(os.environ.get("SYNC_DAYS_BACK", "90"))
PHONE_RE = re.compile(r"^62\d{8,15}$")

AUTO_REPLIES = [
    "hello! can i get more info on this?",
    "hallo boleh minta info detail nya perumahan kayana?",
    "halo! bisakah saya mendapatkan info selengkapnya tentang ini?",
]

# ═══════════════════════════════════════════════════════════
# AI SCORING SYSTEM PROMPT (18 dimensions)
# ═══════════════════════════════════════════════════════════

SCORING_PROMPT = """Kamu adalah LeadSense AI — mesin scoring lead properti Kayana Green Hills.
Analisis percakapan WhatsApp berikut dan berikan scoring berdasarkan 18 dimensi.

KLASIFIKASI: HOT (>=90) | WARM (50-89) | COLD (<50)

DIMENSI POSITIF:
[1] VOLUME: >=1 msg +15, >=2 +15, >=5 +10 (max +40)
[2] LAST SENDER: Lead +30, Agent +20
[3] MOFU: +8/keyword (info,detail,brosur,harga,cicilan,berapa,lokasi,maps,tipe,kamar,luas)
[4] BOFU: +20/keyword (survey/survei,datang/kunjung,jadwal,booking,dp,akad,kpr,bank,slip,gaji,cash)
[5] URGENCY: +25 flat (segera,bulan ini,minggu ini,asap,urgent,secepatnya,akhir bulan/tahun)
[6] BUDGET: +30 flat (kpr sudah/di,dp siap/ada,uang muka,budget saya,mampu,sanggup,bisa kpr,sudah acc)
[7] DEPTH: >=4 bolak-balik +20, >=2 +10
[8] RECENCY: hari ini +20, kemarin +10, 2-3 hari 0, 4-7 hari -10, >7 hari -20
[9] MSG QUALITY: avg >=100 kata +15, >=50 +10
[10] DECISION MAKER: +20 flat (suami,istri,keluarga setuju,tanya dulu,pasangan)
[11] SPECIFIC UNIT: +25 flat (blok,kavling,type/tipe 36/45/54,masih ada unit)
[12] LOCATION: +15 flat (deket/dekat kantor/sekolah/rumah,satu area,area kerja)
[13] PRICE ACCEPT: +10 flat (cicilan berapa,ada diskon/promo,bisa nego,beli sekarang)
[14] REFERRAL: +20 flat (teman/rekan/saudara saya,dari teman/kenalan,referral)
[15] FAST REPLY: +15 (lead balas <1 jam)

DIMENSI NEGATIF:
[16] GHOST: 1 msg -5, 2 msg -15, 3-4 msg -30, >=5 msg -45
[17] NEG: -30/hit max -60 (tolak,mahal,tunda,ga bisa,keluarga tolak,sudah beli)
[18] COMPETITOR: -10 flat (dibanding,perumahan/proyek/developer lain)

ABAIKAN auto-reply: "Hello! Can I get more info...", "Hallo boleh minta info detail nya..."
Skor minimum = 0.

ACTION (prioritas):
1. Ghost>=5 → "⚠️ Lead tidak merespon — coba channel lain"
2. Ghost>=3 → "📲 Kirim pesan ulang pendekatan berbeda"
3. Budget → "🔥 Prioritas! Segera closing"
4. Specific Unit → "Konfirmasi ketersediaan & jadwalkan visit"
5. BOFU → "Jadwalkan survey"
6. Decision Maker → "Tawarkan konsultasi keluarga"
7. MOFU → "Kirim brosur & pricelist"
8. NEG → "Re-engagement promo/cicilan ringan"
9. Default → "Follow up info promo terbaru"

KEMBALIKAN HANYA JSON (tanpa markdown):
{"score":int,"temp":"HOT|WARM|COLD","summary":"...","posSignals":"...","negStr":"...","urgLabel":"","bdgLabel":"","action":"...","reasons":"...","ghostCount":int,"ghostLabel":"","bofuHits":int,"mofuHits":int,"negHits":int,"msgCount":int,"leadMsgCount":int,"bf":int,"daysDiff":int,"recencyLabel":"..."}"""


# ═══════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════

def sc_get(path):
    url = f"{SOCIALCHAT_BASE}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {SOCIALCHAT_API_KEY}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_conversations(days_back=90):
    from_d = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00.000Z")
    to_d = datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59.999Z")
    all_convs = []
    page = 1
    while True:
        data = sc_get(f"conversation?page={page}&limit=50&fromDate={from_d}&toDate={to_d}")
        docs = data.get("docs", [])
        all_convs.extend(docs)
        total_pages = data.get("totalPages", 1)
        print(f"  Page {page}/{total_pages} — {len(docs)} conversations")
        if page >= total_pages:
            break
        page += 1
    return all_convs


def fetch_messages(conv_id):
    """Fetch messages for a conversation (no query params, like n8n does)."""
    try:
        data = sc_get(f"message/{conv_id}")
        return data.get("docs", [])
    except Exception as e:
        return []


def call_ai(transcript, contact_name, phone, agent_name, created_at):
    """Call LLM to score a lead conversation."""
    if not LLM_API_KEY:
        return None

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    user_prompt = f"""Analisis percakapan lead berikut:

LEAD: {contact_name} | HP: {phone} | Agent: {agent_name} | Mulai: {created_at} | Sekarang: {now_str}

TRANSKRIP:
{transcript}

Berikan scoring JSON sesuai format."""

    if LLM_PROVIDER == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent?key={LLM_API_KEY}"
        payload = {
            "systemInstruction": {"parts": [{"text": SCORING_PROMPT}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000, "responseMimeType": "application/json"},
        }
    else:
        base = (LLM_BASE_URL.rstrip("/") if LLM_BASE_URL else "https://api.openai.com/v1")
        url = f"{base}/chat/completions"
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": SCORING_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
        }

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, method="POST")
    req.add_header("Content-Type", "application/json")
    if LLM_PROVIDER != "gemini":
        req.add_header("Authorization", f"Bearer {LLM_API_KEY}")

    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())

    if LLM_PROVIDER == "gemini":
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        text = result["choices"][0]["message"]["content"]

    # Parse JSON
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return json.loads(text)


def build_transcript(messages, conv_sender_id):
    """Build a readable transcript from messages."""
    lines = []
    for m in messages:
        text = (m.get("text") or "").strip()
        if not text:
            msg_type = m.get("type", "")
            if msg_type:
                text = f"[{msg_type}]"
            else:
                continue

        sender_id = m.get("senderId", m.get("originalSenderId", ""))
        send_at = (m.get("sendAt") or m.get("createdAt") or "")[:16]
        sender_name = m.get("senderName", "")

        # Determine role
        if sender_id == conv_sender_id:
            role = "LEAD"
        elif "system" in sender_name.lower() or "sistem" in text.lower()[:20]:
            role = "SYSTEM"
        else:
            role = "AGENT"

        lines.append(f"[{send_at}] {role} ({sender_name}): {text}")

    return "\n".join(lines)


def push_to_kgh(lead, score=None):
    """Push lead + AI scoring to KGH database."""
    notes = []
    if lead.get("lastMessage"):
        notes.append(f"Last: {lead['lastMessage'][:150]}")

    cf = {
        "socialchat_id": lead.get("conversationId", ""),
        "socialchat_updated": lead.get("updatedAt", ""),
    }

    if score:
        cf["ai_score"] = score.get("score", 0)
        cf["ai_temp"] = score.get("temp", "COLD")
        cf["ai_summary"] = score.get("summary", "")
        cf["ai_signals_pos"] = score.get("posSignals", "")
        cf["ai_signals_neg"] = score.get("negStr", "")
        cf["ai_action"] = score.get("action", "")
        cf["ai_reasons"] = score.get("reasons", "")
        cf["ai_ghost"] = score.get("ghostLabel", "")
        cf["ai_recency"] = score.get("recencyLabel", "")
        cf["ai_scored_at"] = datetime.now(timezone.utc).isoformat()
        notes.append(f"AI: {score.get('temp','?')} ({score.get('score',0)})")

    payload = json.dumps({
        "full_name": lead.get("name", "Unknown"),
        "phone": lead.get("phone", ""),
        "source": "WhatsApp (SocialChat)",
        "status": score.get("temp", "NEW") if score else "NEW",
        "assigned_to": lead.get("agent") if lead.get("agent") != "Unassigned" else None,
        "notes": " | ".join(notes) if notes else None,
        "custom_fields": cf,
    }).encode("utf-8")

    req = urllib.request.Request(f"{KGH_API}/api/leads", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10):
            return "created"
    except urllib.error.HTTPError as e:
        if "409" in str(e.code):
            return "skipped"
        return f"error:{e.code}"
    except Exception as e:
        return f"error:{e}"


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("  SocialChat → KGH Lead Sync + AI Scoring")
    print("=" * 65)

    ai_ok = bool(LLM_API_KEY)
    print(f"\n  AI Scoring: {'ON (' + LLM_PROVIDER + '/' + LLM_MODEL + ')' if ai_ok else 'OFF (no LLM_API_KEY)'}")
    print(f"  Days back:  {DAYS_BACK}")

    # ── 1. Pull conversations ──────────────────────────────
    print(f"\n[1/4] Fetching conversations...")
    convs = fetch_conversations(DAYS_BACK)
    print(f"  Total: {len(convs)}")

    # ── 2. Extract leads + messages ────────────────────────
    print("\n[2/4] Extracting leads & fetching messages...")
    leads = []
    skip = {"dk": 0, "phone": 0, "group": 0}

    for i, conv in enumerate(convs):
        if conv.get("isGroup"):
            skip["group"] += 1
            continue

        agent = conv.get("agentBy", {}) or {}
        agent_name = agent.get("name", "") if isinstance(agent, dict) else ""
        if agent_name.startswith("DK"):
            skip["dk"] += 1
            continue

        sender_id = conv.get("senderId", "")
        phone = sender_id.split("@")[0] if "@" in sender_id else ""
        if not PHONE_RE.match(phone):
            skip["phone"] += 1
            continue

        # Fetch messages
        messages = fetch_messages(conv["_id"])

        # Build transcript
        transcript = ""
        if messages:
            transcript = build_transcript(messages, sender_id)

        last_msg = conv.get("lastMessage", {}) or {}
        last_text = last_msg.get("text", "") if isinstance(last_msg, dict) else ""

        leads.append({
            "name": conv.get("senderName", "Unknown"),
            "phone": phone,
            "agent": agent_name,
            "createdAt": conv.get("createdAt", ""),
            "updatedAt": conv.get("updatedAt", ""),
            "lastMessage": last_text,
            "conversationId": conv["_id"],
            "transcript": transcript,
            "msg_count": len(messages),
            "conv": conv,
        })

        if (i + 1) % 50 == 0:
            print(f"  ... processed {i+1}/{len(convs)}")

    print(f"  Qualified leads: {len(leads)}")
    for k, v in skip.items():
        if v:
            print(f"    skip_{k}: {v}")

    # ── 3. AI Scoring ──────────────────────────────────────
    print(f"\n[3/4] AI Scoring...")
    ai_ok_count = 0
    ai_err = 0

    for i, lead in enumerate(leads):
        score = None

        if ai_ok and lead["transcript"]:
            try:
                score = call_ai(
                    lead["transcript"],
                    lead["name"], lead["phone"],
                    lead["agent"], lead["createdAt"],
                )
                if score and score.get("score", 0) >= 0:
                    ai_ok_count += 1
                    t = score.get("temp", "?")
                    s = score.get("score", 0)
                    act = score.get("action", "")[:50]
                    print(f"  {i+1:3d}. {lead['name'][:22]:22s} → {t:4s} ({s:3d}) | {act}")
                time.sleep(0.5)  # rate limit
            except Exception as e:
                ai_err += 1
                if ai_err <= 5:
                    print(f"  AI err: {lead['name']}: {str(e)[:80]}")
        elif ai_ok and not lead["transcript"]:
            # No messages available — use lastMessage as minimal transcript
            if lead["lastMessage"]:
                try:
                    mini_transcript = f"[LEAD]: {lead['lastMessage']}"
                    score = call_ai(
                        mini_transcript,
                        lead["name"], lead["phone"],
                        lead["agent"], lead["createdAt"],
                    )
                    if score:
                        ai_ok_count += 1
                        t = score.get("temp", "?")
                        s = score.get("score", 0)
                        print(f"  {i+1:3d}. {lead['name'][:22]:22s} → {t:4s} ({s:3d}) [minimal]")
                    time.sleep(0.5)
                except Exception as e:
                    ai_err += 1

        lead["score"] = score

    if ai_ok:
        print(f"\n  AI scored: {ai_ok_count}, errors: {ai_err}")

    # ── 4. Push to KGH ─────────────────────────────────────
    print(f"\n[4/4] Pushing {len(leads)} leads to KGH...")
    res = {"created": 0, "skipped": 0, "errors": 0}

    for lead in leads:
        status = push_to_kgh(lead, lead.get("score"))
        if status == "created":
            res["created"] += 1
        elif status == "skipped":
            res["skipped"] += 1
        else:
            res["errors"] += 1

    # Save backup
    backup = []
    for lead in leads:
        entry = {k: v for k, v in lead.items() if k not in ("conv", "transcript")}
        backup.append(entry)
    with open("socialchat_leads_scored.json", "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2, default=str)

    # Summary
    print("\n" + "=" * 65)
    print("  SYNC COMPLETE")
    print("=" * 65)
    print(f"  Conversations : {len(convs)}")
    print(f"  Leads         : {len(leads)}")
    print(f"  AI scored     : {ai_ok_count}")
    print(f"  DB created    : {res['created']}")
    print(f"  DB skipped    : {res['skipped']}")
    print(f"  Errors        : {res['errors']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
