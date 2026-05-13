"""
KGH Meta Ads — Analytics Router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Optional

from app.database import get_db
from app.models.campaign import Campaign, CampaignMetrics
from app.models.lead import Lead
from app.schemas.campaign import KPIOverview, TrendDataPoint, FunnelData, CampaignCompare

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=KPIOverview)
async def get_overview(
    days: int = Query(30, description="Lookback period in days"),
    db: AsyncSession = Depends(get_db)
):
    """KPI summary for dashboard overview cards"""
    date_from = date.today() - timedelta(days=days)
    date_to = date.today()

    # Aggregate campaign metrics
    metrics_query = select(
        func.coalesce(func.sum(CampaignMetrics.spend), 0).label("total_spend"),
        func.coalesce(func.sum(CampaignMetrics.impressions), 0).label("total_impressions"),
        func.coalesce(func.sum(CampaignMetrics.clicks), 0).label("total_clicks"),
        func.coalesce(func.avg(CampaignMetrics.ctr), 0).label("average_ctr"),
        func.coalesce(func.avg(CampaignMetrics.cpm), 0).label("average_cpm"),
    ).where(
        CampaignMetrics.date >= date_from,
        CampaignMetrics.date <= date_to
    )
    metrics_result = await db.execute(metrics_query)
    metrics = metrics_result.one()

    # Count leads
    lead_query = select(func.count()).where(Lead.created_at >= date_from)
    total_leads = (await db.execute(lead_query)).scalar() or 0

    hot_leads = (await db.execute(select(func.count()).where(Lead.score_label == "HOT"))).scalar() or 0
    warm_leads = (await db.execute(select(func.count()).where(Lead.score_label == "WARM"))).scalar() or 0
    cold_leads = (await db.execute(select(func.count()).where(Lead.score_label == "COLD"))).scalar() or 0

    # Active campaigns
    active_campaigns = (await db.execute(
        select(func.count()).where(Campaign.status == "ACTIVE")
    )).scalar() or 0

    total_spend = Decimal(str(metrics.total_spend))
    average_cpl = (total_spend / total_leads) if total_leads > 0 else Decimal("0")

    return KPIOverview(
        total_spend=total_spend,
        total_impressions=int(metrics.total_impressions),
        total_clicks=int(metrics.total_clicks),
        total_leads=total_leads,
        average_cpl=average_cpl,
        average_ctr=Decimal(str(metrics.average_ctr)),
        average_cpm=Decimal(str(metrics.average_cpm)),
        active_campaigns=active_campaigns,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        date_from=date_from,
        date_to=date_to
    )


@router.get("/trends")
async def get_trends(
    days: int = Query(30),
    db: AsyncSession = Depends(get_db)
):
    """Daily time-series data for trend charts"""
    date_from = date.today() - timedelta(days=days)

    metrics_query = select(
        CampaignMetrics.date,
        func.sum(CampaignMetrics.spend).label("spend"),
        func.sum(CampaignMetrics.impressions).label("impressions"),
        func.sum(CampaignMetrics.clicks).label("clicks"),
        func.avg(CampaignMetrics.ctr).label("ctr"),
    ).where(
        CampaignMetrics.date >= date_from
    ).group_by(CampaignMetrics.date).order_by(CampaignMetrics.date)

    metrics_result = await db.execute(metrics_query)
    rows = metrics_result.all()

    # Get leads by date
    leads_query = select(
        func.date(Lead.created_at).label("date"),
        func.count().label("leads")
    ).where(Lead.created_at >= date_from).group_by(func.date(Lead.created_at))

    leads_result = await db.execute(leads_query)
    leads_by_date = {row.date: row.leads for row in leads_result.all()}

    output = []
    for row in rows:
        leads = leads_by_date.get(row.date, 0)
        spend = Decimal(str(row.spend or 0))
        cpl = (spend / leads) if leads > 0 else Decimal("0")
        output.append({
            "date": str(row.date),
            "spend": float(spend),
            "impressions": int(row.impressions or 0),
            "clicks": int(row.clicks or 0),
            "leads": leads,
            "cpl": float(cpl),
            "ctr": float(row.ctr or 0),
        })

    return output


@router.get("/funnel")
async def get_funnel(db: AsyncSession = Depends(get_db)):
    """Lead pipeline funnel data"""
    async def count(status: str):
        result = await db.execute(select(func.count()).where(Lead.status == status))
        return result.scalar() or 0

    new = await count("NEW")
    contacted = await count("CONTACTED")
    qualified = await count("QUALIFIED")
    proposal = await count("PROPOSAL")
    won = await count("WON")
    lost = await count("LOST")
    total = new + contacted + qualified + proposal + won + lost

    return {
        "new": new,
        "contacted": contacted,
        "qualified": qualified,
        "proposal": proposal,
        "won": won,
        "lost": lost,
        "conversion_rate": round((won / total * 100) if total > 0 else 0, 2)
    }


@router.get("/campaigns/compare")
async def compare_campaigns(
    ids: Optional[str] = Query(None, description="Comma-separated campaign IDs"),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db)
):
    """Side-by-side campaign performance comparison"""
    date_from = date.today() - timedelta(days=days)

    query = select(
        Campaign.id,
        Campaign.name,
        func.sum(CampaignMetrics.spend).label("spend"),
        func.sum(CampaignMetrics.impressions).label("impressions"),
        func.sum(CampaignMetrics.clicks).label("clicks"),
        func.avg(CampaignMetrics.ctr).label("ctr"),
        func.avg(CampaignMetrics.roas).label("roas"),
    ).join(CampaignMetrics, CampaignMetrics.campaign_id == Campaign.id
    ).where(CampaignMetrics.date >= date_from
    ).group_by(Campaign.id, Campaign.name)

    if ids:
        id_list = [int(i.strip()) for i in ids.split(",") if i.strip().isdigit()]
        if id_list:
            query = query.where(Campaign.id.in_(id_list))

    result = await db.execute(query)
    rows = result.all()

    # Get leads per campaign
    leads_query = select(
        Lead.campaign_id,
        func.count().label("leads")
    ).where(Lead.created_at >= date_from).group_by(Lead.campaign_id)

    leads_result = await db.execute(leads_query)
    leads_by_campaign = {row.campaign_id: row.leads for row in leads_result.all()}

    output = []
    for row in rows:
        leads = leads_by_campaign.get(row.id, 0)
        spend = float(row.spend or 0)
        cpl = spend / leads if leads > 0 else 0
        output.append({
            "campaign_id": row.id,
            "campaign_name": row.name,
            "spend": spend,
            "impressions": int(row.impressions or 0),
            "clicks": int(row.clicks or 0),
            "leads": leads,
            "cpl": cpl,
            "ctr": float(row.ctr or 0),
            "roas": float(row.roas or 0),
        })

    return output
