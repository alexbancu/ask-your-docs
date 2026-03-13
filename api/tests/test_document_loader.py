"""Tests for the markdown document loader."""

import tempfile
from pathlib import Path

import pytest

from api.document_loader import (
    _count_heading_level,
    _filename_to_document_name,
    load_documents,
)


class TestFilenameToDocumentName:
    """Tests for filename to document name conversion."""

    def test_basic_conversion(self) -> None:
        """Test basic filename conversion."""
        assert _filename_to_document_name("employee-handbook") == "Employee Handbook"

    def test_single_word(self) -> None:
        """Test single word filename."""
        assert _filename_to_document_name("readme") == "Readme"

    def test_multiple_hyphens(self) -> None:
        """Test filename with multiple hyphens."""
        assert _filename_to_document_name("my-long-document-name") == "My Long Document Name"


class TestCountHeadingLevel:
    """Tests for section number extraction from headings."""

    def test_finds_section_number(self) -> None:
        """Test extracting section number from heading."""
        text = "## 3. Remote Work Policy\n\nSome content here."
        assert _count_heading_level(text) == 3

    def test_no_heading(self) -> None:
        """Test text without headings returns 0."""
        text = "Just some plain text without headings."
        assert _count_heading_level(text) == 0

    def test_multiple_headings_returns_last(self) -> None:
        """Test that the last section number is returned."""
        text = "## 1. First\n\nContent\n\n## 2. Second\n\nMore content"
        assert _count_heading_level(text) == 2


class TestLoadDocuments:
    """Tests for document loading."""

    def test_load_markdown_files(self) -> None:
        """Test loading markdown files with metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_file = Path(tmpdir) / "employee-handbook.md"
            md_file.write_text(
                "# Employee Handbook\n\n"
                "## 1. Welcome\n\n"
                "Welcome to the company.\n\n"
                "## 2. PTO Policy\n\n"
                "You get 20 days of PTO.\n"
            )

            docs = load_documents(tmpdir)

            assert len(docs) > 0
            assert all(d.metadata["source_document"] == "Employee Handbook" for d in docs)
            assert all(d.metadata["document_type"] == "hr" for d in docs)
            assert all(d.metadata["source_file"] == "employee-handbook.md" for d in docs)

    def test_load_multiple_files(self) -> None:
        """Test loading multiple markdown files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "employee-handbook.md").write_text("# Handbook\n\nContent")
            (Path(tmpdir) / "security-policy.md").write_text("# Security\n\nContent")

            docs = load_documents(tmpdir)

            doc_names = {d.metadata["source_document"] for d in docs}
            assert "Employee Handbook" in doc_names
            assert "Security Policy" in doc_names

    def test_load_unknown_filename_type(self) -> None:
        """Test that unknown filenames get 'general' type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "random-doc.md").write_text("# Random\n\nContent")

            docs = load_documents(tmpdir)

            assert docs[0].metadata["document_type"] == "general"

    def test_load_empty_directory(self) -> None:
        """Test loading from empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs = load_documents(tmpdir)
            assert docs == []

    def test_load_nonexistent_directory(self) -> None:
        """Test loading from nonexistent directory raises error."""
        with pytest.raises(FileNotFoundError):
            load_documents("/nonexistent/path")

    def test_chunks_have_content(self) -> None:
        """Test that loaded chunks have non-empty content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "employee-handbook.md").write_text(
                "# Handbook\n\n## 1. Section\n\n" + "Content. " * 100
            )

            docs = load_documents(tmpdir)

            assert all(len(d.page_content) > 0 for d in docs)
