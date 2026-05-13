"""
KGH Meta Ads — Pydantic Schemas: Leads
"""
from pydantic import BaseModel, EmailStr, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Any, Dict


# ─── Lead Activity ────────────────────────────────────────

class LeadActivityOut(BaseModel):
    id: int
    action_type: str
    description: Optional[str] = None
    performed_by: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime

    model_config = {"from_attributes": True}


# ─── Lead ─────────────────────────────────────────────────

class LeadBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    custom_fields: Dict[str, Any] = {}
    source: str = "META_LEAD_ADS"


class LeadCreate(LeadBase):
    meta_lead_id: Optional[str] = None
    form_id: Optional[int] = None
    campaign_id: Optional[int] = None
    ad_id: Optional[int] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[int] = None
    score_label: Optional[str] = None
    score_reason: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class LeadOut(LeadBase):
    id: int
    meta_lead_id: Optional[str] = None
    campaign_id: Optional[int] = None
    score: int
    score_label: str
    status: str
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    contacted_at: Optional[datetime] = None
    qualified_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LeadDetail(LeadOut):
    activities: List[LeadActivityOut] = []

    model_config = {"from_attributes": True}


# ─── Lead Stats ───────────────────────────────────────────

class LeadStats(BaseModel):
    total: int
    new: int
    contacted: int
    qualified: int
    proposal: int
    won: int
    lost: int
    hot: int
    warm: int
    cold: int
    today: int
    this_week: int
    this_month: int


# ─── Automation Rules ─────────────────────────────────────

class AutomationRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    conditions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    scope: str = "ALL"
    scope_ids: List[str] = []
    is_active: bool = True
    cooldown_minutes: int = 60


class AutomationRuleCreate(AutomationRuleBase):
    pass


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    cooldown_minutes: Optional[int] = None


class AutomationRuleOut(AutomationRuleBase):
    id: int
    last_triggered: Optional[datetime] = None
    trigger_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutomationLogOut(BaseModel):
    id: int
    rule_id: Optional[int] = None
    rule_name: Optional[str] = None
    action_taken: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Dict[str, Any] = {}
    status: str
    error_message: Optional[str] = None
    executed_at: datetime

    model_config = {"from_attributes": True}


# ─── Webhook Payload ──────────────────────────────────────

class MetaLeadWebhookEntry(BaseModel):
    id: str
    time: int
    changes: List[Dict[str, Any]]


class MetaLeadWebhookPayload(BaseModel):
    object: str
    entry: List[MetaLeadWebhookEntry]


# ─── Notifications ────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    channel: Optional[str] = None
    is_read: bool
    metadata: Dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}
