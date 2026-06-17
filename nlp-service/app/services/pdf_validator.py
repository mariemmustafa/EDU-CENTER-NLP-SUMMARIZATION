import io

from pypdf import PdfReader

from app.config import settings
from app.utils.exceptions import (
    InvalidFileError,
    FileTooLargeError,
    PageRangeError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

PDF_MAGIC_BYTES = b"%PDF"


def validate_pdf(content: bytes, filename: str) -> int:
    """
    Validate that the uploaded file is a legitimate, parseable PDF.

    Returns the total page count on success.
    Raises InvalidFileError or FileTooLargeError on failure.
    """
    # 1. Check extension
    if not filename.lower().endswith(".pdf"):
        raise InvalidFileError(
            f"Expected a .pdf file, got '{filename.rsplit('.', 1)[-1]}'"
        )

    # 2. Check file size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise FileTooLargeError(size_mb=size_mb, max_mb=settings.max_file_size_mb)

    # 3. Check magic bytes (catches renamed non-PDF files)
    if not content[:4].startswith(PDF_MAGIC_BYTES):
        raise InvalidFileError("File does not appear to be a valid PDF (bad header)")

    # 4. Attempt to parse — catches corrupted PDFs
    try:
        reader = PdfReader(io.BytesIO(content))
        total_pages = len(reader.pages)
    except Exception as e:
        raise InvalidFileError(f"PDF is corrupted or unreadable: {e}")

    if total_pages == 0:
        raise InvalidFileError("PDF contains zero pages")

    logger.info(f"PDF validated: {filename}, {total_pages} pages, {size_mb:.1f} MB")
    return total_pages


def validate_page_range(
    start_page: int | None,
    end_page: int | None,
    total_pages: int,
) -> tuple[int, int]:
    """
    Validate and normalise page range to 0-based indices for slicing.

    User-facing pages are 1-based. Returns (start_idx, end_idx) where
    end_idx is exclusive (suitable for Python slicing).
    """
    start = start_page if start_page is not None else 1
    end = end_page if end_page is not None else total_pages

    if start < 1:
        raise PageRangeError("start_page must be >= 1")
    if end < start:
        raise PageRangeError(
            f"end_page ({end}) must be >= start_page ({start})"
        )
    if start > total_pages:
        raise PageRangeError(
            f"start_page ({start}) exceeds total pages ({total_pages})"
        )
    if end > total_pages:
        raise PageRangeError(
            f"end_page ({end}) exceeds total pages ({total_pages})"
        )

    # Convert to 0-based, end exclusive
    return start - 1, end
