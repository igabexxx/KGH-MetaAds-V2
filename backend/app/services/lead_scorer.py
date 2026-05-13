"""
KGH Meta Ads — Lead Scoring Service
Scores leads berdasarkan data yang tersedia dari Meta Lead Ads form.
"""
from typing import Tuple
from app.models.lead import Lead


# ─── Scoring Weights ──────────────────────────────────────
WEIGHTS = {
    "has_phone": 25,
    "has_email": 15,
    "has_name": 10,
    "phone_format_valid": 10,
    "budget_keyword_high": 20,   # from custom_fields
    "budget_keyword_med": 10,
    "timeline_urgent": 15,       # "segera", "bulan ini", etc.
    "location_match": 10,        # target area
    "unit_type_match": 10,       # tipe unit sesuai
}

HOT_THRESHOLD = 65
WARM_THRESHOLD = 35

BUDGET_HIGH_KEYWORDS = [
    "cash", "tunai", "kpr ready", "dp siap", "langsung", "serius",
    "beli", "inden", "ready", "deal", "fix"
]
BUDGET_MED_KEYWORDS = [
    "survey", "info", "tanya", "lihat", "detail", "brosur"
]
TIMELINE_URGENT_KEYWORDS = [
    "segera", "secepatnya", "bulan ini", "minggu ini", "asap",
    "cepat", "urgent", "1 bulan", "2 bulan"
]
NEGATIVE_KEYWORDS = [
    "tidak", "ga", "nggak", "belum bisa", "tidak jadi",
    "batal", "salah kirim", "iseng", "coba-coba"
]

VALID_AREA_KEYWORDS = [
    "bandung", "kab bandung", "soreang", "banjaran", "dayeuhkolot",
    "margahayu", "katapang", "bojongsoang"
]


def score_lead(lead: Lead) -> Tuple[int, str, str]:
    """
    Returns (score: int, label: str, reason: str)
    label: HOT | WARM | COLD
    """
    score = 0
    reasons = []

    # ─── Basic data completeness ──────────────────────────
    if lead.phone and len(lead.phone) >= 8:
        score += WEIGHTS["has_phone"]
        if lead.phone.startswith(("08", "628", "+628")):
            score += WEIGHTS["phone_format_valid"]
            reasons.append("Nomor HP valid")
    else:
        reasons.append("Tidak ada nomor HP")

    if lead.email:
        score += WEIGHTS["has_email"]

    if lead.full_name and len(lead.full_name) > 2:
        score += WEIGHTS["has_name"]

    # ─── Custom fields analysis ───────────────────────────
    cf = lead.custom_fields or {}
    all_text = " ".join(str(v).lower() for v in cf.values() if v)

    # Negative intent — hard penalty
    for kw in NEGATIVE_KEYWORDS:
        if kw in all_text:
            score = max(0, score - 30)
            reasons.append(f"Negatif intent: '{kw}'")
            break

    # Budget / readiness keywords
    for kw in BUDGET_HIGH_KEYWORDS:
        if kw in all_text:
            score += WEIGHTS["budget_keyword_high"]
            reasons.append(f"Keyword HOT: '{kw}'")
            break

    for kw in BUDGET_MED_KEYWORDS:
        if kw in all_text:
            score += WEIGHTS["budget_keyword_med"]
            reasons.append(f"Keyword WARM: '{kw}'")
            break

    # Timeline urgency
    for kw in TIMELINE_URGENT_KEYWORDS:
        if kw in all_text:
            score += WEIGHTS["timeline_urgent"]
            reasons.append(f"Timeline urgent: '{kw}'")
            break

    # Location match
    for area in VALID_AREA_KEYWORDS:
        if area in all_text:
            score += WEIGHTS["location_match"]
            reasons.append(f"Area match: '{area}'")
            break

    # Clamp score
    score = max(0, min(100, score))

    # Determine label
    if score >= HOT_THRESHOLD:
        label = "HOT"
    elif score >= WARM_THRESHOLD:
        label = "WARM"
    else:
        label = "COLD"

    reason_text = "; ".join(reasons) if reasons else "Data minimal"
    return score, label, reason_text
