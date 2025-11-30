from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
import secrets
import tldextract

from app.database import get_db
from app.models.website import Website
from app.models.client import Client

router = APIRouter()


# Pydantic schemas
class WebsiteCreate(BaseModel):
    client_id: int
    url: HttpUrl
    name: Optional[str] = None


class WebsiteResponse(BaseModel):
    id: int
    client_id: int
    domain: str
    name: Optional[str]
    url: str
    is_active: bool
    is_verified: bool
    last_audit_at: Optional[datetime]
    last_audit_score: Optional[int]
    performance_score: Optional[int]
    seo_score: Optional[int]
    accessibility_score: Optional[int]
    keywords_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# Endpoints
@router.post("/", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
async def create_website(website: WebsiteCreate, db: Session = Depends(get_db)):
    """Add a new website for tracking."""
    # Check client exists
    client = db.query(Client).filter(Client.id == website.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Check tier limits
    current_count = len(client.websites)
    if not client.can_add_website(current_count):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Website limit reached for {client.tier.value} tier"
        )

    # Extract domain
    url_str = str(website.url)
    extracted = tldextract.extract(url_str)
    domain = f"{extracted.domain}.{extracted.suffix}"

    # Check if domain already exists for this client
    existing = db.query(Website).filter(
        Website.client_id == website.client_id,
        Website.domain == domain
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain already added"
        )

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)

    db_website = Website(
        client_id=website.client_id,
        domain=domain,
        name=website.name or domain,
        url=url_str,
        verification_token=verification_token,
    )
    db.add(db_website)
    db.commit()
    db.refresh(db_website)

    return WebsiteResponse(
        **db_website.__dict__,
        keywords_count=0,
    )


@router.get("/", response_model=list[WebsiteResponse])
async def list_websites(
    client_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all websites."""
    query = db.query(Website)
    if client_id:
        query = query.filter(Website.client_id == client_id)

    websites = query.offset(skip).limit(limit).all()

    return [
        WebsiteResponse(
            **w.__dict__,
            keywords_count=len(w.keywords),
        )
        for w in websites
    ]


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(website_id: int, db: Session = Depends(get_db)):
    """Get a specific website."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    return WebsiteResponse(
        **website.__dict__,
        keywords_count=len(website.keywords),
    )


@router.get("/{website_id}/verify")
async def get_verification_info(website_id: int, db: Session = Depends(get_db)):
    """Get verification instructions for a website."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    if website.is_verified:
        return {"status": "already_verified"}

    return {
        "status": "pending",
        "verification_token": website.verification_token,
        "methods": [
            {
                "method": "meta_tag",
                "instructions": f'Add this meta tag to your homepage: <meta name="aiqso-verification" content="{website.verification_token}">',
            },
            {
                "method": "txt_file",
                "instructions": f"Create a file at {website.url}/aiqso-verify.txt containing: {website.verification_token}",
            },
            {
                "method": "dns_txt",
                "instructions": f'Add a TXT record to your DNS: aiqso-verify={website.verification_token}',
            },
        ],
    }


@router.post("/{website_id}/verify")
async def verify_website(website_id: int, db: Session = Depends(get_db)):
    """Verify website ownership."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    if website.is_verified:
        return {"status": "already_verified"}

    # TODO: Implement actual verification check
    # For now, auto-verify
    website.is_verified = True
    db.commit()

    return {"status": "verified"}


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website(website_id: int, db: Session = Depends(get_db)):
    """Delete a website."""
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found"
        )

    db.delete(website)
    db.commit()
