"""Pytest wrapper for RAG evaluation suite.

Parametrized tests — one test case per eval question.
Marked with @pytest.mark.eval so they're excluded from normal pytest runs.

Usage:
    uv run pytest api/evals/test_eval.py -v -m eval        # run all
    uv run pytest api/evals/test_eval.py -v -m eval -k pto  # run one
"""

import json
import os
from pathlib import Path

import pytest

DATASET_PATH = Path(__file__).parent / "eval_dataset.json"


def _load_dataset() -> list[dict]:
    """Load the eval dataset for parametrization."""
    with open(DATASET_PATH) as f:
        return json.load(f)


def _requires_api_keys() -> bool:
    """Check if all required API keys are set."""
    return all(
        os.getenv(key)
        for key in ("GOOGLE_API_KEY", "PINECONE_API_KEY")
    )


# Load dataset at module level for parametrize
_dataset = _load_dataset()


@pytest.mark.eval
@pytest.mark.parametrize(
    "eval_entry",
    _dataset,
    ids=[e["id"] for e in _dataset],
)
def test_eval_question(eval_entry: dict) -> None:
    """Test a single eval question against the live RAG pipeline.

    Args:
        eval_entry: Eval dataset entry with question and criteria.
    """
    if not _requires_api_keys():
        pytest.skip("Missing required API keys (GOOGLE_API_KEY, PINECONE_API_KEY)")

    from langchain_google_genai import ChatGoogleGenerativeAI

    from api.config import load_config
    from api.evals.grader import DEFAULT_GRADER_MODEL, grade_response
    from api.rag_service import CloudRAGService

    config = load_config()
    service = CloudRAGService(config)
    grader_llm = ChatGoogleGenerativeAI(
        model=DEFAULT_GRADER_MODEL,
        google_api_key=config.google_api_key,
        temperature=0,
    )

    response = service.ask(eval_entry["question"])
    sources = [s.model_dump() for s in response.sources]

    result = grade_response(
        llm=grader_llm,
        eval_entry=eval_entry,
        answer=response.answer,
        sources=sources,
        actual_confidence=response.confidence,
    )

    assert result.overall_pass, (
        f"Eval '{eval_entry['id']}' failed: "
        f"factual={result.factual_score:.1f}, "
        f"source={result.source_score:.1f}, "
        f"halluc={result.hallucination_score:.1f} — "
        f"{result.reasoning}"
    )
