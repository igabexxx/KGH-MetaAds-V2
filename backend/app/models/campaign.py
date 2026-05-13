"""
KGH Meta Ads — SQLAlchemy Models: Campaigns
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Date,
    TIMESTAMP, ForeignKey, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id              = Column(Integer, primary_key=True, index=True)
    meta_id         = Column(String(50), unique=True, nullable=False, index=True)
    name            = Column(String(255), nullable=False)
    objective       = Column(String(100))
    status          = Column(String(20), default="UNKNOWN")
    buying_type     = Column(String(50))
    daily_budget    = Column(Numeric(15, 2))
    lifetime_budget = Column(Numeric(15, 2))
    start_date      = Column(Date)
    end_date        = Column(Date)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    ad_sets     = relationship("AdSet", back_populates="campaign", cascade="all, delete-orphan")
    metrics     = relationship("CampaignMetrics", back_populates="campaign", cascade="all, delete-orphan")
    leads       = relationship("Lead", back_populates="campaign")
    lead_forms  = relationship("LeadForm", back_populates="campaign")


class AdSet(Base):
    __tablename__ = "ad_sets"

    id                  = Column(Integer, primary_key=True, index=True)
    meta_id             = Column(String(50), unique=True, nullable=False, index=True)
    campaign_id         = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"))
    name                = Column(String(255), nullable=False)
    status              = Column(String(20), default="UNKNOWN")
    daily_budget        = Column(Numeric(15, 2))
    lifetime_budget     = Column(Numeric(15, 2))
    targeting_summary   = Column(String)
    optimization_goal   = Column(String(100))
    billing_event       = Column(String(100))
    bid_amount          = Column(Numeric(15, 2))
    created_at          = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at          = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    campaign    = relationship("Campaign", back_populates="ad_sets")
    ads         = relationship("Ad", back_populates="ad_set", cascade="all, delete-orphan")
    metrics     = relationship("AdSetMetrics", back_populates="ad_set", cascade="all, delete-orphan")


class Ad(Base):
    __tablename__ = "ads"

    id              = Column(Integer, primary_key=True, index=True)
    meta_id         = Column(String(50), unique=True, nullable=False, index=True)
    adset_id        = Column(Integer, ForeignKey("ad_sets.id", ondelete="CASCADE"))
    name            = Column(String(255), nullable=False)
    status          = Column(String(20), default="UNKNOWN")
    creative_type   = Column(String(50))
    preview_url     = Column(String)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at      = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    ad_set  = relationship("AdSet", back_populates="ads")
    leads   = relationship("Lead", back_populates="ad")


class CampaignMetrics(Base):
    __tablename__ = "campaign_metrics"

    id              = Column(Integer, primary_key=True, index=True)
    campaign_id     = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"))
    date            = Column(Date, nullable=False, index=True)
    impressions     = Column(Integer, default=0)
    clicks          = Column(Integer, default=0)
    spend           = Column(Numeric(15, 2), default=0)
    reach           = Column(Integer, default=0)
    frequency       = Column(Numeric(8, 4), default=0)
    ctr             = Column(Numeric(8, 4), default=0)
    cpc             = Column(Numeric(15, 4), default=0)
    cpm             = Column(Numeric(15, 4), default=0)
    cpp             = Column(Numeric(15, 4), default=0)
    conversions     = Column(Integer, default=0)
    cost_per_result = Column(Numeric(15, 4), default=0)
    roas            = Column(Numeric(10, 4), default=0)
    video_views     = Column(Integer, default=0)
    link_clicks     = Column(Integer, default=0)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="metrics")


class AdSetMetrics(Base):
    __tablename__ = "adset_metrics"

    id              = Column(Integer, primary_key=True, index=True)
    adset_id        = Column(Integer, ForeignKey("ad_sets.id", ondelete="CASCADE"))
    date            = Column(Date, nullable=False)
    impressions     = Column(Integer, default=0)
    clicks          = Column(Integer, default=0)
    spend           = Column(Numeric(15, 2), default=0)
    reach           = Column(Integer, default=0)
    ctr             = Column(Numeric(8, 4), default=0)
    cpc             = Column(Numeric(15, 4), default=0)
    cpm             = Column(Numeric(15, 4), default=0)
    conversions     = Column(Integer, default=0)
    cost_per_result = Column(Numeric(15, 4), default=0)
    created_at      = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    ad_set = relationship("AdSet", back_populates="metrics")
