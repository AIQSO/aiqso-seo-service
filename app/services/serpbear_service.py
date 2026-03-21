"""
SerpBear Integration Service

Syncs keyword rankings from SerpBear's API into the local database.
SerpBear is a self-hosted SERP tracking tool running as a sidecar.
"""

import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.keyword import Keyword, KeywordRanking

logger = logging.getLogger(__name__)
settings = get_settings()


class SerpBearService:
    """Service for interacting with SerpBear API."""

    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.serpbear_url.rstrip("/")
        self.api_key = settings.serpbear_api_key

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def sync_keyword_rankings(self, website_id: int) -> dict:
        """
        Fetch latest rankings from SerpBear for all keywords of a website
        and store them in the database.

        Returns summary of synced keywords.
        """
        keywords = (
            self.db.query(Keyword)
            .filter(Keyword.website_id == website_id, Keyword.is_active.is_(True))
            .all()
        )

        if not keywords:
            return {"synced": 0, "website_id": website_id}

        synced = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            for keyword in keywords:
                try:
                    if keyword.serpbear_id:
                        await self._sync_existing_keyword(client, keyword)
                    else:
                        await self._register_and_sync_keyword(client, keyword)
                    synced += 1
                except Exception as e:
                    logger.error(f"Failed to sync keyword '{keyword.keyword}': {e}")

        self.db.commit()
        return {"synced": synced, "total": len(keywords), "website_id": website_id}

    async def _sync_existing_keyword(self, client: httpx.AsyncClient, keyword: Keyword):
        """Fetch ranking data for a keyword already registered in SerpBear."""
        response = await client.get(
            f"{self.base_url}/api/keywords/{keyword.serpbear_id}",
            headers=self._headers,
        )
        if response.status_code != 200:
            logger.warning(f"SerpBear returned {response.status_code} for keyword {keyword.serpbear_id}")
            return

        data = response.json()
        self._update_keyword_from_serpbear(keyword, data)

    async def _register_and_sync_keyword(self, client: httpx.AsyncClient, keyword: Keyword):
        """Register a keyword in SerpBear and sync its initial data."""
        # Add keyword to SerpBear domain
        response = await client.post(
            f"{self.base_url}/api/keywords",
            headers=self._headers,
            json={
                "keyword": keyword.keyword,
                "device": keyword.device.value,
                "country": keyword.country,
                "domain": keyword.website.domain if keyword.website else "",
            },
        )

        if response.status_code not in (200, 201):
            logger.warning(f"Failed to register keyword in SerpBear: {response.status_code}")
            return

        data = response.json()
        if "id" in data:
            keyword.serpbear_id = data["id"]

        self._update_keyword_from_serpbear(keyword, data)

    def _update_keyword_from_serpbear(self, keyword: Keyword, data: dict):
        """Update local keyword model from SerpBear response data."""
        position = data.get("position")
        url = data.get("url")

        if position is not None:
            keyword.position = position
            keyword.url = url
            keyword.last_updated = datetime.now(UTC)

            # Update best/worst
            if keyword.best_position is None or (position > 0 and position < keyword.best_position):
                keyword.best_position = position
                keyword.best_position_date = datetime.now(UTC)
            if keyword.worst_position is None or position > keyword.worst_position:
                keyword.worst_position = position

            # Store ranking history
            ranking = KeywordRanking(
                keyword_id=keyword.id,
                date=datetime.now(UTC),
                position=position,
                url=url,
                featured_snippet=data.get("featured_snippet", False),
                local_pack=data.get("local_pack", False),
                serp_features=data.get("serp_features"),
            )
            self.db.add(ranking)

        # Update search volume if available
        if data.get("search_volume"):
            keyword.search_volume = data["search_volume"]
        if data.get("cpc"):
            keyword.cpc = str(data["cpc"])
