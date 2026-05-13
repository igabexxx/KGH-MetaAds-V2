"""
SocialChat → KGH Lead Sync + AI Scoring (Fast Mode)
Uses lastMessage from conversation metadata for AI scoring.
No individual message fetching needed — fast and reliable.
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
# CONFIG
# ═══════════════════════════════════════════════════════════

SC_KEY = os.environ.get("SOCIALCHAT_API_KEY", "MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg==")
SC_BASE = os.environ.get("SOCIALCHAT_BASE_URL", "https://api.socialchat.id/partner")
LLM_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
KGH_API = os.environ.get("KGH_API", "http://192.168.101.226:8005")
DAYS = int(os.environ.get("SYNC_DAYS_BACK", "45"))
PHONE_RE = re.compile(r"^62\d{8,15}$")

# ═══════════════════════════════════════════════════════════
# SCORING PROMPT
# ═══════════════════════════════════════════════════════════

SCORING_PROMPT = """Kamu adalah LeadSense AI — mesin scoring lead properti Kayana Green Hills.
Analisis data lead WhatsApp berikut dan berikan scoring berdasarkan 18 dimensi.

KLASIFIKASI: HOT (>=90) | WARM (50-89) | COLD (<50). Skor min 0, max tak terbatas.

DIMENSI POSITIF:
[1] VOLUME: hitung dari msgCount. >=1 +15, >=2 +15, >=5 +10 (max +40)
[2] LAST SENDER: Lead terakhir kirim +30, Agent +20
[3] MOFU: +8/keyword (info,detail,brosur,harga,cicilan,berapa,lokasi,maps,tipe,kamar,luas)
[4] BOFU: +20/keyword (survey/survei,datang/kunjung,jadwal,booking,dp,akad,kpr,bank,slip,gaji,cash)
[5] URGENCY: +25 flat (segera,bulan ini,minggu ini,asap,urgent,secepatnya)
[6] BUDGET: +30 flat (kpr sudah/di,dp siap/ada,uang muka,mampu,sanggup,bisa kpr,sudah acc)
[7] DEPTH: estimasi dari context. >=4 bolak-balik +20, >=2 +10
[8] RECENCY: hitung dari lastActiveDate vs sekarang. Hari ini +20, kemarin +10, 2-3 hari 0, 4-7 -10, >7 -20
[9] MSG QUALITY: estimasi dari pesan. avg >=100 kata +15, >=50 +10
[10] DECISION MAKER: +20 flat (suami,istri,keluarga setuju,pasangan)
[11] SPECIFIC UNIT: +25 flat (blok,kavling,type/tipe 36/45/54,masih ada unit)
[12] LOCATION: +15 flat (deket/dekat kantor/sekolah/rumah,satu area)
[13] PRICE ACCEPT: +10 flat (cicilan berapa,ada diskon/promo,bisa nego)
[14] REFERRAL: +20 flat (teman/rekan/saudara saya,dari teman/kenalan)
[15] FAST REPLY: +15 jika konteks menunjukkan respon cepat

DIMENSI NEGATIF:
[16] GHOST: estimasi dari lastSender & unread. 1 -5, 2 -15, 3-4 -30, >=5 -45
[17] NEG: -30/hit max -60 (tolak,mahal,tunda,ga bisa,keluarga tolak,sudah beli)
[18] COMPETITOR: -10 flat (dibanding,perumahan/proyek lain)

ABAIKAN auto-reply: "Hello! Can I get more info...", "Hallo boleh minta info detail nya Perumahan Kayana?"
Skor minimum = 0.

ACTION (prioritas): Ghost>=5→re-engagement, Budget→closing, SpecificUnit→konfirmasi, BOFU→survey, DecisionMaker→konsultasi keluarga, MOFU→brosur, NEG→promo, Default→follow up.

Emoji sinyal: MOFU: info→📋,harga→💰,cicilan→💳,lokasi→📍,tipe→🏠 | BOFU: survey→🔍,datang→🚗,booking→📝,dp→💵,kpr→🏦,cash→💸 | Extra: DecisionMaker→👨‍👩‍👧,SpecificUnit→🏠,Referral→👥,FastReply→⚡

KEMBALIKAN HANYA JSON (tanpa markdown/penjelasan):
{"score":0,"temp":"COLD","summary":"","posSignals":"","negStr":"","urgLabel":"","bdgLabel":"","action":"","reasons":"","ghostCount":0,"ghostLabel":"","bofuHits":0,"mofuHits":0,"negHits":0,"msgCount":0,"leadMsgCount":0,"bf":0,"daysDiff":0,"recencyLabel":""}"""


# ═══════════════════════════════════════════════════════════
# FUNCTIONS
# ═══════════════════════════════════════════════════════════

def sc_get(path):
    url = f"{SC_BASE}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {SC_KEY}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_conversations():
    from_d = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT00:00:00.000Z")
    to_d = datetime.now(timezone.utc).strftime("%Y-%m-%dT23:59:59.999Z")
    all_c = []
    page = 1
    while True:
        data = sc_get(f"conversation?page={page}&limit=50&fromDate={from_d}&toDate={to_d}")
        docs = data.get("docs", [])
        all_c.extend(docs)
        tp = data.get("totalPages", 1)
        print(f"  Page {page}/{tp} — {len(docs)} convs", flush=True)
        if page >= tp:
            break
        page += 1
    return all_c


def call_ai(lead_info):
    """Score a lead using OpenAI."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SCORING_PROMPT},
            {"role": "user", "content": lead_info},
        ],
        "temperature": 0.1,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {LLM_KEY}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"].strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return json.loads(text)


