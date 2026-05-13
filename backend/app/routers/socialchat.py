from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.lead import Lead, LeadActivity
import logging
from datetime import datetime
import json
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# Verify Token if SocialChat uses one, or use simple authentication
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "your_webhook_verify_token")

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Endpoint for webhook verification (often required by platforms like Meta or generic webhooks).
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == WEBHOOK_VERIFY_TOKEN:
            logger.info("SocialChat Webhook verified!")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Forbidden")
    
    return {"status": "ok", "message": "SocialChat webhook endpoint is ready"}

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Endpoint to receive incoming leads or messages from SocialChat.
    Since we don't have the exact payload schema yet, we will accept any JSON,
    log it, and attempt to extract standard fields (name, phone, message).
    """
    try:
        payload = await request.json()
        logger.info(f"Received SocialChat Webhook: {json.dumps(payload)}")
        
        # --- DYNAMIC EXTRACTION ---
        # Note: This extraction logic should be adjusted once the exact SocialChat payload is known.
        # Common WhatsApp API / CRM payload structures:
        
        # Try to find contact info
        contact_name = "Unknown WhatsApp User"
        phone_number = None
        message_text = "Incoming WhatsApp Message"
        
        # Scenario 1: Standard generic structure
        if "contact" in payload:
            contact_name = payload["contact"].get("name", contact_name)
            phone_number = payload["contact"].get("phone", phone_number)
            
        # Scenario 2: Flat structure
        if "name" in payload:
            contact_name = payload["name"]
        if "phone" in payload or "phone_number" in payload:
            phone_number = payload.get("phone", payload.get("phone_number"))
            
        # Scenario 3: Message content
        if "message" in payload:
            if isinstance(payload["message"], dict):
                message_text = payload["message"].get("text", message_text)
            else:
                message_text = str(payload["message"])

        # If we couldn't find a phone number, we can't properly track it as a lead yet
        if not phone_number:
            # Maybe it's nested deep, for now just log it
            return {"status": "success", "message": "Payload logged but no phone number found"}
            
        # Ensure phone format (basic)
        phone_number = str(phone_number).replace("+", "").replace("-", "").replace(" ", "")
        
        from sqlalchemy import select
        # 1. Check if lead exists
        result = await db.execute(select(Lead).filter(Lead.phone == phone_number))
        lead = result.scalars().first()
        
        if not lead:
            # Create new lead from SocialChat
            lead = Lead(
                full_name=contact_name,
                phone=phone_number,
                source="WhatsApp (SocialChat)",
                status="NEW",
                # Give a default score, can be adjusted by OpenClaw later
                score=50,
                custom_fields={"socialchat_raw": payload}
            )
            db.add(lead)
            await db.commit()
            await db.refresh(lead)
            logger.info(f"Created new lead from SocialChat: {lead.id}")
            
        # 2. Record Activity
        activity = LeadActivity(
            lead_id=lead.id,
            action_type="MESSAGE_RECEIVED",
            description=f"Received WhatsApp Message via SocialChat",
            performed_by="system",
            meta_data={"message": message_text, "direction": "inbound"}
        )
        db.add(activity)
        
        # 3. Update Lead timestamp
        lead.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {"status": "success", "lead_id": lead.id}

    except Exception as e:
        logger.error(f"Error processing SocialChat webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ═══════════════════════════════════════════════════════════
# AI SCORING ENDPOINT — Receives scoring results from n8n
# ═══════════════════════════════════════════════════════════

@router.post("/scoring/bulk")
async def receive_ai_scoring(request: Request, db: Session = Depends(get_db)):
    """
    Receives AI scoring results from n8n LeadSense workflow.
    Updates existing leads or creates new ones with AI analysis data.

    Expected payload:
    {
      "leads": [
        {
          "contactName": "...",
          "contactPhone": "62xxx",
          "agentName": "...",
          "score": 85,
          "temp": "WARM",
          "summary": "...",
          "posSignals": "...",
          "negStr": "...",
          "action": "...",
          "reasons": "...",
          "delta": 10,
          "prevScore": 75,
          "statusDir": "UP",
          "ghostLabel": "",
          "recencyLabel": "hari ini",
          "daysDiff": 0,
          "msgCount": 15,
          "bf": 4,
          ... (other scoring fields)
        }
      ]
    }
    """
    try:
        payload = await request.json()
        leads_data = payload.get("leads", [])

        if not leads_data:
            return {"status": "error", "message": "No leads data provided"}

        from sqlalchemy import select

        created = 0
        updated = 0
        errors = 0

        for item in leads_data:
            try:
                phone = str(item.get("contactPhone", "")).strip()
                if not phone:
                    errors += 1
                    continue

                name = item.get("contactName", "Unknown")
                agent = item.get("agentName", "Unassigned")
                score = item.get("score", 0)
                temp = item.get("temp", "COLD")

                # Build custom_fields with AI scoring data
                ai_data = {
                    "ai_score": score,
                    "ai_temp": temp,
                    "ai_summary": item.get("summary", ""),
                    "ai_signals_pos": item.get("posSignals", ""),
                    "ai_signals_neg": item.get("negStr", ""),
                    "ai_action": item.get("action", ""),
                    "ai_reasons": item.get("reasons", ""),
                    "ai_delta": item.get("delta"),
                    "ai_prev_score": item.get("prevScore"),
                    "ai_prev_temp": item.get("prevTemp"),
                    "ai_status_dir": item.get("statusDir", "NEW"),
                    "ai_status_changed": item.get("statusChanged", False),
                    "ai_ghost_label": item.get("ghostLabel", ""),
                    "ai_recency": item.get("recencyLabel", ""),
                    "ai_days_diff": item.get("daysDiff", 999),
                    "ai_msg_count": item.get("msgCount", 0),
                    "ai_bf": item.get("bf", 0),
                    "ai_urg_label": item.get("urgLabel", ""),
                    "ai_bdg_label": item.get("bdgLabel", ""),
                    "ai_bofu_hits": item.get("bofuHits", 0),
                    "ai_mofu_hits": item.get("mofuHits", 0),
                    "ai_neg_hits": item.get("negHits", 0),
                    "ai_lead_msg_count": item.get("leadMsgCount", 0),
                    "ai_scored_at": datetime.utcnow().isoformat(),
                }

                # Build notes
                notes_parts = []
                if item.get("summary"):
                    notes_parts.append(item["summary"])
                if item.get("action"):
                    notes_parts.append(f"Action: {item['action']}")
                notes = " | ".join(notes_parts) if notes_parts else None

                # Check if lead exists by phone
                result = await db.execute(select(Lead).filter(Lead.phone == phone))
                lead = result.scalars().first()

                if lead:
                    # Update existing lead with AI scoring
                    lead.score = score
                    lead.status = temp
                    lead.assigned_to = agent if agent != "Unassigned" else lead.assigned_to
                    lead.notes = notes
                    # Merge AI data into existing custom_fields
                    existing_cf = lead.custom_fields or {}
                    existing_cf.update(ai_data)
                    lead.custom_fields = existing_cf
                    lead.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    # Create new lead
                    lead = Lead(
                        full_name=name,
                        phone=phone,
                        source="WhatsApp (SocialChat)",
                        status=temp,
                        score=score,
                        assigned_to=agent if agent != "Unassigned" else None,
                        notes=notes,
                        custom_fields=ai_data,
                    )
                    db.add(lead)
                    created += 1

                # Record scoring activity
                activity = LeadActivity(
                    lead_id=lead.id if lead.id else None,
                    action_type="AI_SCORING",
                    description=f"LeadSense AI: {temp} (score {score})",
                    performed_by="leadsense-ai",
                    meta_data=ai_data,
                )
                db.add(activity)

            except Exception as e:
                errors += 1
                logger.error(f"Error processing lead {item.get('contactName', '?')}: {e}")

        await db.commit()

        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "errors": errors,
            "total": len(leads_data),
        }

    except Exception as e:
        logger.error(f"Error in AI scoring bulk endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoring/summary")
async def get_scoring_summary(db: Session = Depends(get_db)):
    """
    Returns a summary of AI scoring data for the dashboard.
    """
    from sqlalchemy import select, func

    try:
        # Total leads with AI scoring
        result = await db.execute(select(func.count(Lead.id)))
        total = result.scalar() or 0

        # Count by temperature
        hot_result = await db.execute(
            select(func.count(Lead.id)).filter(Lead.status == "HOT")
        )
        hot = hot_result.scalar() or 0

        warm_result = await db.execute(
            select(func.count(Lead.id)).filter(Lead.status == "WARM")
        )
        warm = warm_result.scalar() or 0

        cold_result = await db.execute(
            select(func.count(Lead.id)).filter(Lead.status == "COLD")
        )
        cold = cold_result.scalar() or 0

        # Get top 10 HOT leads
        top_hot = await db.execute(
            select(Lead)
            .filter(Lead.status == "HOT")
            .order_by(Lead.score.desc())
            .limit(10)
        )
        hot_leads = [
            {
                "id": l.id,
                "name": l.full_name,
                "phone": l.phone,
                "score": l.score,
                "agent": l.assigned_to,
                "ai_summary": (l.custom_fields or {}).get("ai_summary", ""),
                "ai_action": (l.custom_fields or {}).get("ai_action", ""),
                "ai_signals_pos": (l.custom_fields or {}).get("ai_signals_pos", ""),
            }
            for l in top_hot.scalars().all()
        ]

        return {
            "total": total,
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "new": total - hot - warm - cold,
            "topHot": hot_leads,
        }

    except Exception as e:
        logger.error(f"Error getting scoring summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
