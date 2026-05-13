"""
KGH Meta Ads — Campaigns Router
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import date, timedelta
from typing import Optional, List
import httpx

from app.database import get_db
from app.models.campaign import Campaign, CampaignMetrics
from app.schemas.campaign import (
    CampaignOut, CampaignDetail, CampaignMetricsOut,
    KPIOverview, TrendDataPoint, FunnelData, CampaignCompare
)
from app.config import settings

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("", response_model=List[CampaignOut])
async def list_campaigns(
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, PAUSED"),
    db: AsyncSession = Depends(get_db)
):
    """List all campaigns with their latest metrics"""
    query = select(Campaign).order_by(desc(Campaign.updated_at))
    if status:
        query = query.where(Campaign.status == status.upper())

    result = await db.execute(query)
    campaigns = result.scalars().all()

    # Attach latest metrics
    output = []
    for campaign in campaigns:
        metrics_query = (
            select(CampaignMetrics)
            .where(CampaignMetrics.campaign_id == campaign.id)
            .order_by(desc(CampaignMetrics.date))
            .limit(1)
        )
        metrics_result = await db.execute(metrics_query)
        latest_metrics = metrics_result.scalar_one_or_none()

        camp_dict = {
            **campaign.__dict__,
            "latest_metrics": latest_metrics
        }
        output.append(CampaignOut.model_validate(camp_dict))

    return output


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: int,
    days: int = Query(30, description="Number of days for metrics history"),
    db: AsyncSession = Depends(get_db)
):
    """Get campaign detail with metrics time-series"""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    date_from = date.today() - timedelta(days=days)
    metrics_query = (
        select(CampaignMetrics)
        .where(
            CampaignMetrics.campaign_id == campaign_id,
            CampaignMetrics.date >= date_from
        )
        .order_by(CampaignMetrics.date)
    )
    metrics_result = await db.execute(metrics_query)
    metrics = metrics_result.scalars().all()

    return CampaignDetail.model_validate({
        **campaign.__dict__,
        "metrics": metrics,
        "latest_metrics": metrics[-1] if metrics else None
    })


@router.get("/{campaign_id}/insights", response_model=List[CampaignMetricsOut])
async def get_campaign_insights(
    campaign_id: int,
    date_from: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    date_to: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db)
):
    """Get time-series metrics for a campaign"""
    query = (
        select(CampaignMetrics)
        .where(
            CampaignMetrics.campaign_id == campaign_id,
            CampaignMetrics.date >= date_from,
            CampaignMetrics.date <= date_to
        )
        .order_by(CampaignMetrics.date)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger N8N data sync workflow"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.N8N_BASE_URL}/webhook/meta-sync-trigger",
                json={"trigger": "manual", "timestamp": str(date.today())}
            )
        return {"status": "sync_triggered", "n8n_status": response.status_code}
    except Exception as e:
        return {"status": "sync_requested", "note": "N8N may not be running", "error": str(e)}
