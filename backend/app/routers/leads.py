"""
KGH Meta Ads — Leads Router
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from datetime import date, datetime, timedelta
from typing import Optional, List
import hmac, hashlib, json, os
import urllib.request

from app.database import get_db
from app.models.lead import Lead, LeadActivity, AutomationRule, AutomationLog, Notification
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadOut, LeadDetail, LeadStats,
    MetaLeadWebhookPayload, AutomationRuleCreate, AutomationRuleUpdate,
    AutomationRuleOut, AutomationLogOut, NotificationOut
)
from app.config import settings
from app.services.lead_scorer import score_lead

router = APIRouter(prefix="/api/leads", tags=["leads"])


# ─── Lead CRUD ────────────────────────────────────────────

@router.get("", response_model=List[LeadOut])
async def list_leads(
    status: Optional[str] = Query(None),
    score_label: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List leads with filtering, sorting, and pagination"""
    query = select(Lead).order_by(desc(Lead.created_at))

    if status:
        query = query.where(Lead.status == status.upper())
    if score_label:
        query = query.where(Lead.score_label == score_label.upper())
    if assigned_to:
        if assigned_to == "__unassigned__":
            query = query.where(
                (Lead.assigned_to.is_(None)) | 
                (Lead.assigned_to == "") | 
                (Lead.assigned_to == "Unassigned")
            )
        else:
            query = query.where(Lead.assigned_to == assigned_to)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            Lead.full_name.ilike(pattern) |
            Lead.phone.ilike(pattern) |
            Lead.email.ilike(pattern)
        )

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats", response_model=LeadStats)
async def get_lead_stats(db: AsyncSession = Depends(get_db)):
    """Get pipeline statistics"""
    today = date.today()
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)

    async def count_where(condition):
        result = await db.execute(select(func.count()).where(condition))
        return result.scalar() or 0

    total = await count_where(Lead.id > 0)

    return LeadStats(
        total=total,
        new=await count_where(Lead.status == "NEW"),
        contacted=await count_where(Lead.status == "CONTACTED"),
        qualified=await count_where(Lead.status == "QUALIFIED"),
        proposal=await count_where(Lead.status == "PROPOSAL"),
        won=await count_where(Lead.status == "WON"),
        lost=await count_where(Lead.status == "LOST"),
        hot=await count_where(Lead.score_label == "HOT"),
        warm=await count_where(Lead.score_label == "WARM"),
        cold=await count_where(Lead.score_label == "COLD"),
        today=await count_where(func.date(Lead.created_at) == today),
        this_week=await count_where(Lead.created_at >= week_start),
        this_month=await count_where(Lead.created_at >= month_start),
    )


