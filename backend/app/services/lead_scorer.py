"""
KGH Meta Ads — LeadSense AI Scoring Engine v2
18-Dimension Lead Scoring menggunakan AI (LLM) untuk menganalisis percakapan.

Spesifikasi 18 dimensi dikirim sebagai system prompt ke AI.
AI menganalisis teks percakapan dan mengembalikan skor terstruktur.
"""
from typing import Tuple, Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import logging
import urllib.request
import os

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# AI SCORING SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════

SCORING_SYSTEM_PROMPT = """Kamu adalah LeadSense AI — mesin scoring lead properti Kayana Green Hills.
Tugasmu menganalisis percakapan WhatsApp antara lead (calon pembeli) dan agen sales, lalu memberikan skor integer berdasarkan 18 dimensi berikut.

═══════════════════════════════════════
CARA KERJA SCORING
═══════════════════════════════════════

Skor menentukan klasifikasi:
  HOT  = skor >= 90  → Siap Beli, prioritas utama
  WARM = skor 50-89  → Perlu Follow-up
  COLD = skor < 50   → Belum Minat, pantau saja

═══════════════════════════════════════
DIMENSI POSITIF (menambah skor)
═══════════════════════════════════════

[1] PESAN VOLUME — Jumlah pesan yang dikirim lead
    >=1 pesan → +15 | >=2 pesan → +15 (kumulatif) | >=5 pesan → +10 (kumulatif) | Max +40

[2] LAST SENDER — Siapa kirim pesan terakhir?
    Lead = +30 | Agent = +20 | System = 0

[3] MOFU (Middle of Funnel) — Kata tanya riset/minat awal
    +8 poin per keyword: info, detail, brosur, harga, cicilan, berapa, lokasi, maps, tipe, kamar, luas

[4] BOFU (Bottom of Funnel) — Kata sinyal siap transaksi
    +20 poin per keyword: survey/survei, datang/kunjung, jadwal, booking, dp, akad, kpr, bank, slip, gaji, cash

[5] URGENCY — Kebutuhan mendesak (+25 FLAT jika ada >=1)
    Keyword: segera, bulan ini, minggu ini, asap, urgent, secepatnya, akhir bulan, akhir tahun

[6] BUDGET READY — Kesiapan finansial (+30 FLAT jika ada >=1)
    Keyword: kpr sudah, kpr di, dp siap, dp ada, uang muka, budget saya, cicilan sekitar, mampu, sanggup, bisa kpr, sudah acc

[7] DIALOGUE DEPTH — Bolak-balik percakapan (turn/2)
    >=4 bolak-balik → +20 | >=2 bolak-balik → +10

[8] RECENCY — Kapan terakhir lead aktif?
    Hari ini → +20 | Kemarin → +10 | 2-3 hari → 0 | 4-7 hari → -10 | >7 hari → -20

[9] MESSAGE QUALITY — Panjang rata-rata pesan lead
    >=100 kata → +15 | >=50 kata → +10

[10] DECISION MAKER — Libatkan pengambil keputusan (+20 FLAT)
    Keyword: suami, istri, keluarga setuju, tanya dulu, izin tanya, diskusi dulu, minta pendapat, pasangan

[11] SPECIFIC UNIT — Tanya unit tertentu (+25 FLAT)
    Keyword: blok, kavling, nomor unit, type/tipe 36/45/54, masih ada unit, stok unit, unit tersedia

[12] LOCATION AFFINITY — Lokasi dekat (+15 FLAT)
    Keyword: deket/dekat kantor/sekolah/rumah, satu area, daerah sini, area kerja

[13] PRICE ACCEPTANCE — Sinyal penerimaan harga (+10 FLAT)
    Keyword: cicilan berapa, ada diskon, ada promo, bisa nego, harga bisa, beli sekarang

[14] SOCIAL PROOF / REFERRAL (+20 FLAT)
    Keyword: teman/rekan/saudara saya, direkomendasikan, dari teman/kenalan, referral, tetangga saya

[15] FAST REPLY — Lead balas agen <1 jam (+15)

═══════════════════════════════════════
DIMENSI NEGATIF (mengurangi skor)
═══════════════════════════════════════

[16] GHOST PENALTY — Pesan agen tak dibalas (dari akhir percakapan mundur)
    1 pesan → -5 | 2 pesan → -15 | 3-4 pesan → -30 | >=5 pesan → -45

[17] NEG KEYWORDS — Intensi negatif (-30 per hit, max -60)
    7 kategori: Penolakan langsung, Keberatan harga, Penundaan/keraguan, Ketidakmampuan hadir, Penolakan keluarga, Sudah beli di tempat lain, Ketidaksanggupan

[18] COMPETITOR — Bandingkan proyek lain (-10 FLAT)
    Keyword: dibanding, perumahan/proyek/developer/cluster lain

═══════════════════════════════════════
FILTER: ABAIKAN pesan auto-reply ini:
- "Hello! Can I get more info on this?"
- "Hallo boleh minta info detail nya Perumahan Kayana?"  
- "Halo! Bisakah saya mendapatkan info selengkapnya tentang ini?"

Filter agent: ABAIKAN lead jika nama agen prefix "DK" (tim demo internal)
Filter nomor: HANYA proses nomor format Indonesia /^62\\d{8,15}$/
═══════════════════════════════════════

SINYAL POSITIF — Gunakan emoji:
  MOFU: info→📋, detail→📄, brosur→📑, harga→💰, cicilan→💳, berapa→🔢, lokasi→📍, maps→🗺️, tipe→🏠, kamar→🛏️, luas→📐
  BOFU: survey→🔍, datang→🚗, jadwal→📅, booking→📝, dp→💵, akad→🤝, kpr→🏦, bank→🏦, gaji→💼, cash→💸
  Extra: Decision Maker→👨‍👩‍👧, Specific Unit→🏠, Location→📍, Price Accept→💵, Social Proof→👥, Fast Reply→⚡, Long Message→✍️

SINYAL NEGATIF (maks 3):
  NEG hits → 🚫 [keyword], Competitor → ⚔️, Ghost → ⏳/🔕/👻

ACTION LOGIC (prioritas):
1. Ghost >=5 → "⚠️ Lead tidak merespon — coba via channel lain atau re-engagement WA langsung."
2. Ghost >=3 → "📲 Kirim pesan ulang dengan pendekatan berbeda (promo/tanya kabar)."
3. Budget Ready → "🔥 Prioritas! Lead siap finansial — segera hubungi untuk closing."
4. Specific Unit → "Unit spesifik diminati — segera konfirmasi ketersediaan & jadwalkan visit."
5. BOFU → "Jadwalkan survey, siapkan info detail unit."
6. Decision Maker → "Libatkan decision maker — tawarkan sesi konsultasi keluarga."
7. MOFU → "Kirimkan brosur & pricelist."
8. NEG → "Re-engagement dengan promo atau cicilan ringan."
9. Default → "Follow up dengan info promo terbaru."

═══════════════════════════════════════
OUTPUT FORMAT — Kembalikan HANYA JSON valid (tanpa markdown, tanpa penjelasan):
{
  "score": <integer, min 0>,
  "temp": "HOT" | "WARM" | "COLD",
  "summary": "<deskripsi singkat status lead>",
  "posSignals": "<sinyal positif dengan emoji, dipisah koma>",
  "negStr": "<sinyal negatif, maks 3, dipisah koma>",
  "urgLabel": "<kata urgency terdeteksi atau kosong>",
  "bdgLabel": "<kata budget terdeteksi atau kosong>",
  "action": "<rekomendasi tindakan>",
  "reasons": "<breakdown skor per dimensi, dipisah ;>",
  "ghostCount": <integer>,
  "ghostLabel": "<label ghost atau kosong>",
  "bofuHits": <integer>,
  "mofuHits": <integer>,
  "negHits": <integer>,
  "msgCount": <total pesan dalam percakapan>,
  "leadMsgCount": <pesan non-auto dari lead>,
  "bf": <jumlah bolak-balik>,
  "daysDiff": <hari sejak terakhir aktif>,
  "recencyLabel": "<hari ini/kemarin/X hari lalu>"
}
"""


