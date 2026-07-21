"""
agent1/app/routes/catalogue.py
───────────────────────────────
GET /catalogue/stats — Integration catalogue statistics endpoint.

Returns aggregated usage statistics from the learnable integration_catalogue
stored in watsonx.data. Used to inspect which tools are being recommended
most frequently and validate that the learnable catalogue is working.
"""

from fastapi import APIRouter, Depends

from shared.config import Settings
from shared.logging import get_logger

from agent1.app.config import get_settings
from agent1.app.models.response import CatalogueStats
from agent1.app.services.catalogue_store import get_catalogue_stats

logger = get_logger(__name__)
router = APIRouter(prefix="/catalogue", tags=["catalogue"])


@router.get("/stats", response_model=CatalogueStats)
async def catalogue_stats(
    settings: Settings = Depends(get_settings),
) -> CatalogueStats:
    """
    Return aggregated tool usage statistics from the integration catalogue.

    Useful for:
    - Validating the learnable recommender is recording usage correctly
    - Showing integration teams which tools are most frequently recommended
    - Providing input to governance reviews
    """
    logger.info("Catalogue stats requested")
    stats = get_catalogue_stats(settings)
    return CatalogueStats(**stats)
