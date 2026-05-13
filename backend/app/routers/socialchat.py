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
        
        # --- PROCESS LEAD ---
        # 1. Check if lead exists
        lead = db.query(Lead).filter(Lead.phone_number == phone_number).first()
        
        if not lead:
            # Create new lead from SocialChat
            lead = Lead(
                full_name=contact_name,
                phone_number=phone_number,
                source="WhatsApp (SocialChat)",
                status="NEW",
                # Give a default score, can be adjusted by OpenClaw later
                ai_score=50,
                meta_data={"socialchat_raw": payload}
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
            logger.info(f"Created new lead from SocialChat: {lead.id}")
            
        # 2. Record Activity
        activity = LeadActivity(
            lead_id=lead.id,
            activity_type="WhatsApp Message",
            details={"message": message_text, "direction": "inbound"},
            ai_sentiment_score=None # To be processed by OpenClaw
        )
        db.add(activity)
        
        # 3. Update Lead timestamp
        lead.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"status": "success", "lead_id": lead.id}

    except Exception as e:
        logger.error(f"Error processing SocialChat webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
