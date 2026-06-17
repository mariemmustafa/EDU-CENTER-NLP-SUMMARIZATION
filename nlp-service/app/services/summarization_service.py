import asyncio
from typing import Awaitable, Callable

from app.application.interfaces import SummarizationProvider
from app.config import settings
from app.infrastructure.text_processor import chunk_text, merge_summaries
from app.utils.exceptions import ProviderError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Indicators that a HuggingFace model name supports non-English languages
_MULTILINGUAL_INDICATORS = ("multilingual", "mt5", "mbart", "xlsum", "arabic", "multi")


def _is_multilingual_model(model_name: str) -> bool:
    """Check if a HuggingFace model name looks multilingual."""
    lower = model_name.lower()
    return any(ind in lower for ind in _MULTILINGUAL_INDICATORS)


class SummarizationService:
    """
    Orchestrates chunking → summarization → merging.

    Supports language-aware routing with retry (max 1 retry / 2 attempts).
    """

    def __init__(
        self,
        primary: SummarizationProvider,
        openai: SummarizationProvider | None = None,
        get_multilingual_hf: Callable[[], Awaitable[SummarizationProvider | None]] | None = None,
        # Legacy parameter kept for backward compatibility
        fallback: SummarizationProvider | None = None,
    ):
        self._primary = primary
        self._openai = openai
        self._get_multilingual_hf = get_multilingual_hf
        # Support the old `fallback` kwarg for backward compatibility
        if fallback is not None and openai is None:
            self._openai = fallback

    async def summarize(self, text: str, request_id: str = "unknown", lang: str = "en") -> str:
        """
        Summarize text by chunking, running each chunk through the provider,
        and merging the results.
        """
        import time
        start_time = time.time()
        
        # 1. Analyze text complexity and type
        from app.infrastructure.text_processor import analyze_text
        analysis = analyze_text(text)
        
        chunks = chunk_text(
            text,
            max_tokens=settings.chunk_max_tokens,
            overlap=settings.chunk_overlap,
            analysis=analysis
        )

        logger.info(
            f"Summarizing {len(chunks)} chunk(s) [lang={lang}, type={analysis['type']}, complexity={analysis['complexity']}]",
            extra={"request_id": request_id},
        )

        # Use an ephemeral cache to avoid reprocessing identical chunks
        self._chunk_cache = {}

        summaries = await self._summarize_chunks(chunks, request_id, lang, analysis)

        # Merge chunk summaries
        merged = merge_summaries(summaries)

        # If we had many chunks, do a final condensation pass
        if len(chunks) >= 3 and len(merged) > 1000:
            logger.info(
                "Running condensation pass on merged summaries",
                extra={"request_id": request_id},
            )
            merged = await self._call_with_routing(merged, request_id, lang, analysis)
            
        process_time = round(time.time() - start_time, 2)
        logger.info(f"Summarization pipeline completed in {process_time}s", extra={"request_id": request_id})

        return merged

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _summarize_chunks(
        self, chunks: list[str], request_id: str, lang: str, analysis: dict
    ) -> list[str]:
        """Summarize each chunk, with fallback on failure."""
        summaries: list[str] = []

        for i, chunk in enumerate(chunks):
            if chunk in self._chunk_cache:
                summaries.append(self._chunk_cache[chunk])
                continue

            import time
            chunk_start = time.time()
            logger.info(
                f"Processing chunk {i + 1}/{len(chunks)}",
                extra={"request_id": request_id},
            )
            summary = await self._call_with_routing(chunk, request_id, lang, analysis)
            
            chunk_time = round(time.time() - chunk_start, 2)
            logger.info(f"Chunk {i + 1} processed in {chunk_time}s", extra={"request_id": request_id})
            
            self._chunk_cache[chunk] = summary
            summaries.append(summary)

        return summaries

    async def _call_with_routing(self, text: str, request_id: str, lang: str, analysis: dict) -> str:
        """
        Route to the correct provider based on language, type, complexity, with fallbacks.
        """
        is_arabic = lang == "ar"
        text_type = analysis.get("type", "general")
        complexity = analysis.get("complexity", "low")

        multilingual_hf = None
        if self._get_multilingual_hf is not None:
            multilingual_hf = await self._get_multilingual_hf()

        if is_arabic:
            # Arabic: OpenAI primary, HF fallback
            primary, fallbacks = self._resolve_arabic_providers(multilingual_hf)
        else:
            # English / other
            if text_type == "math/scientific" or complexity == "high":
                # Complex/Math: OpenAI primary, HF fallback
                primary = self._openai if self._openai else self._primary
                fallbacks = [self._primary] if self._openai else [multilingual_hf]
            else:
                # General simple: HF primary, OpenAI fallback, then multilingual
                primary = self._primary
                fallbacks = [self._openai, multilingual_hf]

        # Clean None values from fallbacks
        fallbacks = [f for f in fallbacks if f is not None and f is not primary]

        return await self._call_provider_with_retry(
            primary, fallbacks, text, request_id, lang
        )

    def _resolve_arabic_providers(
        self,
        multilingual_hf: SummarizationProvider | None
    ) -> tuple[SummarizationProvider, list[SummarizationProvider]]:
        """Return (primary, fallbacks) providers for Arabic text."""
        if self._openai is not None:
            # OpenAI primary, multilingual HF fallback
            return self._openai, [multilingual_hf]
        elif multilingual_hf is not None:
            # No OpenAI → multilingual HF primary, no fallback
            return multilingual_hf, []
        else:
            # Last resort: try the English-only primary (may produce low-quality output)
            logger.warning(
                "No Arabic-capable provider available; falling back to English-only model"
            )
            return self._primary, []

    async def _call_provider_with_retry(
        self,
        primary: SummarizationProvider,
        fallbacks: list[SummarizationProvider],
        text: str,
        request_id: str,
        lang: str,
    ) -> str:
        """
        Try primary provider with 1 retry (2 attempts total).
        On exhaustion, try the fallback providers sequentially (1 retry each).
        Raises ProviderError if everything fails.
        """
        # --- Attempt primary (with 1 retry) ---
        primary_error = await self._try_provider(primary, text, lang, request_id, label="primary")
        if primary_error is None:
            return self._last_result  # set by _try_provider on success

        # --- Attempt fallbacks (with 1 retry each) ---
        for i, fallback in enumerate(fallbacks):
            logger.warning(
                f"Provider failed, trying fallback {i+1}",
                extra={"request_id": request_id},
            )
            fallback_error = await self._try_provider(fallback, text, lang, request_id, label=f"fallback-{i+1}")
            if fallback_error is None:
                return self._last_result

        # No fallbacks succeeded
        raise ProviderError("all", f"All providers failed. Root cause from primary: {primary_error}")

    async def _try_provider(
        self,
        provider: SummarizationProvider,
        text: str,
        lang: str,
        request_id: str,
        label: str,
        max_attempts: int = 2,
    ) -> str | None:
        """
        Try a provider up to `max_attempts` times (default 2 = 1 retry).

        Returns None on success (result stored in self._last_result).
        Returns error message string on failure.
        """
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                import time
                call_start = time.time()
                result = await provider.summarize(text, lang)
                call_time = round(time.time() - call_start, 2)
                
                # Strict Output Validation
                cleaned = result.strip() if result else ""
                if not cleaned or len(cleaned) < 20:
                    raise ProviderError("all", f"Provider returned empty or too short text (<20 chars).")
                
                # Extremely low diversity check
                if len(set(cleaned)) < 10:
                    raise ProviderError("all", f"Provider returned meaningless/repeating text (low diversity).")
                    
                # Meaningless repetition: "world world world"
                words = cleaned.split()
                if words and len(words) > 10:
                    unique_words = set(words)
                    if len(unique_words) / len(words) < 0.2:
                        raise ProviderError("all", "Provider returned meaningless/repeating text (word repetition).")
                    
                self._last_result = cleaned
                logger.info(f"{label} provider succeeded in {call_time}s", extra={"request_id": request_id})
                return None  # success

            except ProviderError as e:
                last_error = e.message
                logger.warning(
                    f"{label} provider error (attempt {attempt}/{max_attempts}): {e.message}",
                    extra={"request_id": request_id},
                )
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"{label} provider unexpected error (attempt {attempt}/{max_attempts}): {e}",
                    extra={"request_id": request_id},
                    exc_info=True
                )

            # Brief pause before retry
            if attempt < max_attempts:
                await asyncio.sleep(1)

        return last_error
