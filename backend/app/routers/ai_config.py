"""
KGH Meta Ads — AI Config Router
Manages phrases that should be skipped during AI conversation analysis
(e.g. Facebook Ads auto-reply templates)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.lead import AiSkipPhrase

router = APIRouter(prefix="/api/ai-config", tags=["ai-config"])

# Flag: table has been initialized for this process run
_table_ready = False


# ─── Schemas ──────────────────────────────────────────────

class SkipPhraseCreate(BaseModel):
    phrase: str
    description: Optional[str] = None
    match_type: str = "contains"  # contains | exact | startswith

class SkipPhraseOut(BaseModel):
    id: int
    phrase: str
    description: Optional[str]
    match_type: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── One-time table setup (called on first request) ───────

async def ensure_table(db: AsyncSession):
    global _table_ready
    if _table_ready:
        return
    _table_ready = True

    # Create table (without UNIQUE yet — we'll add it after dedup)
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS ai_skip_phrases (
            id          SERIAL PRIMARY KEY,
            phrase      TEXT NOT NULL,
            description VARCHAR(255),
            match_type  VARCHAR(20) DEFAULT 'contains',
            is_active   BOOLEAN DEFAULT true,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """))
    await db.commit()

    # Step 1: Remove duplicate rows — keep only the lowest id per phrase
    await db.execute(text("""
        DELETE FROM ai_skip_phrases a
        USING ai_skip_phrases b
        WHERE a.id > b.id AND a.phrase = b.phrase
    """))
    await db.commit()

    # Step 2: Add UNIQUE constraint (safe now that duplicates are gone)
    await db.execute(text("""
        DO $$ BEGIN
            ALTER TABLE ai_skip_phrases ADD CONSTRAINT ai_skip_phrases_phrase_unique UNIQUE (phrase);
        EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL;
        END $$;
    """))
    await db.commit()

    # Step 3: Seed defaults only if table is empty
    count_result = await db.execute(text("SELECT COUNT(*) FROM ai_skip_phrases"))
    count = count_result.scalar()
    if count == 0:
        await db.execute(text("""
            INSERT INTO ai_skip_phrases (phrase, description, match_type) VALUES
            ('Halo! Ada yang bisa kami bantu?', 'Template sambutan otomatis', 'exact'),
            ('Terima kasih sudah menghubungi kami', 'Template penutup otomatis', 'contains'),
            ('Kami akan segera menghubungi Anda', 'Template konfirmasi auto-reply', 'contains'),
            ('Silakan tunggu, agen kami akan segera membantu', 'Template antrian agen', 'contains'),
            ('Hai! Selamat datang di Kayana Green Hills', 'Template sambutan KGH', 'contains'),
            ('Terima kasih atas minat Anda', 'Template respons awal', 'contains')
            ON CONFLICT (phrase) DO NOTHING
        """))
        await db.commit()


# ─── GET all skip phrases ──────────────────────────────────

@router.get("/skip-phrases", response_model=List[SkipPhraseOut])
async def list_skip_phrases(db: AsyncSession = Depends(get_db)):
    """List all AI skip phrases"""
    await ensure_table(db)
    result = await db.execute(
        select(AiSkipPhrase).order_by(AiSkipPhrase.created_at.asc())
    )
    return result.scalars().all()


# ─── POST create phrase ────────────────────────────────────

@router.post("/skip-phrases", response_model=SkipPhraseOut, status_code=201)
async def create_skip_phrase(payload: SkipPhraseCreate, db: AsyncSession = Depends(get_db)):
    """Add a new phrase to the AI skip list"""
    # Check for duplicate
    existing = await db.execute(
        select(AiSkipPhrase).where(AiSkipPhrase.phrase == payload.phrase.strip())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Kalimat ini sudah ada dalam daftar")

    phrase = AiSkipPhrase(
        phrase=payload.phrase.strip(),
        description=payload.description,
        match_type=payload.match_type
    )
    db.add(phrase)
    await db.commit()
    await db.refresh(phrase)
    return phrase


# ─── PATCH toggle active ───────────────────────────────────

@router.patch("/skip-phrases/{phrase_id}")
async def toggle_skip_phrase(phrase_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle active status of a skip phrase"""
    phrase = await db.get(AiSkipPhrase, phrase_id)
    if not phrase:
        raise HTTPException(status_code=404, detail="Phrase not found")
    phrase.is_active = not phrase.is_active
    await db.commit()
    return {"id": phrase.id, "is_active": phrase.is_active}


# ─── DELETE phrase ─────────────────────────────────────────

@router.delete("/skip-phrases/{phrase_id}")
async def delete_skip_phrase(phrase_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a skip phrase"""
    phrase = await db.get(AiSkipPhrase, phrase_id)
    if not phrase:
        raise HTTPException(status_code=404, detail="Phrase not found")
    await db.delete(phrase)
    await db.commit()
    return {"deleted": True}


# ─── GET active phrases (used by analyze endpoint) ─────────

@router.get("/skip-phrases/active")
async def get_active_phrases(db: AsyncSession = Depends(get_db)):
    """Get only active phrases — used internally by analyze endpoint"""
    await ensure_table(db)
    result = await db.execute(
        select(AiSkipPhrase).where(AiSkipPhrase.is_active == True)
    )
    phrases = result.scalars().all()
    return [{"phrase": p.phrase, "match_type": p.match_type} for p in phrases]
