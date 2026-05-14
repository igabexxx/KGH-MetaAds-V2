"""
KGH Meta Ads — Authentication Router
JWT-based login for dashboard access
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import structlog

from app.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Schemas ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    expires_in: int  # seconds


# ─── JWT Helpers ──────────────────────────────────────────

def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> str:
    """Returns username if token is valid, raises 401 otherwise"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Dependency ───────────────────────────────────────────

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """FastAPI dependency — validates JWT and returns username"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)


# ─── Endpoints ────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate user and return JWT token"""
    # Validate credentials against env-configured admin account
    if req.username != settings.ADMIN_USERNAME:
        logger.warning("login_failed", username=req.username, reason="unknown_user")
        raise HTTPException(status_code=401, detail="Username atau password salah")

    # For bcrypt-hashed passwords stored in config, or plain comparison
    admin_pw = settings.ADMIN_PASSWORD
    # Support both plain and hashed passwords
    if admin_pw.startswith("$2"):
        valid = pwd_context.verify(req.password, admin_pw)
    else:
        valid = req.password == admin_pw

    if not valid:
        logger.warning("login_failed", username=req.username, reason="wrong_password")
        raise HTTPException(status_code=401, detail="Username atau password salah")

    token = create_token(req.username)
    logger.info("login_success", username=req.username)

    return TokenResponse(
        access_token=token,
        username=req.username,
        expires_in=settings.JWT_EXPIRE_HOURS * 3600,
    )


@router.get("/verify")
async def verify_current_token(username: str = Depends(require_auth)):
    """Check if current token is still valid"""
    return {"valid": True, "username": username}


@router.post("/logout")
async def logout():
    """Client-side logout — just return success (token invalidated on client)"""
    return {"success": True, "message": "Logged out successfully"}
