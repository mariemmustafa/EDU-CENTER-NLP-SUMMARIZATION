from app.application.interfaces import SummarizationProvider
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_provider(provider_name: str | None = None, model_override: str | None = None) -> SummarizationProvider:
    """
    Create a summarization provider by name.

    Args:
        provider_name: Override name. Defaults to settings.summarization_provider.
        model_override: Optional model name override (used for HuggingFace variants).

    Returns:
        An initialised (but not yet loaded) provider instance.
    """
    name = (provider_name or settings.summarization_provider).lower()

    if name == "huggingface":
        from app.infrastructure.providers.huggingface_provider import (
            HuggingFaceProvider,
        )

        hf_model = model_override or settings.huggingface_model
        logger.info(f"Creating HuggingFace provider (model={hf_model})")
        return HuggingFaceProvider(model_name=hf_model)

    if name == "openai":
        from app.infrastructure.providers.openai_provider import OpenAIProvider

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        logger.info(f"Creating OpenAI provider (model={settings.openai_model})")
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    raise ValueError(f"Unknown provider: {name}")