def push_to_kgh(name, phone, agent, status, score_data=None):
    cf = {}
    notes = ""
    if score_data:
        cf = {
            "ai_score": score_data.get("score", 0),
            "ai_temp": score_data.get("temp", "COLD"),
            "ai_summary": score_data.get("summary", ""),
            "ai_signals_pos": score_data.get("posSignals", ""),
            "ai_signals_neg": score_data.get("negStr", ""),
            "ai_action": score_data.get("action", ""),
            "ai_reasons": score_data.get("reasons", ""),
            "ai_ghost": score_data.get("ghostLabel", ""),
            "ai_recency": score_data.get("recencyLabel", ""),
            "ai_bf": score_data.get("bf", 0),
            "ai_msg_count": score_data.get("msgCount", 0),
            "ai_scored_at": datetime.now(timezone.utc).isoformat(),
        }
        notes = score_data.get("summary", "")

    payload = json.dumps({
        "full_name": name,
        "phone": phone,
        "source": "WhatsApp (SocialChat)",
        "status": status,
        "assigned_to": agent if agent != "Unassigned" else None,
        "notes": notes[:500] if notes else None,
        "custom_fields": cf,
    }).encode("utf-8")

    req = urllib.request.Request(f"{KGH_API}/api/leads", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10):
            return "created"
    except urllib.error.HTTPError:
        return "skipped"
    except Exception:
        return "error"


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60, flush=True)
    print("  LeadSense AI Sync — SocialChat → KGH", flush=True)
    print("=" * 60, flush=True)
    print(f"  Model: OpenAI/{LLM_MODEL}", flush=True)
    print(f"  Days: {DAYS}", flush=True)

    # 1. Fetch conversations
    print(f"\n[1/3] Fetching conversations...", flush=True)
    convs = fetch_conversations()
    print(f"  Total: {len(convs)}", flush=True)

    # 2. Filter & Score
    print(f"\n[2/3] AI Scoring...", flush=True)
    results = []
    skip_dk = skip_phone = skip_group = 0
    ai_ok = ai_err = 0
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for i, conv in enumerate(convs):
        if conv.get("isGroup"):
            skip_group += 1
            continue

        agent = conv.get("agentBy", {}) or {}
        agent_name = agent.get("name", "") if isinstance(agent, dict) else ""
        if agent_name.startswith("DK"):
            skip_dk += 1
            continue

        sender_id = conv.get("senderId", "")
        phone = sender_id.split("@")[0] if "@" in sender_id else ""
        if not PHONE_RE.match(phone):
            skip_phone += 1
            continue

        name = conv.get("senderName", "Unknown")
        last_msg = conv.get("lastMessage", {}) or {}
        last_text = last_msg.get("text", "") if isinstance(last_msg, dict) else ""
        last_sender = last_msg.get("sendBy", "") if isinstance(last_msg, dict) else ""
        last_at = last_msg.get("sendAt", "") if isinstance(last_msg, dict) else ""
        created = conv.get("createdAt", "")
        updated = conv.get("updatedAt", "")
        unread = conv.get("unreadCount", 0)

        # Build lead info for AI
        lead_info = f"""LEAD: {name}
HP: {phone}
Agent: {agent_name}
Percakapan dimulai: {created}
Terakhir update: {updated}
Waktu sekarang: {now_str}
Unread count: {unread}
Last message sender: {last_sender} (contact=lead, user=agent)
Last message: {last_text}
Last message time: {last_at}

Berikan scoring JSON."""

        # AI Score
        score_data = None
        if LLM_KEY:
            try:
                score_data = call_ai(lead_info)
                if score_data and isinstance(score_data, dict):
                    ai_ok += 1
                    t = score_data.get("temp", "?")
                    s = score_data.get("score", 0)
                    act = score_data.get("action", "")[:45]
                    print(f"  {ai_ok:3d}. {name[:22]:22s} → {t:4s} ({s:3d}) | {act}", flush=True)
                else:
                    ai_err += 1
                time.sleep(0.3)
            except Exception as e:
                ai_err += 1
                if ai_err <= 5:
                    print(f"  ERR: {name}: {str(e)[:60]}", flush=True)
                time.sleep(1)

        status = score_data.get("temp", "NEW") if score_data else "NEW"
        results.append({
            "name": name, "phone": phone, "agent": agent_name,
            "status": status, "score": score_data,
        })

    print(f"\n  Scored: {ai_ok}, Errors: {ai_err}", flush=True)
    print(f"  Skipped: DK={skip_dk}, phone={skip_phone}, group={skip_group}", flush=True)

    # 3. Push to KGH
    print(f"\n[3/3] Pushing {len(results)} leads to KGH...", flush=True)
    cr = sk = er = 0
    for r in results:
        st = push_to_kgh(r["name"], r["phone"], r["agent"], r["status"], r["score"])
        if st == "created":
            cr += 1
        elif st == "skipped":
            sk += 1
        else:
            er += 1

    # Save backup
    backup = [{"name": r["name"], "phone": r["phone"], "agent": r["agent"],
               "status": r["status"], "ai": r["score"]} for r in results]
    with open("socialchat_leads_scored.json", "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2, default=str)

    # Summary
    hot = sum(1 for r in results if r["status"] == "HOT")
    warm = sum(1 for r in results if r["status"] == "WARM")
    cold = sum(1 for r in results if r["status"] == "COLD")

    print("\n" + "=" * 60, flush=True)
    print("  SYNC COMPLETE", flush=True)
    print("=" * 60, flush=True)
    print(f"  Total leads  : {len(results)}", flush=True)
    print(f"  🔥 HOT       : {hot}", flush=True)
    print(f"  🟡 WARM      : {warm}", flush=True)
    print(f"  ❄️ COLD      : {cold}", flush=True)
    print(f"  DB created   : {cr}", flush=True)
    print(f"  DB skipped   : {sk}", flush=True)
    print(f"  DB errors    : {er}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
