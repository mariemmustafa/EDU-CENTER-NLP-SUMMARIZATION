from app.config import settings
from app.domain.entities import SummarizationResponse
from app.services.pdf_validator import validate_pdf, validate_page_range
from app.services.pdf_extractor import extract_text
from app.services.summarization_service import SummarizationService
from app.utils.exceptions import EmptyTextError, TextTooLongError, SummarizationError
from app.utils.logger import get_logger
from langdetect import detect, LangDetectException

logger = get_logger(__name__)


class SummarizeDocumentUseCase:
    """
    Full PDF summarization pipeline:
    validate → extract → check limits → detect lang → summarize → respond.
    """

    def __init__(self, summarization_service: SummarizationService):
        self._summarization_service = summarization_service

    async def execute(
        self,
        content: bytes,
        filename: str,
        start_page: int | None = None,
        end_page: int | None = None,
        request_id: str = "unknown",
    ) -> SummarizationResponse:
        # 1. Validate PDF
        logger.info(
            f"Processing file: {filename}",
            extra={"request_id": request_id},
        )
        total_pages = validate_pdf(content, filename)

        # 2. Validate page range
        start_idx, end_idx = validate_page_range(start_page, end_page, total_pages)
        logger.info(
            f"Page range: {start_idx + 1}-{end_idx} of {total_pages}",
            extra={"request_id": request_id},
        )

        # 3. Extract and clean text
        text = extract_text(content, start_idx, end_idx)
        
        # Lightweight input quality check: reject empty or mostly noisy/scanned text
        import re
        if not text.strip() or len(re.findall(r'[^\W\d_]', text)) < 50:
            raise EmptyTextError()

        original_length = len(text)

        # 4. Check text length limit
        if original_length > settings.max_input_length:
            raise TextTooLongError(
                length=original_length,
                max_length=settings.max_input_length,
            )

        # 5. Detect language
        try:
            lang = detect(text)
        except LangDetectException:
            lang = "en"
            
        logger.info(f"Detected language: {lang}", extra={"request_id": request_id})

        # 6. Summarize
        logger.info(
            f"Starting summarization ({original_length} chars)",
            extra={"request_id": request_id},
        )
        summary_text = await self._summarization_service.summarize(
            text, request_id=request_id, lang=lang
        )

        # 7. Validate summary result
        cleaned_summary = summary_text.strip() if summary_text else ""
        if not cleaned_summary:
            raise SummarizationError(
                message="Summary generation failed: the provider returned an empty response.",
                status_code=500,
            )

        if len(cleaned_summary) < 10 or len(set(cleaned_summary)) < 4:
            raise SummarizationError(
                message="Summary generation failed: the provider returned corrupted or meaningless text.",
                status_code=500,
            )

        # 8. Build response
        summary_length = len(cleaned_summary)
        compression_ratio = (
            round(1 - (summary_length / original_length), 4)
            if original_length > 0
            else 0.0
        )

        logger.info(
            f"Summarization complete: {original_length} → {summary_length} chars "
            f"({compression_ratio:.1%} compression)",
            extra={"request_id": request_id},
        )

        return SummarizationResponse(
            original_length=original_length,
            summary_length=summary_length,
            compression_ratio=compression_ratio,
            summary_text=cleaned_summary,
        )