# ═══════════════════════════════════════════════════════════
# AI SCORING ENGINE
# ═══════════════════════════════════════════════════════════

def score_lead_ai(messages: List[Dict], conv_data: Dict,
                  prev_score: Optional[int] = None,
                  prev_temp: Optional[str] = None,
                  llm_api_key: str = "",
                  llm_model: str = "gpt-4o",
                  llm_provider: str = "openai",
                  llm_base_url: str = "") -> Dict[str, Any]:
    """
    Score a lead using AI analysis of conversation messages.
    
    Args:
        messages: List of message dicts from SocialChat
        conv_data: Conversation metadata
        prev_score: Previous score for delta calculation
        prev_temp: Previous temperature label
        llm_api_key: API key for the LLM provider
        llm_model: Model name
        llm_provider: "openai" | "gemini" | "anthropic"
        llm_base_url: Custom base URL (e.g. for OpenClaw/proxy)
    """
    # ── Build conversation transcript ───────────────────────
    contact_name = conv_data.get("senderName", "Unknown")
    phone = conv_data.get("senderId", "").split("@")[0] if conv_data.get("senderId") else ""
    agent = conv_data.get("agentBy", {}) or {}
    agent_name = agent.get("name", "Unassigned") if isinstance(agent, dict) else "Unassigned"
    created_at = conv_data.get("createdAt", "")

    transcript_lines = []
    for msg in messages:
        send_by = msg.get("sendBy", "system")
        text = (msg.get("text") or "").strip()
        send_at = msg.get("sendAt") or msg.get("createdAt") or ""
        sender_name = msg.get("senderName", "")

        if not text:
            msg_type = msg.get("type", "")
            if msg_type == "media":
                text = "[Media/Gambar]"
            elif msg_type == "document":
                text = "[Dokumen]"
            elif msg_type == "audio":
                text = "[Audio]"
            elif msg_type == "sticker":
                text = "[Sticker]"
            else:
                continue

        role_label = "LEAD" if send_by == "contact" else "AGENT" if send_by == "user" else "SYSTEM"
        timestamp = send_at[:16] if send_at else ""
        transcript_lines.append(f"[{timestamp}] {role_label} ({sender_name}): {text}")

    transcript = "\n".join(transcript_lines)

    if not transcript.strip():
        return _empty_result(contact_name, phone, agent_name, prev_score, prev_temp)

    # ── Build user prompt ───────────────────────────────────
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    user_prompt = f"""Analisis percakapan lead properti berikut dan berikan scoring.

INFO LEAD:
- Nama: {contact_name}
- Telepon: {phone}
- Agent: {agent_name}
- Tanggal mulai percakapan: {created_at}
- Waktu sekarang: {today_str}

TRANSKRIP PERCAKAPAN:
{transcript}

Berikan scoring JSON sesuai format yang diminta. HANYA kembalikan JSON, tanpa teks lain."""

    # ── Call AI ──────────────────────────────────────────────
    try:
        ai_response = _call_llm(
            system_prompt=SCORING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            api_key=llm_api_key,
            model=llm_model,
            provider=llm_provider,
            base_url=llm_base_url,
        )

        # Parse JSON from AI response
        result = _parse_ai_response(ai_response)
        if not result:
            logger.warning(f"Failed to parse AI response for {contact_name}, using fallback")
            return _empty_result(contact_name, phone, agent_name, prev_score, prev_temp)

    except Exception as e:
        logger.error(f"AI scoring error for {contact_name}: {e}")
        return _empty_result(contact_name, phone, agent_name, prev_score, prev_temp)

    # ── Enrich with metadata ────────────────────────────────
    result["contactName"] = contact_name
    result["contactPhone"] = phone
    result["agentName"] = agent_name

    # ── Delta calculation ───────────────────────────────────
    score = result.get("score", 0)
    temp = result.get("temp", "COLD")

    delta = None
    status_changed = False
    status_dir = "NEW"
    if prev_score is not None:
        delta = score - prev_score
        status_dir = "UP" if delta > 0 else "DOWN" if delta < 0 else "SAME"
        if prev_temp and prev_temp != temp:
            status_changed = True

    result["delta"] = delta
    result["prevScore"] = prev_score
    result["prevTemp"] = prev_temp
    result["statusChanged"] = status_changed
    result["statusDir"] = status_dir
    result["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return result


def _call_llm(system_prompt: str, user_prompt: str,
              api_key: str, model: str, provider: str,
              base_url: str = "") -> str:
    """Call the LLM API and return the response text."""

    if provider == "gemini":
        return _call_gemini(system_prompt, user_prompt, api_key, model)
    else:
        # OpenAI-compatible API (works with OpenAI, OpenClaw, Anthropic proxy, etc.)
        return _call_openai_compatible(system_prompt, user_prompt, api_key, model, base_url)


def _call_openai_compatible(system_prompt: str, user_prompt: str,
                            api_key: str, model: str,
                            base_url: str = "") -> str:
    """Call OpenAI-compatible API (OpenAI, OpenClaw, etc.)"""
    url = (base_url.rstrip("/") if base_url else "https://api.openai.com/v1") + "/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _call_gemini(system_prompt: str, user_prompt: str,
                 api_key: str, model: str) -> str:
    """Call Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2000,
            "responseMimeType": "application/json",
        },
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _parse_ai_response(response_text: str) -> Optional[Dict]:
    """Parse JSON from AI response, handling markdown code blocks."""
    text = response_text.strip()

    # Strip markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


def _empty_result(contact_name, phone, agent_name,
                  prev_score=None, prev_temp=None) -> Dict:
    """Return a minimal result when AI scoring fails."""
    return {
        "contactName": contact_name,
        "contactPhone": phone,
        "agentName": agent_name,
        "score": 0,
        "temp": "COLD",
        "delta": (0 - prev_score) if prev_score else None,
        "prevScore": prev_score,
        "prevTemp": prev_temp,
        "statusChanged": prev_temp is not None and prev_temp != "COLD",
        "statusDir": "NEW" if prev_score is None else "DOWN",
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "summary": "❄️ COLD (skor 0) | Tidak cukup data untuk analisis",
        "posSignals": "Tidak ada",
        "negStr": "Tidak ada",
        "urgLabel": "",
        "bdgLabel": "",
        "action": "Follow up dengan info promo terbaru.",
        "reasons": "AI scoring gagal atau tidak ada pesan",
        "ghostCount": 0,
        "ghostLabel": "",
        "bofuHits": 0,
        "mofuHits": 0,
        "negHits": 0,
        "msgCount": 0,
        "leadMsgCount": 0,
        "bf": 0,
        "daysDiff": 999,
        "recencyLabel": "N/A",
    }


# ═══════════════════════════════════════════════════════════
# LEGACY WRAPPER — backward compatibility with existing routes
# ═══════════════════════════════════════════════════════════

def score_lead(lead) -> Tuple[int, str, str]:
    """
    Legacy function for backward compatibility with existing routers.
    Scores based on Lead model data only (no AI, no conversation).
    Returns (score: int, label: str, reason: str)
    """
    score = 0
    reasons = []

    # Basic data completeness
    if lead.phone and len(str(lead.phone)) >= 8:
        score += 25
        if str(lead.phone).startswith(("08", "628", "+628", "62")):
            score += 10
            reasons.append("Nomor HP valid")

    if lead.email:
        score += 15
    if lead.full_name and len(str(lead.full_name)) > 2:
        score += 10

    # Quick keyword scan from custom_fields
    cf = lead.custom_fields or {}
    all_text = " ".join(str(v).lower() for v in cf.values() if v)

    for kw in ["survey", "booking", "dp", "kpr", "cash", "akad"]:
        if kw in all_text:
            score += 20
            reasons.append(f"BOFU: '{kw}'")
            break

    for kw in ["info", "harga", "cicilan", "tipe", "lokasi"]:
        if kw in all_text:
            score += 8
            reasons.append(f"MOFU: '{kw}'")
            break

    neg_keywords = ["tidak jadi", "batal", "mahal", "ga jadi", "nanti aja"]
    for kw in neg_keywords:
        if kw in all_text:
            score = max(0, score - 30)
            reasons.append(f"NEG: '{kw}'")
            break

    score = max(0, score)
    if score >= 90:
        label = "HOT"
    elif score >= 50:
        label = "WARM"
    else:
        label = "COLD"

    return score, label, "; ".join(reasons) if reasons else "Data minimal"
