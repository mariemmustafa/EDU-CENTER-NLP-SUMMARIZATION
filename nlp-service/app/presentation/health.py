from fastapi import APIRouter
from app.dependencies import get_provider

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    provider = get_provider()
    provider_health = await provider.health_check()

    return {
        "status": "healthy",
        "service": "nlp-service",
        "provider": provider_health,
    }
