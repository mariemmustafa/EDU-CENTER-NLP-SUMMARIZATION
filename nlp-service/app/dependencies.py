from app.application.interfaces import SummarizationProvider
from app.application.use_cases import SummarizeDocumentUseCase
from app.infrastructure.providers.factory import create_provider
from app.services.summarization_service import SummarizationService
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_primary_provider: SummarizationProvider | None = None
_openai_provider: SummarizationProvider | None = None
_multilingual_hf_provider: SummarizationProvider | None = None
_use_case: SummarizeDocumentUseCase | None = None


async def _get_multilingual_hf_provider() -> SummarizationProvider | None:
    """Lazily load the multilingual HuggingFace provider on first Arabic request."""
    global _multilingual_hf_provider
    if _multilingual_hf_provider is not None:
        return _multilingual_hf_provider

    try:
        logger.info(
            f"Loading multilingual HuggingFace model: {settings.multilingual_huggingface_model}"
        )
        _multilingual_hf_provider = create_provider(
            "huggingface", model_override=settings.multilingual_huggingface_model
        )
        if hasattr(_multilingual_hf_provider, "load_model"):
            await _multilingual_hf_provider.load_model()
        return _multilingual_hf_provider
    except Exception as e:
        logger.warning(f"Failed to load multilingual HF provider: {e}")
        return None


async def initialize_dependencies():
    """Load providers and wire the use case at startup."""
    global _primary_provider, _openai_provider, _use_case

    # --- Primary provider (HuggingFace for English) ---
    _primary_provider = create_provider(settings.summarization_provider)
    if hasattr(_primary_provider, "load_model"):
        await _primary_provider.load_model()

    # --- OpenAI provider (loaded eagerly when API key is present) ---
    if settings.openai_api_key:
        try:
            _openai_provider = create_provider("openai")
            logger.info("OpenAI provider ready (will be used for Arabic text)")
        except Exception as e:
            logger.warning(f"Failed to load OpenAI provider: {e}. Arabic will fall back to multilingual HF.")

    # --- Wire services ---
    summarization_service = SummarizationService(
        primary=_primary_provider,
        openai=_openai_provider,
        get_multilingual_hf=_get_multilingual_hf_provider,
    )
    _use_case = SummarizeDocumentUseCase(
        summarization_service=summarization_service,
    )

    logger.info(
        f"Dependencies ready — primary={settings.summarization_provider}, "
        f"openai={'available' if _openai_provider else 'not configured'}"
    )


def get_use_case() -> SummarizeDocumentUseCase:
    if not _use_case:
        raise RuntimeError("Dependencies not initialized")
    return _use_case


def get_provider() -> SummarizationProvider:
    if not _primary_provider:
        raise RuntimeError("Dependencies not initialized")
    return _primary_provider
