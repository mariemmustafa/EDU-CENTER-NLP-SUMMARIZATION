import re

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Sentence-ending pattern: period/question/exclamation followed by space or newline
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def analyze_text(text: str) -> dict:
    """Analyze text to determine complexity and type."""
    math_indicators = len(re.findall(r'[\+\=\/\*\^\%\∑\∫\≈\≤\≥\∞]', text))
    words = text.split()
    word_count = len(words)
    
    if word_count == 0:
        return {"complexity": "low", "type": "general"}
        
    sentences = _SENTENCE_END.split(text)
    avg_sentence_length = word_count / max(1, len(sentences))
    avg_word_length = sum(len(w) for w in words) / word_count
    
    if math_indicators > word_count * 0.02:
        text_type = "math/scientific"
    else:
        text_type = "general"
        
    if avg_sentence_length > 25 or avg_word_length > 6 or text_type == "math/scientific":
        complexity = "high"
    elif avg_sentence_length > 15 or avg_word_length > 4.5:
        complexity = "medium"
    else:
        complexity = "low"
        
    return {"complexity": complexity, "type": text_type}


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 20, analysis: dict | None = None) -> list[str]:
    """
    Split text into chunks using sentence-aware boundaries.
    Dynamically adjusts sizes based on text complexity.
    """
    if analysis:
        if analysis["complexity"] == "high":
            max_tokens = min(max_tokens, 500)
            overlap = min(overlap, 30)
        elif analysis["complexity"] == "low":
            max_tokens = max(max_tokens, 600)

    words = text.split()
    if len(words) <= max_tokens:
        return [text]

    # Split into sentences first
    sentences = _SENTENCE_END.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    current_words: list[str] = []
    current_count = 0

    for sentence in sentences:
        sentence_words = sentence.split()
        sentence_len = len(sentence_words)

        # If a single sentence exceeds max, force-split it by words
        if sentence_len > max_tokens:
            # Flush current buffer first
            if current_words:
                chunks.append(" ".join(current_words))
                # Keep overlap words for context continuity
                current_words = current_words[-overlap:] if overlap else []
                current_count = len(current_words)

            # Force-split the long sentence
            for i in range(0, sentence_len, max_tokens - overlap):
                segment = sentence_words[i : i + max_tokens]
                chunks.append(" ".join(segment))
            continue

        # Would adding this sentence exceed the limit?
        if current_count + sentence_len > max_tokens:
            # Flush current chunk
            chunks.append(" ".join(current_words))
            # Keep overlap words for context continuity
            current_words = current_words[-overlap:] if overlap else []
            current_count = len(current_words)

        current_words.extend(sentence_words)
        current_count += sentence_len

    # Flush remaining
    if current_words:
        chunks.append(" ".join(current_words))

    logger.info(f"Split text into {len(chunks)} chunks (max_tokens={max_tokens})")
    return chunks


def merge_summaries(summaries: list[str]) -> str:
    """
    Merge multiple chunk summaries into a single coherent summary.

    - 1 chunk: return as-is.
    - 2-3 chunks: join with paragraph breaks.
    - 4+ chunks: join with paragraph breaks (recursive re-summarization
      is done at the service layer if needed).
    """
    if len(summaries) <= 1:
        return summaries[0] if summaries else ""

    return "\n\n".join(s.strip() for s in summaries if s.strip())
