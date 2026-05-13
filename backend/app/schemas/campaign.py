"""
KGH Meta Ads — Pydantic Schemas: Campaigns
"""
from pydantic import BaseModel, field_validator
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List


# ─── Campaign ─────────────────────────────────────────────

class CampaignBase(BaseModel):
    meta_id: str
    name: str
    objective: Optional[str] = None
    status: str = "UNKNOWN"
    buying_type: Optional[str] = None
    daily_budget: Optional[Decimal] = None
    lifetime_budget: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignMetricsOut(BaseModel):
    id: int
    date: date
    impressions: int
    clicks: int
    spend: Decimal
    reach: int
    ctr: Decimal
    cpc: Decimal
    cpm: Decimal
    conversions: int
    cost_per_result: Decimal
    roas: Decimal

    model_config = {"from_attributes": True}


class CampaignOut(CampaignBase):
    id: int
    created_at: datetime
    updated_at: datetime
    latest_metrics: Optional[CampaignMetricsOut] = None

    model_config = {"from_attributes": True}


class CampaignDetail(CampaignOut):
    metrics: List[CampaignMetricsOut] = []

    model_config = {"from_attributes": True}


# ─── Analytics / Overview ─────────────────────────────────

class KPIOverview(BaseModel):
    total_spend: Decimal
    total_impressions: int
    total_clicks: int
    total_leads: int
    average_cpl: Decimal
    average_ctr: Decimal
    average_cpm: Decimal
    active_campaigns: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    date_from: date
    date_to: date


class TrendDataPoint(BaseModel):
    date: date
    spend: Decimal
    impressions: int
    clicks: int
    leads: int
    cpl: Decimal
    ctr: Decimal


class FunnelData(BaseModel):
    new: int
    contacted: int
    qualified: int
    proposal: int
    won: int
    lost: int
    conversion_rate: float


class CampaignCompare(BaseModel):
    campaign_id: int
    campaign_name: str
    spend: Decimal
    impressions: int
    clicks: int
    leads: int
    cpl: Decimal
    ctr: Decimal
    roas: Decimal
