from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.keyword import Keyword, KeywordRanking, DeviceType
from app.models.website import Website
from app.models.client import Client

router = APIRouter()


class KeywordCreate(BaseModel):
    website_id: int
    keyword: str
    device: DeviceType = DeviceType.DESKTOP
    country: str = "US"
    tags: list[str] = []


class KeywordResponse(BaseModel):
    id: int
    website_id: int
    keyword: str
    device: DeviceType
    country: str
    position: Optional[int]
    url: Optional[str]
    last_updated: Optional[datetime]
    best_position: Optional[int]
    search_volume: Optional[int]
    position_change_7d: Optional[int] = None
    tags: list[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class KeywordRankingResponse(BaseModel):
    date: datetime
    position: Optional[int]
    url: Optional[str]
    impressions: Optional[int]
    clicks: Optional[int]

    class Config:
        from_attributes = True


@router.post("/", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(keyword: KeywordCreate, db: Session = Depends(get_db)):
    """Add a new keyword for tracking."""
    website = db.query(Website).filter(Website.id == keyword.website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    client = db.query(Client).filter(Client.id == website.client_id).first()
    current_count = sum(len(w.keywords) for w in client.websites)
    if not client.can_add_keyword(current_count):
        raise HTTPException(
            status_code=403,
            detail=f"Keyword limit reached for {client.tier.value} tier"
        )

    existing = db.query(Keyword).filter(
        Keyword.website_id == keyword.website_id,
        Keyword.keyword == keyword.keyword,
        Keyword.device == keyword.device,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Keyword already tracked")

    db_keyword = Keyword(**keyword.dict())
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)

    return KeywordResponse(**db_keyword.__dict__, position_change_7d=None)


@router.get("/", response_model=list[KeywordResponse])
async def list_keywords(
    website_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List keywords."""
    query = db.query(Keyword)
    if website_id:
        query = query.filter(Keyword.website_id == website_id)

    keywords = query.offset(skip).limit(limit).all()

    return [
        KeywordResponse(
            **k.__dict__,
            position_change_7d=k.get_position_change(7),
        )
        for k in keywords
    ]


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Get a specific keyword."""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    return KeywordResponse(
        **keyword.__dict__,
        position_change_7d=keyword.get_position_change(7),
    )


@router.get("/{keyword_id}/history", response_model=list[KeywordRankingResponse])
async def get_keyword_history(
    keyword_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get ranking history for a keyword."""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    rankings = db.query(KeywordRanking).filter(
        KeywordRanking.keyword_id == keyword_id,
        KeywordRanking.date >= cutoff,
    ).order_by(KeywordRanking.date.desc()).all()

    return [KeywordRankingResponse(**r.__dict__) for r in rankings]


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Delete a keyword."""
    keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    db.delete(keyword)
    db.commit()
