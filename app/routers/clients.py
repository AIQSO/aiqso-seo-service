from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import secrets

from app.database import get_db
from app.models.client import Client, ClientTier, TIER_LIMITS

router = APIRouter()


# Pydantic schemas
class ClientCreate(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    tier: ClientTier = ClientTier.STARTER


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    tier: Optional[ClientTier] = None
    is_active: Optional[bool] = None


class ClientResponse(BaseModel):
    id: int
    name: str
    email: str
    company: Optional[str]
    phone: Optional[str]
    tier: ClientTier
    is_active: bool
    api_key: Optional[str]
    created_at: datetime
    websites_count: int = 0
    keywords_count: int = 0

    class Config:
        from_attributes = True


class TierInfo(BaseModel):
    tier: ClientTier
    max_keywords: int
    max_websites: int
    audit_frequency: str
    ai_insights: bool
    api_access: bool
    white_label: bool
    price: int


# Endpoints
@router.get("/tiers")
async def list_tiers():
    """Get all available service tiers with their limits."""
    return [
        TierInfo(tier=tier, **limits)
        for tier, limits in TIER_LIMITS.items()
    ]


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client."""
    # Check if email already exists
    existing = db.query(Client).filter(Client.email == client.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Generate API key
    api_key = f"aiqso_seo_{secrets.token_urlsafe(32)}"

    db_client = Client(
        **client.dict(),
        api_key=api_key,
        subscription_start=datetime.utcnow(),
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)

    return ClientResponse(
        **db_client.__dict__,
        websites_count=0,
        keywords_count=0,
    )


@router.get("/", response_model=list[ClientResponse])
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all clients."""
    query = db.query(Client)
    if is_active is not None:
        query = query.filter(Client.is_active == is_active)

    clients = query.offset(skip).limit(limit).all()

    return [
        ClientResponse(
            **client.__dict__,
            websites_count=len(client.websites),
            keywords_count=sum(len(w.keywords) for w in client.websites),
        )
        for client in clients
    ]


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a specific client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    return ClientResponse(
        **client.__dict__,
        websites_count=len(client.websites),
        keywords_count=sum(len(w.keywords) for w in client.websites),
    )


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_db)
):
    """Update a client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    update_data = client_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)

    return ClientResponse(
        **client.__dict__,
        websites_count=len(client.websites),
        keywords_count=sum(len(w.keywords) for w in client.websites),
    )


@router.post("/{client_id}/regenerate-api-key")
async def regenerate_api_key(client_id: int, db: Session = Depends(get_db)):
    """Regenerate client's API key."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    new_api_key = f"aiqso_seo_{secrets.token_urlsafe(32)}"
    client.api_key = new_api_key
    db.commit()

    return {"api_key": new_api_key}


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: int, db: Session = Depends(get_db)):
    """Delete a client (soft delete by deactivating)."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    client.is_active = False
    db.commit()
