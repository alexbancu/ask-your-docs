"""Markdown document loader with metadata tagging for the RAG knowledge base."""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChunkDoc:
    """A lightweight document chunk replacing LangChain's Document class.

    Attributes:
        page_content: The text content of the chunk.
        metadata: Arbitrary metadata dict (source, type, section, etc.).
    """

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DemoConfig:
    """Configuration for a single demo loaded from demo.json.

    Attributes:
        name: Human-readable demo name.
        slug: Directory name / URL slug for the demo.
        documents: Mapping of filename stem to {type, owner} dicts.
    """

    name: str
    slug: str
    documents: dict[str, dict[str, str]]

    @property
    def filename_to_type(self) -> dict[str, str]:
        """Map of filename stem to document type."""
        return {k: v.get("type", "general") for k, v in self.documents.items()}

    @property
    def document_owners(self) -> dict[str, str]:
        """Map of filename stem to document owner."""
        return {k: v.get("owner", "Unknown") for k, v in self.documents.items()}


# Legacy hardcoded mappings — used as fallback when no demo config is available.
FILENAME_TO_TYPE: dict[str, str] = {
    "employee-handbook": "hr",
    "engineering-runbook": "engineering",
    "onboarding-guide": "onboarding",
    "product-docs": "product",
    "security-policy": "security",
}

DOCUMENT_OWNERS: dict[str, str] = {
    "employee-handbook": "HR Team",
    "engineering-runbook": "Platform Engineering",
    "onboarding-guide": "People Ops",
    "product-docs": "Product Management",
    "security-policy": "InfoSec Team",
}

STALE_THRESHOLD_DAYS = 180


def load_demo_config(demo_slug: str) -> DemoConfig:
    """Load a demo configuration from resources/{demo_slug}/demo.json.

    Args:
        demo_slug: The demo directory name (e.g. 'acme-corp').

    Returns:
        DemoConfig instance.

    Raises:
        FileNotFoundError: If demo.json does not exist.
    """
    config_path = Path("resources") / demo_slug / "demo.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Demo config not found: {config_path}")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return DemoConfig(
        name=data["name"],
        slug=demo_slug,
        documents=data.get("documents", {}),
    )


def list_demos() -> list[DemoConfig]:
    """List all available demos by scanning resources/*/demo.json.

    Returns:
        List of DemoConfig instances, sorted by slug.
    """
    resources = Path("resources")
    if not resources.exists():
        return []

    demos: list[DemoConfig] = []
    for demo_dir in sorted(resources.iterdir()):
        config_path = demo_dir / "demo.json"
        if demo_dir.is_dir() and config_path.exists():
            try:
                demos.append(load_demo_config(demo_dir.name))
            except Exception:
                logger.exception("Failed to load demo config from %s", demo_dir)
    return demos


def _filename_to_document_name(filename: str) -> str:
    """Convert a filename stem to a human-readable document name.

    Args:
        filename: File stem (without extension).

    Returns:
        Human-readable name.
    """
    return filename.replace("-", " ").title()


def _count_heading_level(text: str) -> int:
    """Find the current section number from markdown headings in text.

    Args:
        text: Text chunk to analyze.

    Returns:
        Last section number found, or 0 if none.
    """
    sections = re.findall(r"^##\s+(\d+)\.", text, re.MULTILINE)
    if sections:
        return int(sections[-1])
    return 0


def load_documents(
    directory: str | Path,
    demo_config: DemoConfig | None = None,
) -> list[ChunkDoc]:
    """Load and chunk all markdown files from a directory with metadata.

    Args:
        directory: Path to directory containing markdown files.
        demo_config: Optional demo config for type lookups. Falls back to
            hardcoded FILENAME_TO_TYPE when None.

    Returns:
        List of ChunkDoc objects with enriched metadata.

    Raises:
        FileNotFoundError: If directory does not exist.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    type_map = demo_config.filename_to_type if demo_config else FILENAME_TO_TYPE

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    all_documents: list[ChunkDoc] = []
    md_files = sorted(directory.glob("*.md"))

    if not md_files:
        logger.warning("No markdown files found in %s", directory)
        return []

    for md_file in md_files:
        stem = md_file.stem
        doc_name = _filename_to_document_name(stem)
        doc_type = type_map.get(stem, "general")

        content = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(content)

        for chunk in chunks:
            section_num = _count_heading_level(chunk)
            doc = ChunkDoc(
                page_content=chunk,
                metadata={
                    "source_document": doc_name,
                    "document_type": doc_type,
                    "section_number": section_num,
                    "source_file": md_file.name,
                },
            )
            all_documents.append(doc)

        logger.info(
            "Loaded %s: %d chunks (type=%s)", doc_name, len(chunks), doc_type
        )

    logger.info("Total: %d chunks from %d documents", len(all_documents), len(md_files))
    return all_documents


def _parse_last_updated(content: str) -> str | None:
    """Extract the 'Last updated: ...' date string from markdown content.

    Args:
        content: Raw markdown text.

    Returns:
        Date string (e.g. 'January 15, 2025') or None if not found.
    """
    match = re.search(r"Last updated:\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return None


def _is_stale(last_updated: str | None) -> bool:
    """Check if a document is stale (older than STALE_THRESHOLD_DAYS).

    Args:
        last_updated: Date string like 'January 15, 2025'.

    Returns:
        True if the date is more than STALE_THRESHOLD_DAYS ago, or if unparseable.
    """
    if not last_updated:
        return True
    try:
        date = datetime.strptime(last_updated, "%B %d, %Y")
        return (datetime.now() - date).days > STALE_THRESHOLD_DAYS
    except ValueError:
        return True


def load_full_document(
    directory: str | Path,
    slug: str,
    demo_config: DemoConfig | None = None,
) -> dict | None:
    """Read a single markdown file and return its content with metadata.

    Args:
        directory: Path to directory containing markdown files.
        slug: Filename stem (e.g. 'employee-handbook').
        demo_config: Optional demo config for type/owner lookups.

    Returns:
        Dict with name, slug, document_type, content, owner, last_updated,
        is_stale, and section_count. None if file not found.
    """
    directory = Path(directory)
    md_file = directory / f"{slug}.md"

    if not md_file.exists():
        return None

    type_map = demo_config.filename_to_type if demo_config else FILENAME_TO_TYPE
    owner_map = demo_config.document_owners if demo_config else DOCUMENT_OWNERS

    content = md_file.read_text(encoding="utf-8")
    last_updated = _parse_last_updated(content)
    sections = re.findall(r"^##\s+\d+\.", content, re.MULTILINE)

    return {
        "name": _filename_to_document_name(slug),
        "slug": slug,
        "document_type": type_map.get(slug, "general"),
        "content": content,
        "owner": owner_map.get(slug, "Unknown"),
        "last_updated": last_updated,
        "is_stale": _is_stale(last_updated),
        "section_count": len(sections),
    }
