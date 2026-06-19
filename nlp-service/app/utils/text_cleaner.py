"""
Post-processing text cleanup for summarization output.

Removes hallucinated repetitions, corrupted tokens, duplicate sentences,
quote artifacts, Arabic temporal hallucinations, formatting leftovers,
and normalises whitespace — without altering the semantic content.
"""

import re
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 1. Repeated character patterns  ("OSOSOS", "AAAA", "ababab")
# ---------------------------------------------------------------------------

# Two-or-more characters repeated 3+ times  e.g. "OS" x3 → "OSOSOS"
_REPEATED_NGRAM = re.compile(r'(.{2,6}?)\1{2,}')

# Single character repeated 4+ times  e.g. "AAAA", "aaaa"
_REPEATED_CHAR = re.compile(r'(.)\1{3,}')

# Arabic-specific: same Arabic word repeated 3+ times consecutively
_REPEATED_AR_WORD = re.compile(r'([\u0600-\u06FF]+)(?:\s+\1){2,}')

# Numbers / noise like "11 121" at end of text (common Arabic model artefact)
_TRAILING_NOISE = re.compile(r'(?:\s+\d{1,3}){2,}\s*$')


def _remove_repeated_char_patterns(text: str) -> str:
    """Strip repeated character n-grams and single chars."""
    # Remove repeated n-grams (e.g. "OSOSOS" → "")
    text = _REPEATED_NGRAM.sub('', text)
    # Collapse runs of single char (e.g. "AAAA" → "A")
    text = _REPEATED_CHAR.sub(r'\1', text)
    # Remove repeated Arabic words (e.g. "دبي دبي دبي" → "دبي")
    text = _REPEATED_AR_WORD.sub(r'\1', text)
    # Remove trailing numeric noise
    text = _TRAILING_NOISE.sub('', text)
    return text


# ---------------------------------------------------------------------------
# 2. Repeated consecutive words (language-agnostic)
# ---------------------------------------------------------------------------

def _remove_repeated_words(text: str) -> str:
    """Remove consecutive duplicate words, e.g. 'the the cat' → 'the cat'."""
    # Split on whitespace, keeping track of tokens
    tokens = text.split()
    if len(tokens) < 2:
        return text

    deduped = [tokens[0]]
    for tok in tokens[1:]:
        if tok.lower() != deduped[-1].lower():
            deduped.append(tok)
    return ' '.join(deduped)


# ---------------------------------------------------------------------------
# 3. Duplicated sentences
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?؟。])\s+')


def _remove_duplicate_sentences(text: str) -> str:
    """Remove exact-duplicate sentences while preserving order."""
    sentences = _SENTENCE_SPLIT.split(text)
    if len(sentences) < 2:
        return text

    seen: set[str] = set()
    unique: list[str] = []
    for sent in sentences:
        normalised = sent.strip()
        if not normalised:
            continue
        key = normalised.lower()
        if key not in seen:
            seen.add(key)
            unique.append(normalised)

    return ' '.join(unique)


# ---------------------------------------------------------------------------
# 4. Whitespace normalisation
# ---------------------------------------------------------------------------

_MULTI_SPACE = re.compile(r'[ \t]+')
_MULTI_NEWLINE = re.compile(r'\n{3,}')


def _normalise_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs and excessive newlines."""
    text = _MULTI_SPACE.sub(' ', text)
    text = _MULTI_NEWLINE.sub('\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# 5. Output artifact cleanup (NEW — post-processing only)
# ---------------------------------------------------------------------------

# 5a. Empty or duplicated quotation marks
#     Matches: "", '', «», \u201c\u201d, or quotes with only whitespace inside
_EMPTY_QUOTES = re.compile(
    r'[\u201c\u201d\u00ab\u00bb]{2}'
    r'|[\u201c\u00ab]\s*[\u201d\u00bb]'
    r'|""'
    r"|''"
)

# 5b. Arabic hallucinated temporal / transition filler phrases
#     Only fires when TWO OR MORE of these phrases appear back-to-back
#     (a single occurrence is legitimate and kept).
_AR_TEMPORAL_PHRASES = (
    r'في الوقت الحالي'
    r'|في الوقت نفسه'
    r'|على صعيد آخر'
    r'|من جهة أخرى'
    r'|بالإضافة إلى ذلك'
)
_AR_TEMPORAL_HALLUCINATIONS = re.compile(
    r'(?:' + _AR_TEMPORAL_PHRASES + r')'
    r'(?:[،,]\s*(?:' + _AR_TEMPORAL_PHRASES + r'))+'
)

# 5c. Orphan section numbers on their own line (e.g. "1." or "2.3.")
_ORPHAN_SECTION_NUMBERS = re.compile(r'^\s*(?:\d+\.)+\s*$', re.MULTILINE)

# 5d. Exact consecutive duplicate lines (typically duplicated headings)
_DUPLICATED_LINES = re.compile(r'^(.+)\n\1$', re.MULTILINE)

# 5e. Repeated multi-word phrases (3-8 words repeated 2+ times consecutively)
_REPEATED_PHRASE = re.compile(r'((?:\S+\s+){2,7}\S+)(?:\s+\1)+')


def _remove_quote_artifacts(text: str) -> str:
    """Remove empty or whitespace-only quotation mark pairs."""
    return _EMPTY_QUOTES.sub('', text)


def _remove_arabic_temporal_hallucinations(text: str) -> str:
    """Collapse chained Arabic temporal filler phrases, keeping one instance."""
    return _AR_TEMPORAL_HALLUCINATIONS.sub(lambda m: m.group().split('،')[0].split(',')[0].strip(), text)


def _remove_formatting_artifacts(text: str) -> str:
    """Remove orphan section numbers and collapse duplicated lines."""
    text = _ORPHAN_SECTION_NUMBERS.sub('', text)
    text = _DUPLICATED_LINES.sub(r'\1', text)
    return text


def _remove_repeated_phrases(text: str) -> str:
    """Collapse multi-word phrases repeated consecutively."""
    return _REPEATED_PHRASE.sub(r'\1', text)


# ---------------------------------------------------------------------------
# 6. Quality detection
# ---------------------------------------------------------------------------

def has_excessive_repetition(text: str) -> bool:
    """
    Return True if the text shows signs of hallucinated repetition that
    should trigger a regeneration attempt.
    """
    if not text or len(text) < 20:
        return True

    # Check for repeated n-gram patterns
    if _REPEATED_NGRAM.search(text):
        return True

    # Check for repeated Arabic words (3+ consecutive)
    if _REPEATED_AR_WORD.search(text):
        return True

    # Check word-level diversity
    words = text.split()
    if len(words) > 10:
        unique = set(w.lower() for w in words)
        if len(unique) / len(words) < 0.4:
            return True

    # Check for long runs of repeated consecutive words
    if len(words) > 5:
        repeat_count = 0
        for i in range(1, len(words)):
            if words[i].lower() == words[i - 1].lower():
                repeat_count += 1
        if repeat_count > len(words) * 0.3:
            return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_summary(text: str) -> str:
    """
    Full post-processing pipeline for a generated summary.

    1. Remove repeated character patterns
    2. Remove repeated consecutive words
    3. Remove duplicate sentences
    4. Remove output artifacts (quotes, Arabic temporal, formatting, phrases)
    5. Normalise whitespace
    """
    if not text:
        return text

    original_len = len(text)

    text = _remove_repeated_char_patterns(text)
    text = _remove_repeated_words(text)
    text = _remove_duplicate_sentences(text)

    # ── NEW: output artifact cleanup (reversible — remove these 4 lines to roll back) ──
    text = _remove_quote_artifacts(text)
    text = _remove_arabic_temporal_hallucinations(text)
    text = _remove_formatting_artifacts(text)
    text = _remove_repeated_phrases(text)

    text = _normalise_whitespace(text)

    cleaned_len = len(text)
    if original_len != cleaned_len:
        removed = original_len - cleaned_len
        logger.info(
            f"Post-processing removed {removed} chars "
            f"({original_len} → {cleaned_len})"
        )

    return text
