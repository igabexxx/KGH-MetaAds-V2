"""
KGH Meta Ads — SQLAlchemy Models: Leads
"""
from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP,
    ForeignKey, Boolean, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class LeadForm(Base):
    __tablename__ = "lead_forms"

    id              = Column(Integer, primary_key=True, index=True)
    meta_form_id    = Column(String(100), unique=True, nullable=False)
    name            = Column(String(255))
    campaign_id     = Column(Integer, ForeignKey("campaigns.id"))
    questions       = Column(JSONB, default=list)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    campaign    = relationship("Campaign", back_populates="lead_forms")
    leads       = relationship("Lead", back_populates="lead_form")


class Lead(Base):
    __tablename__ = "leads"

    id              = Column(Integer, primary_key=True, index=True)
    meta_lead_id    = Column(String(100), unique=True)
    form_id         = Column(Integer, ForeignKey("lead_forms.id"))
    campaign_id     = Column(Integer, ForeignKey("campaigns.id"))
    ad_id           = Column(Integer, ForeignKey("ads.id"))

    # Contact Info
    full_name       = Column(String(255))
    email           = Column(String(255))
    phone           = Column(String(50), index=True)

    # Custom form fields
    custom_fields   = Column(JSONB, default=dict)

    # Scoring
    score           = Column(Integer, default=0)
    score_label     = Column(String(10), default="COLD", index=True)  # HOT, WARM, COLD
    score_reason    = Column(Text)

    # Status & Assignment
    status          = Column(String(20), default="NEW", index=True)
    assigned_to     = Column(String(100))
    notes           = Column(Text)

    # Source tracking
    source          = Column(String(50), default="META_LEAD_ADS")
    utm_source      = Column(String(100))
    utm_medium      = Column(String(100))
    utm_campaign    = Column(String(100))

    # Timestamps
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at      = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    contacted_at    = Column(TIMESTAMP(timezone=True))
    qualified_at    = Column(TIMESTAMP(timezone=True))

    # Relationships
    lead_form   = relationship("LeadForm", back_populates="leads")
    campaign    = relationship("Campaign", back_populates="leads")
    ad          = relationship("Ad", back_populates="leads")
    activities  = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan",
                               order_by="LeadActivity.timestamp.desc()")


class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id              = Column(Integer, primary_key=True, index=True)
    lead_id         = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    action_type     = Column(String(50), nullable=False)
    description     = Column(Text)
    performed_by    = Column(String(100), default="system")
    meta_data       = Column("metadata", JSONB, default=dict)
    timestamp       = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="activities")


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(255), nullable=False)
    description     = Column(Text)
    trigger_type    = Column(String(50), nullable=False)
    conditions      = Column(JSONB, nullable=False, default=list)
    actions         = Column(JSONB, nullable=False, default=list)
    scope           = Column(String(20), default="ALL")
    scope_ids       = Column(JSONB, default=list)
    is_active       = Column(Boolean, default=True)
    last_triggered  = Column(TIMESTAMP(timezone=True))
    trigger_count   = Column(Integer, default=0)
    cooldown_minutes = Column(Integer, default=60)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id              = Column(Integer, primary_key=True, index=True)
    rule_id         = Column(Integer, ForeignKey("automation_rules.id", ondelete="SET NULL"))
    rule_name       = Column(String(255))
    action_taken    = Column(String(100))
    target_type     = Column(String(50))
    target_id       = Column(String(100))
    details         = Column(JSONB, default=dict)
    status          = Column(String(20), default="SUCCESS")
    error_message   = Column(Text)
    executed_at     = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    message     = Column(Text, nullable=False)
    type        = Column(String(30), default="INFO")
    channel     = Column(String(30))
    is_read     = Column(Boolean, default=False, index=True)
    meta_data   = Column("metadata", JSONB, default=dict)
    created_at  = Column(TIMESTAMP(timezone=True), server_default=func.now())
