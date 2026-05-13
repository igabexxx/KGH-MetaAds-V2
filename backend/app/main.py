"""
KGH Meta Ads — FastAPI Main Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import structlog
import time
import os

from app.config import settings
from app.database import init_db
from app.routers import campaigns, leads, analytics, socialchat

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("startup", service="KGH Meta Ads API", version="1.0.0")
    await init_db()
    yield
    logger.info("shutdown")


app = FastAPI(
    title="KGH Meta Ads API",
    description="Backend API untuk sistem otomasi Meta Ads — Kayana Green Hills",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Logging Middleware ────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration,
    )
    return response


# ─── Routers ──────────────────────────────────────────────
app.include_router(campaigns.router)
app.include_router(leads.router)
app.include_router(analytics.router)
app.include_router(socialchat.router, prefix="/api/v1/socialchat", tags=["SocialChat"])


# ─── Health Check ─────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "service": "KGH Meta Ads API",
        "version": "1.0.0",
    }


@app.get("/api/status", tags=["system"])
async def api_status():
    return {
        "api": "online",
        "meta_configured": bool(settings.META_ACCESS_TOKEN),
        "n8n_url": settings.N8N_BASE_URL,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
    }


# ─── Serve Frontend SPA ───────────────────────────────────
frontend_path = "/app/frontend"

if os.path.isdir(frontend_path):
    # app.mount("/assets", StaticFiles(directory=f"{frontend_path}/assets"), name="assets")
    app.mount("/css", StaticFiles(directory=f"{frontend_path}/css"), name="css")
    app.mount("/js", StaticFiles(directory=f"{frontend_path}/js"), name="js")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all: serve index.html for SPA routing"""
        index = os.path.join(frontend_path, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return JSONResponse({"error": "Frontend not found"}, status_code=404)
