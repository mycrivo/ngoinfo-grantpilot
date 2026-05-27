import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.reports.extraction.docling_adapter import extract_text_from_path


def test_extract_text_from_path_returns_structured_result(tmp_path: Path):
    doc_path = tmp_path / "sample.txt"
    doc_path.write_text("hello", encoding="utf-8")

    mock_document = MagicMock()
    mock_document.export_to_markdown.return_value = "# Sample\n\nhello"
    mock_document.pages = []

    mock_result = MagicMock()
    mock_result.document = mock_document
    mock_status = MagicMock()
    mock_status.value = "success"
    mock_result.status = mock_status
    mock_result.errors = []

    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result

    mock_converter_class = MagicMock(return_value=mock_converter)
    fake_docling_converter = MagicMock()
    fake_docling_converter.DocumentConverter = mock_converter_class

    with patch.dict(
        sys.modules,
        {
            "docling": MagicMock(),
            "docling.document_converter": fake_docling_converter,
        },
    ):
        result = extract_text_from_path(doc_path)

    assert result["text"] == "# Sample\n\nhello"
    assert result["metadata"]["source_path"] == str(doc_path)
    assert result["metadata"]["page_count"] == 0
    assert result["conversion_status"] == "success"
    assert result["conversion_errors"] == []
    mock_converter.convert.assert_called_once_with(str(doc_path))
