import pytest
from unittest.mock import patch, MagicMock
from app.services.pdf_extractor import extract_text, clean_text
from app.application.use_cases import SummarizeDocumentUseCase

# Dummy PyMuPDF mock
class MockPage:
    def __init__(self, text):
        self._text = text
    def get_text(self, extraction_type="text", *args, **kwargs):
        if extraction_type == "blocks":
            return [(0, 0, 10, 10, self._text, 0, 0)]
        return self._text

class MockDoc:
    def __init__(self, pages):
        self._pages = pages
    def __len__(self):
        return len(self._pages)
    def __getitem__(self, idx):
        return self._pages[idx]

def test_clean_text_deduplication():
    # Make the formula longer than 15 chars to trigger the heavily-repeated filter
    raw_text = "Heading 1\nHeading 1\nData 1\nFormula A = B + C\nFormula A = B + C\nFormula A = B + C\nData 2\nFormula A = B + C"
    cleaned = clean_text(raw_text)
    # Consecutive duplicates should be removed, but non-consecutive kept
    assert "Heading 1\nData 1" in cleaned
    # We should have two instances of 'Formula A = B + C' since the last one is not consecutive
    assert cleaned.count("Formula A = B + C") == 2

def test_arabic_pdf_extraction():
    arabic_text = "هذا نص عربي للاختبار."
    doc = MockDoc([MockPage(arabic_text)])
    
    with patch('fitz.open', return_value=doc):
        text = extract_text(b"dummy pdf content")
        assert text == arabic_text

def test_english_pdf_extraction():
    english_text = "This is a simple English test."
    doc = MockDoc([MockPage(english_text)])
    
    with patch('fitz.open', return_value=doc):
        text = extract_text(b"dummy pdf content")
        assert text == english_text

def test_mathematical_pdf_extraction():
    # Add extra lines so len(lines) > 5, triggering clean_text's dedup logic
    math_text = "Line 1\nLine 2\nTheorem 1\nE=mc^2\nE=mc^2\nProof follows..."
    doc = MockDoc([MockPage(math_text)])
    
    with patch('fitz.open', return_value=doc):
        text = extract_text(b"dummy pdf content")
        # clean_text removes consecutive duplicates
        assert "Theorem 1\nE=mc^2\nProof follows..." in text

@pytest.mark.asyncio
async def test_empty_arabic_summary_raises_error():
    from unittest.mock import AsyncMock
    service_mock = AsyncMock()
    service_mock.summarize.return_value = "   " # Empty summary

    use_case = SummarizeDocumentUseCase(service_mock)

    # Text must be long enough (>=50 word chars) to pass the input quality gate
    long_arabic = "هذا نص عربي طويل بما يكفي لاجتياز فحص الجودة في خط أنابيب الاستخراج والمعالجة"

    with patch('app.application.use_cases.validate_pdf', return_value=1), \
         patch('app.application.use_cases.validate_page_range', return_value=(0, 1)), \
         patch('app.application.use_cases.extract_text', return_value=long_arabic):

        try:
            await use_case.execute(b"dummy", "test.pdf")
            assert False, "Should have raised SummarizationError"
        except Exception as e:
            assert "Summary generation failed" in str(e)

