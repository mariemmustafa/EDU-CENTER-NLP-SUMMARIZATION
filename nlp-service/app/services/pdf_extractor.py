import re
import unicodedata

import fitz  # PyMuPDF

from app.utils.exceptions import ExtractionError
from app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_text(
    content: bytes,
    start_idx: int = 0,
    end_idx: int | None = None,
) -> str:
    """
    Extract and clean text from a PDF byte stream using PyMuPDF.

    Args:
        content: Raw PDF bytes (already validated).
        start_idx: 0-based start page index (inclusive).
        end_idx: 0-based end page index (exclusive). None = all pages.

    Returns:
        Cleaned text string.
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        
        # Determine valid end index
        if end_idx is None or end_idx > len(doc):
            end_idx = len(doc)
            
        raw_parts: list[str] = []
        for i in range(start_idx, end_idx):
            page = doc[i]
            # PyMuPDF extracts text including RTL properly. sort=True improves reading order in mixed/noisy PDFs.
            page_text = page.get_text("text", sort=True)
            
            # Fallback extraction
            if not page_text or len(page_text.strip()) < 50:
                blocks = page.get_text("blocks")
                if blocks:
                    blocks.sort(key=lambda b: (b[1], b[0]))
                    page_text = "\n".join([b[4] for b in blocks if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()])

            if page_text:
                raw_parts.append(page_text)

        raw_text = "\n".join(raw_parts)

    except Exception as e:
        raise ExtractionError(f"Could not read PDF pages: {e}")

    if not raw_text.strip():
        return ""

    cleaned = clean_text(raw_text)
    
    num_pages = end_idx - start_idx
    num_chars = len(cleaned)
    num_words = len(cleaned.split())
    preview = cleaned[:300].replace('\n', ' ')
    
    logger.info(f"Extracted {num_chars} characters and {num_words} words from {num_pages} pages")
    logger.info(f"Extraction preview: {preview}...")
    
    if num_pages >= 5 and num_chars < num_pages * 200:
        logger.warning("Low extraction quality detected")

    return cleaned


def clean_text(raw: str) -> str:
    """
    Clean extracted PDF text:
    - Fix encoding artefacts
    - Remove page numbers, headers/footers noise
    - Remove duplicated lines/headings
    - Normalise whitespace
    """
    text = raw

    # 1. Replace null bytes and common PDF artefacts
    text = text.replace("\x00", "")
    text = text.replace("\xad", "-")  # soft hyphen

    # 2. Normalise unicode (NFC form) to handle Arabic and other accents correctly
    text = unicodedata.normalize("NFC", text)

    # 3. Remove non-printable characters (keep newlines, tabs)
    text = re.sub(r"[^\S\n\t]", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # 4. Remove standalone page numbers and basic header/footer patterns
    text = re.sub(r"(?im)^\s*(page|p\.)\s*\d+\s*$", "", text)
    text = re.sub(r"(?im)^\s*\d+\s*$", "", text)

    # 5. Remove exact duplicated consecutive lines
    lines = text.split("\n")
    text = _remove_duplicated_lines(lines)

    # 6. Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 7. Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


def _remove_duplicated_lines(lines: list[str]) -> str:
    """
    Remove lines that appear consecutively.
    """
    cleaned = []
    prev_line = None
    
    for line in lines:
        s = line.strip()
        
        # Remove consecutive duplicates
        if s == prev_line and len(s) > 0:
            continue
            
        cleaned.append(line)
        if s:
            prev_line = s

    return "\n".join(cleaned)
