from app.reports.extraction.docling_content_guard import (
    MIN_USABLE_CONTENT_CHARS,
    UNREADABLE_DOCUMENT_LOW_CONTENT,
    assess_docling_usable,
)


def test_failure_status_is_unreadable():
    assessment = assess_docling_usable(
        {
            "conversion_status": "failure",
            "text": "x" * 500,
        }
    )
    assert assessment is not None
    assert assessment.reason == "conversion_failure"


def test_skipped_status_is_unreadable():
    assessment = assess_docling_usable(
        {
            "conversion_status": "skipped",
            "text": "enough text " * 50,
        }
    )
    assert assessment is not None
    assert assessment.reason == "conversion_failure"


def test_low_content_below_floor_is_unreadable():
    assessment = assess_docling_usable(
        {
            "conversion_status": "success",
            "text": "# Header only\n",
        }
    )
    assert assessment is not None
    assert assessment.reason == "low_content"
    assert assessment.content_chars < MIN_USABLE_CONTENT_CHARS


def test_partial_success_above_floor_is_usable():
    text = "Grant letter body. " * 20
    assert len(text.strip()) >= MIN_USABLE_CONTENT_CHARS
    assert assess_docling_usable(
        {
            "conversion_status": "partial_success",
            "text": text,
        }
    ) is None


def test_success_above_floor_is_usable():
    text = "Valid grant terms excerpt. " * 15
    assert assess_docling_usable(
        {
            "conversion_status": "success",
            "text": text,
        }
    ) is None


def test_machine_code_constant():
    assert UNREADABLE_DOCUMENT_LOW_CONTENT == "UNREADABLE_DOCUMENT_LOW_CONTENT"
