"""CLI runner for RAG evaluation suite.

Runs the live RAG pipeline against a curated eval dataset,
grades each answer using Gemini as a judge, and produces a
pass/fail report with category breakdowns.

Usage:
    uv run python -m api.evals.run_eval          # full suite
    uv run python -m api.evals.run_eval -v        # verbose (show reasoning)
    uv run python -m api.evals.run_eval --category unanswerable
"""

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from api.config import CloudConfig, load_config
from api.evals.grader import DEFAULT_GRADER_MODEL, GradeResult, grade_response
from api.rag_service import CloudRAGService

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "eval_dataset.json"


def load_dataset(
    path: Path, category: str | None = None
) -> list[dict]:
    """Load eval dataset, optionally filtered by category.

    Args:
        path: Path to the eval dataset JSON file.
        category: Optional category to filter by.

    Returns:
        List of eval entries.
    """
    with open(path) as f:
        dataset = json.load(f)

    if category:
        dataset = [e for e in dataset if e["category"] == category]

    return dataset


def _create_grader_llm(config: CloudConfig, model: str) -> ChatGoogleGenerativeAI:
    """Create the Gemini LLM instance used for grading.

    Args:
        config: Cloud configuration with Google API key.
        model: Gemini model name.

    Returns:
        ChatGoogleGenerativeAI instance.
    """
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=config.google_api_key,
        temperature=0,
    )


def run_single_eval(
    service: CloudRAGService,
    grader_llm: ChatGoogleGenerativeAI,
    entry: dict,
) -> GradeResult:
    """Run a single eval: ask the RAG system, then grade the response.

    Args:
        service: Live RAG service instance.
        grader_llm: Gemini LLM for grading.
        entry: Eval dataset entry.

    Returns:
        GradeResult with scores.
    """
    response = service.ask(entry["question"])

    sources = [s.model_dump() for s in response.sources]

    return grade_response(
        llm=grader_llm,
        eval_entry=entry,
        answer=response.answer,
        sources=sources,
        actual_confidence=response.confidence,
    )


def print_result(result: GradeResult, verbose: bool = False) -> None:
    """Print a single eval result.

    Args:
        result: The graded result.
        verbose: Whether to show detailed reasoning.
    """
    status = "PASS" if result.overall_pass else "FAIL"
    print(
        f"  [{status}] {result.eval_id:<35} "
        f"factual={result.factual_score:.1f}  "
        f"source={result.source_score:.1f}  "
        f"halluc={result.hallucination_score:.1f}  "
        f"conf={'ok' if result.confidence_correct else 'wrong'}"
    )
    if verbose:
        print(f"         {result.reasoning}")
        for fv in result.fact_verdicts:
            mark = "+" if fv.found else "-"
            print(f"           [{mark}] {fv.fact}: {fv.evidence[:80]}")
        for bv in result.forbidden_verdicts:
            mark = "!" if bv.asserted else "ok"
            print(f"           [{mark}] forbidden: {bv.claim}: {bv.reasoning[:80]}")


def print_summary(results: list[GradeResult], elapsed: float) -> None:
    """Print evaluation summary with category breakdown.

    Args:
        results: All graded results.
        elapsed: Total elapsed time in seconds.
    """
    total = len(results)
    passed = sum(1 for r in results if r.overall_pass)
    pass_rate = passed / total if total > 0 else 0

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed}/{total} passed ({pass_rate:.0%})")
    print(f"Time: {elapsed:.1f}s")
    print("=" * 70)

    # Category breakdown
    by_category: dict[str, list[GradeResult]] = defaultdict(list)
    for r in results:
        by_category[r.category].append(r)

    print(f"\n{'Category':<25} {'Pass Rate':<12} {'Avg Factual':<14} {'Avg Source':<12}")
    print("-" * 65)
    for cat in sorted(by_category):
        cat_results = by_category[cat]
        cat_passed = sum(1 for r in cat_results if r.overall_pass)
        cat_total = len(cat_results)
        avg_factual = sum(r.factual_score for r in cat_results) / cat_total
        avg_source = sum(r.source_score for r in cat_results) / cat_total
        print(
            f"  {cat:<23} {cat_passed}/{cat_total:<9} "
            f"{avg_factual:<14.2f} {avg_source:<12.2f}"
        )

    # Average scores
    avg_factual = sum(r.factual_score for r in results) / total
    avg_source = sum(r.source_score for r in results) / total
    avg_halluc = sum(r.hallucination_score for r in results) / total
    conf_correct = sum(1 for r in results if r.confidence_correct)

    print(f"\nAverage scores:")
    print(f"  Factual:       {avg_factual:.2f}")
    print(f"  Source:        {avg_source:.2f}")
    print(f"  Hallucination: {avg_halluc:.2f}")
    print(f"  Confidence:    {conf_correct}/{total} correct")


def main() -> None:
    """Run the eval suite."""
    parser = argparse.ArgumentParser(description="RAG Evaluation Runner")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help="Path to eval dataset JSON",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter to a specific category",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Minimum pass rate (0.0-1.0) for exit code 0",
    )
    parser.add_argument(
        "--grader-model",
        type=str,
        default=DEFAULT_GRADER_MODEL,
        help="Gemini model for grading",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show grader reasoning for each question",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Load dataset
    dataset = load_dataset(args.dataset, args.category)
    if not dataset:
        print(f"No eval entries found (category={args.category})")
        sys.exit(1)

    print(f"Running {len(dataset)} eval questions...")
    if args.category:
        print(f"  Category filter: {args.category}")
    print(f"  Grader model: {args.grader_model}")
    print()

    # Initialize services
    config = load_config()
    service = CloudRAGService(config)
    grader_llm = _create_grader_llm(config, args.grader_model)

    # Run evals
    results: list[GradeResult] = []
    start = time.time()

    for i, entry in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] {entry['question'][:60]}...")
        try:
            result = run_single_eval(service, grader_llm, entry)
            results.append(result)
            print_result(result, args.verbose)
        except Exception:
            logger.exception("Failed to evaluate: %s", entry["id"])
            print(f"  [ERROR] {entry['id']}: evaluation failed")

    elapsed = time.time() - start

    if not results:
        print("No results to report.")
        sys.exit(1)

    print_summary(results, elapsed)

    # Exit code based on threshold
    pass_rate = sum(1 for r in results if r.overall_pass) / len(results)
    if pass_rate < args.threshold:
        print(f"\nFAILED: pass rate {pass_rate:.0%} < threshold {args.threshold:.0%}")
        sys.exit(1)
    else:
        print(f"\nPASSED: pass rate {pass_rate:.0%} >= threshold {args.threshold:.0%}")
        sys.exit(0)


if __name__ == "__main__":
    main()