@router.get("/agents/summary")
async def get_agents_summary(db: AsyncSession = Depends(get_db)):
    """Get agent breakdown with lead counts and score distribution for channel segregation"""
    # Get all distinct agents with counts
    result = await db.execute(
        select(
            Lead.assigned_to,
            func.count(Lead.id).label("total"),
            func.count().filter(Lead.score_label == "HOT").label("hot"),
            func.count().filter(Lead.score_label == "WARM").label("warm"),
            func.count().filter(Lead.score_label == "COLD").label("cold"),
        )
        .where(Lead.assigned_to.isnot(None))
        .where(Lead.assigned_to != "")
        .where(Lead.assigned_to != "Unassigned")
        .group_by(Lead.assigned_to)
        .order_by(desc("total"))
    )
    rows = result.all()

    agents = []
    for row in rows:
        agents.append({
            "name": row.assigned_to,
            "total": row.total,
            "hot": row.hot,
            "warm": row.warm,
            "cold": row.cold,
        })

    # Also get unassigned count
    unassigned_result = await db.execute(
        select(func.count(Lead.id)).where(
            (Lead.assigned_to.is_(None)) | (Lead.assigned_to == "") | (Lead.assigned_to == "Unassigned")
        )
    )
    unassigned = unassigned_result.scalar() or 0

    return {"agents": agents, "unassigned": unassigned}


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get lead detail with activity timeline"""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        await db.refresh(lead, ["activities"])
    except Exception:
        pass  # activities relation may not exist for SocialChat-sourced leads
    return lead


@router.get("/{lead_id}/messages")
async def get_lead_messages(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch complete conversation history for a lead from SocialChat"""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.phone:
        return {"messages": [], "error": "No phone number attached"}

    sc_key = os.environ.get("SOCIALCHAT_API_KEY", "MTI0NjExMzgxNl9TeWhLc2dDdUlUVGcwQTdWTkZpVg==")
    channel_id = "69f1c4458c09ad192d585af5"
    
    cf = lead.custom_fields or {}
    conv_id = cf.get("socialchat_conversation_id")
    
    # If we don't have conv_id, search by phone across all channels
    if not conv_id:
        url = f"https://api.socialchat.id/partner/conversation?limit=50&search={urllib.parse.quote(lead.phone)}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {sc_key}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                docs = data.get("docs", [])
                for doc in docs:
                    sender_id = doc.get("senderId", "")
                    if lead.phone in sender_id:
                        conv_id = doc.get("_id")
                        break
                if not conv_id and docs:
                    conv_id = docs[0].get("_id")
        except Exception as e:
            print("Error finding conv:", e)
            
        if conv_id:
            # Cache it
            cf["socialchat_conversation_id"] = conv_id
            lead.custom_fields = cf
            await db.commit()
            
    if not conv_id:
        # Look for another lead with the same phone that already has conv_id cached
        sibling_result = await db.execute(
            select(Lead).where(
                Lead.phone == lead.phone,
                Lead.id != lead.id,
                Lead.custom_fields.is_not(None)
            ).order_by(Lead.id)
        )
        for sibling in sibling_result.scalars().all():
            sibling_cf = sibling.custom_fields or {}
            sibling_conv = sibling_cf.get("socialchat_conversation_id")
            if sibling_conv:
                conv_id = sibling_conv
                # Cache it on this lead too
                cf["socialchat_conversation_id"] = conv_id
                lead.custom_fields = cf
                await db.commit()
                break

    if not conv_id:
        return {"messages": [], "error": "Conversation not found in SocialChat"}

    # Fetch messages
    msg_url = f"https://api.socialchat.id/partner/message/{conv_id}"
    req = urllib.request.Request(msg_url)
    req.add_header("Authorization", f"Bearer {sc_key}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            messages = data.get("messages", [])
            # Sort by sendAt ASC
            messages.sort(key=lambda x: x.get("sendAt", ""))
            return {"messages": messages}
    except Exception as e:
        return {"messages": [], "error": f"Failed to fetch messages: {str(e)}"}

@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Manually create a new lead"""
    lead = Lead(**payload.model_dump())
    # Auto-score
    score, label, reason = score_lead(lead)
    lead.score = score
    lead.score_label = label
    lead.score_reason = reason

    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Log activity
    activity = LeadActivity(
        lead_id=lead.id,
        action_type="LEAD_CREATED",
        description=f"Lead dibuat manual. Score: {label} ({score})",
        performed_by="dashboard"
    )
    db.add(activity)
    await db.commit()

    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update lead status, score, assignment, or notes"""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_status = lead.status
    update_data = payload.model_dump(exclude_none=True)

    for field, value in update_data.items():
        setattr(lead, field, value)

    # Track status changes
    if payload.status and payload.status != old_status:
        if payload.status == "CONTACTED":
            lead.contacted_at = datetime.utcnow()
        elif payload.status == "QUALIFIED":
            lead.qualified_at = datetime.utcnow()

        activity = LeadActivity(
            lead_id=lead.id,
            action_type="STATUS_CHANGE",
            description=f"Status berubah dari {old_status} → {payload.status}",
            performed_by="dashboard"
        )
        db.add(activity)

    await db.commit()
    await db.refresh(lead)
    return lead


# ─── Webhook: Meta Lead Ads → N8N pushes here ─────────────

@router.get("/webhook/meta")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge")
):
    """Meta webhook verification challenge"""
    if hub_mode == "subscribe" and hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/meta")
async def receive_meta_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive lead webhook from Meta (via N8N)"""
    body = await request.body()
    payload = json.loads(body)

    if payload.get("object") != "page":
        return {"status": "ignored"}

    leads_created = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "leadgen":
                continue
            value = change.get("value", {})

            # Check for duplicate
            existing = await db.execute(
                select(Lead).where(Lead.meta_lead_id == str(value.get("leadgen_id")))
            )
            if existing.scalar_one_or_none():
                continue

            lead = Lead(
                meta_lead_id=str(value.get("leadgen_id")),
                source="META_LEAD_ADS",
                custom_fields=value
            )
            score, label, reason = score_lead(lead)
            lead.score = score
            lead.score_label = label
            lead.score_reason = reason

            db.add(lead)
            leads_created += 1

    await db.commit()
    return {"status": "ok", "leads_created": leads_created}


# ─── Push from N8N (enriched lead data) ──────────────────

@router.post("/ingest", response_model=LeadOut, status_code=201)
async def ingest_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    """
    N8N calls this endpoint to push enriched lead data after fetching
    from Meta Graph API.
    """
    if payload.meta_lead_id:
        existing = await db.execute(
            select(Lead).where(Lead.meta_lead_id == payload.meta_lead_id)
        )
        if existing.scalar_one_or_none():
            return existing.scalar_one_or_none()

    lead = Lead(**payload.model_dump())
    score, label, reason = score_lead(lead)
    lead.score = score
    lead.score_label = label
    lead.score_reason = reason

    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead
