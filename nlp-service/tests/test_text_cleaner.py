"""
Tests for post-processing text cleaner (app.utils.text_cleaner).

Covers:
  - Existing rules (regression)
  - NEW Rule 5a: Empty / duplicated quotation marks
  - NEW Rule 5b: Arabic hallucinated temporal phrases
  - NEW Rule 5c: Orphan section numbers
  - NEW Rule 5d: Duplicated consecutive lines
  - NEW Rule 5e: Repeated multi-word phrases
  - Full pipeline integration
  - Latency benchmark
"""

import time
import pytest
from app.utils.text_cleaner import (
    clean_summary,
    has_excessive_repetition,
    _remove_quote_artifacts,
    _remove_arabic_temporal_hallucinations,
    _remove_formatting_artifacts,
    _remove_repeated_phrases,
)


# ═══════════════════════════════════════════════════════════════════════════
# Regression tests — existing rules must still work
# ═══════════════════════════════════════════════════════════════════════════

class TestExistingRulesRegression:
    """Ensure the pre-existing cleanup rules are not broken."""

    def test_repeated_ngrams_removed(self):
        assert clean_summary("OSOSOS hello") == "hello"

    def test_repeated_char_collapsed(self):
        result = clean_summary("AAAA world")
        assert "AAAA" not in result
        assert "A world" == result

    def test_repeated_arabic_word(self):
        result = clean_summary("دبي دبي دبي هي مدينة جميلة ورائعة")
        assert result.count("دبي") == 1

    def test_trailing_noise_removed(self):
        result = clean_summary("Summary text 11 121 34")
        assert result == "Summary text"

    def test_consecutive_duplicate_words(self):
        result = clean_summary("the the cat sat on the the mat")
        assert result == "the cat sat on the mat"

    def test_duplicate_sentences(self):
        result = clean_summary("Hello world. Hello world. Goodbye.")
        assert result.count("Hello world") == 1
        assert "Goodbye" in result

    def test_whitespace_normalised(self):
        result = clean_summary("hello   world\n\n\n\nfoo")
        assert result == "hello world\n\nfoo"

    def test_empty_input_passthrough(self):
        assert clean_summary("") == ""
        assert clean_summary(None) is None

    def test_clean_text_unchanged(self):
        clean = "This is a perfectly clean summary with no artifacts."
        assert clean_summary(clean) == clean


# ═══════════════════════════════════════════════════════════════════════════
# NEW Rule 5a — Empty / duplicated quotation marks
# ═══════════════════════════════════════════════════════════════════════════

class TestEmptyQuotes:
    """Rule 5a: empty or whitespace-only quotation mark pairs."""

    def test_empty_double_quotes(self):
        assert _remove_quote_artifacts('hello "" world') == "hello  world"

    def test_empty_single_quotes(self):
        assert _remove_quote_artifacts("hello '' world") == "hello  world"

    def test_empty_guillemets(self):
        assert _remove_quote_artifacts("hello «» world") == "hello  world"

    def test_empty_curly_quotes(self):
        assert _remove_quote_artifacts("hello \u201c\u201d world") == "hello  world"

    def test_curly_quotes_with_whitespace(self):
        assert _remove_quote_artifacts("hello \u201c  \u201d world") == "hello  world"

    def test_real_quotes_kept(self):
        text = 'He said "hello" to the world'
        assert _remove_quote_artifacts(text) == text

    def test_arabic_quotes_kept(self):
        text = "«النص العربي»"
        assert _remove_quote_artifacts(text) == text


# ═══════════════════════════════════════════════════════════════════════════
# NEW Rule 5b — Arabic hallucinated temporal phrases
# ═══════════════════════════════════════════════════════════════════════════

class TestArabicTemporalHallucinations:
    """Rule 5b: chained Arabic temporal/transition fillers."""

    def test_single_phrase_kept(self):
        text = "في الوقت الحالي يتم العمل"
        assert _remove_arabic_temporal_hallucinations(text) == text

    def test_two_chained_collapsed(self):
        text = "في الوقت الحالي، في الوقت نفسه يتم العمل"
        result = _remove_arabic_temporal_hallucinations(text)
        assert "في الوقت الحالي" in result
        assert "في الوقت نفسه" not in result

    def test_three_chained_collapsed(self):
        text = "في الوقت الحالي، على صعيد آخر، من جهة أخرى يتم العمل"
        result = _remove_arabic_temporal_hallucinations(text)
        assert result.count("في الوقت الحالي") == 1
        assert "على صعيد آخر" not in result
        assert "من جهة أخرى" not in result

    def test_comma_variant(self):
        text = "في الوقت الحالي, في الوقت نفسه يتم العمل"
        result = _remove_arabic_temporal_hallucinations(text)
        assert "في الوقت نفسه" not in result

    def test_english_unaffected(self):
        text = "Meanwhile, on the other hand, furthermore"
        assert _remove_arabic_temporal_hallucinations(text) == text


# ═══════════════════════════════════════════════════════════════════════════
# NEW Rule 5c — Orphan section numbers
# ═══════════════════════════════════════════════════════════════════════════

class TestOrphanSectionNumbers:
    """Rule 5c: standalone section numbers on their own line."""

    def test_orphan_single_number(self):
        text = "Summary\n1.\nMore text"
        result = _remove_formatting_artifacts(text)
        assert "1." not in result
        assert "Summary" in result
        assert "More text" in result

    def test_orphan_compound_number(self):
        text = "Summary\n2.3.\nMore text"
        result = _remove_formatting_artifacts(text)
        assert "2.3." not in result

    def test_number_with_heading_kept(self):
        text = "Summary\n1. Introduction\nMore text"
        result = _remove_formatting_artifacts(text)
        assert "1. Introduction" in result

    def test_inline_number_kept(self):
        text = "See section 1. for details"
        result = _remove_formatting_artifacts(text)
        assert "1." in result


# ═══════════════════════════════════════════════════════════════════════════
# NEW Rule 5d — Duplicated consecutive lines
# ═══════════════════════════════════════════════════════════════════════════

class TestDuplicatedLines:
    """Rule 5d: exact consecutive duplicate lines."""

    def test_duplicate_heading(self):
        text = "Introduction\nIntroduction\nSome content"
        result = _remove_formatting_artifacts(text)
        assert result.count("Introduction") == 1
        assert "Some content" in result

    def test_non_consecutive_duplicates_kept(self):
        text = "Introduction\nSome content\nIntroduction"
        result = _remove_formatting_artifacts(text)
        assert result.count("Introduction") == 2

    def test_no_duplicates(self):
        text = "Line one\nLine two\nLine three"
        result = _remove_formatting_artifacts(text)
        assert result == text


# ═══════════════════════════════════════════════════════════════════════════
# NEW Rule 5e — Repeated multi-word phrases
# ═══════════════════════════════════════════════════════════════════════════

class TestRepeatedPhrases:
    """Rule 5e: multi-word phrases repeated consecutively."""

    def test_three_word_phrase_repeated(self):
        text = "the study shows the study shows some results"
        result = _remove_repeated_phrases(text)
        assert result.count("the study shows") == 1
        assert "some results" in result

    def test_long_phrase_repeated(self):
        text = "this is a very important result this is a very important result for science"
        result = _remove_repeated_phrases(text)
        assert result.count("this is a very important result") == 1

    def test_arabic_phrase_repeated(self):
        text = "تشير الدراسة إلى تشير الدراسة إلى نتائج مهمة"
        result = _remove_repeated_phrases(text)
        assert result.count("تشير الدراسة إلى") == 1

    def test_non_repeated_phrases_kept(self):
        text = "the cat sat on the mat and the dog ran"
        result = _remove_repeated_phrases(text)
        assert result == text


# ═══════════════════════════════════════════════════════════════════════════
# Full pipeline integration
# ═══════════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    """End-to-end clean_summary with combined artifacts."""

    def test_combined_english_artifacts(self):
        dirty = (
            'The "" results show the results show that AI is important.\n'
            '1.\n'
            'Introduction\n'
            'Introduction\n'
            'AI is the future   of   technology.'
        )
        result = clean_summary(dirty)
        # Empty quotes removed
        assert '""' not in result
        # Orphan section number removed
        assert '\n1.\n' not in result
        # Duplicate heading collapsed
        assert result.count("Introduction") == 1
        # Multi-space normalised
        assert "   " not in result

    def test_combined_arabic_artifacts(self):
        dirty = (
            "الذكاء الاصطناعي «» مهم جداً. "
            "في الوقت الحالي، في الوقت نفسه، على صعيد آخر يتطور بسرعة."
        )
        result = clean_summary(dirty)
        # Empty guillemets removed
        assert "«»" not in result
        # Temporal chain collapsed
        assert "في الوقت نفسه" not in result
        assert "على صعيد آخر" not in result

    def test_clean_english_unchanged(self):
        clean = (
            "Artificial intelligence refers to the simulation of human intelligence "
            "in machines that are programmed to think and learn."
        )
        assert clean_summary(clean) == clean

    def test_clean_arabic_unchanged(self):
        clean = "الذكاء الاصطناعي هو محاكاة للذكاء البشري في الآلات المبرمجة للتفكير والتعلم."
        assert clean_summary(clean) == clean


# ═══════════════════════════════════════════════════════════════════════════
# Quality detection (existing — regression)
# ═══════════════════════════════════════════════════════════════════════════

class TestQualityDetection:
    def test_good_text_passes(self):
        assert has_excessive_repetition(
            "This is a well-written summary about AI and technology advancements."
        ) is False

    def test_empty_text_fails(self):
        assert has_excessive_repetition("") is True

    def test_short_text_fails(self):
        assert has_excessive_repetition("short") is True


# ═══════════════════════════════════════════════════════════════════════════
# Latency benchmark (callable from CLI)
# ═══════════════════════════════════════════════════════════════════════════

# --- Test inputs for before/after comparison ---
ENGLISH_DIRTY = (
    'The "" results show the results show that AI is important.\n'
    '1.\n'
    'Introduction\n'
    'Introduction\n'
    'AI is the future   of   technology.\n'
    "The study demonstrates the study demonstrates significant progress."
)

ARABIC_DIRTY = (
    "الذكاء الاصطناعي «» مهم جداً.\n"
    "2.\n"
    "المقدمة\n"
    "المقدمة\n"
    "في الوقت الحالي، في الوقت نفسه، على صعيد آخر يتطور بسرعة.\n"
    "تشير الدراسة إلى تشير الدراسة إلى نتائج مهمة."
)


def benchmark_cleaner(iterations: int = 5000):
    """Run clean_summary N times and report latency stats."""
    import statistics

    samples = {
        "English (dirty)": ENGLISH_DIRTY,
        "Arabic (dirty)": ARABIC_DIRTY,
        "English (clean)": "Artificial intelligence refers to the simulation of human intelligence in machines.",
        "Arabic (clean)": "الذكاء الاصطناعي هو محاكاة للذكاء البشري في الآلات المبرمجة.",
    }

    print(f"\n{'='*70}")
    print(f"  Latency Benchmark — {iterations} iterations per sample")
    print(f"{'='*70}\n")

    for label, text in samples.items():
        timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            clean_summary(text)
            elapsed = (time.perf_counter() - start) * 1_000_000  # microseconds
            timings.append(elapsed)

        avg = statistics.mean(timings)
        p50 = statistics.median(timings)
        p99 = sorted(timings)[int(len(timings) * 0.99)]

        print(f"  {label}:")
        print(f"    avg = {avg:.1f} µs | p50 = {p50:.1f} µs | p99 = {p99:.1f} µs\n")


def show_before_after():
    """Print before/after comparison for English and Arabic dirty inputs."""
    print(f"\n{'='*70}")
    print("  BEFORE / AFTER Comparison")
    print(f"{'='*70}")

    for label, dirty in [("ENGLISH", ENGLISH_DIRTY), ("ARABIC", ARABIC_DIRTY)]:
        cleaned = clean_summary(dirty)
        print(f"\n  ── {label} ──")
        print(f"\n  BEFORE ({len(dirty)} chars):")
        for line in dirty.split('\n'):
            print(f"    │ {line}")
        print(f"\n  AFTER  ({len(cleaned)} chars):")
        for line in cleaned.split('\n'):
            print(f"    │ {line}")
        removed = len(dirty) - len(cleaned)
        print(f"\n    Removed: {removed} chars ({removed/len(dirty)*100:.1f}%)")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    show_before_after()
    benchmark_cleaner()
