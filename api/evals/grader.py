"""LLM-as-judge grader for RAG evaluation.

Uses Gemini to evaluate RAG answers with per-claim decomposition,
negation-aware forbidden claim checking, and deterministic source matching.

Architecture (based on RAGAS/DeepEval best practices):
- Factual accuracy: LLM evaluates each expected fact individually (semantic)
- Hallucination: LLM checks if forbidden claims are ASSERTED (negation-aware)
- Source attribution: Deterministic alias map + fuzzy matching (no LLM needed)
- Confidence: Deterministic comparison (no LLM needed)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

DEFAULT_GRADER_MODEL = "gemini-2.5-flash"

# --- Source name normalization ---

# Canonical name -> known aliases (lowercased)
SOURCE_ALIASES: dict[str, set[str]] = {
    "Employee Handbook": {
        "employee handbook", "emp handbook", "handbook",
    },
    "Engineering Runbook": {
        "engineering runbook", "eng runbook", "runbook",
    },
    "Product Documentation": {
        "product documentation", "product docs", "prod docs",
    },
    "Security Policy": {
        "security policy", "sec policy",
    },
    "Onboarding Guide": {
        "onboarding guide", "onboarding",
    },
}


def _normalize_source(name: str) -> str:
    """Normalize a source name to its canonical form.

    Args:
        name: Raw source name from RAG output or eval dataset.

    Returns:
        Canonical source name, or the original if no match found.
    """
    lower = name.lower().strip()
    for canonical, aliases in SOURCE_ALIASES.items():
        if lower == canonical.lower() or lower in aliases:
            return canonical
    return name


def _check_sources(
    expected_sources: list[str],
    answer: str,
    sources: list[dict[str, Any]],
) -> float:
    """Check source attribution using deterministic alias matching.

    A source is considered "found" if its canonical name appears in
    the answer text OR in the returned sources metadata.

    Args:
        expected_sources: List of expected source document names.
        answer: The RAG answer text.
        sources: List of source dicts from the RAG system.

    Returns:
        Proportion of expected sources found (0.0-1.0).
    """
    if not expected_sources:
        return 1.0

    # Build set of all source names mentioned (normalized)
    found_sources: set[str] = set()

    # From sources metadata
    for s in sources:
        raw_name = s.get("document_name", "")
        found_sources.add(_normalize_source(raw_name))

    # From answer text — check if canonical names appear
    answer_lower = answer.lower()
    for canonical in SOURCE_ALIASES:
        if canonical.lower() in answer_lower:
            found_sources.add(canonical)
        # Also check aliases in answer text
        for alias in SOURCE_ALIASES[canonical]:
            if alias in answer_lower:
                found_sources.add(canonical)

    matched = 0
    for expected in expected_sources:
        canonical_expected = _normalize_source(expected)
        if canonical_expected in found_sources:
            matched += 1

    return matched / len(expected_sources)


# --- LLM-based grading prompts ---

FACTUAL_GRADING_PROMPT = """\
You are a strict factual evaluator for a RAG system. Your job is to check \
whether specific expected facts are present in the RAG answer.

For each expected fact, determine if the answer conveys the SAME MEANING, \
even if the wording is different. Use semantic equivalence, not exact matching.

Examples of semantic equivalence:
- "20 days of PTO" matches "twenty days of paid time off"
- "4 hours resolution target" matches "Resolution target: 4 hours"
- "$99 per month" matches "$99/mo" or "ninety-nine dollars monthly"
- "100% match up to 4%" matches "full match on the first 4 percent"

Return a JSON object with:
{{
  "verdicts": [
    {{"fact": "<expected fact>", "found": true/false, "evidence": "<quote or explanation>"}}
  ],
  "forbidden_verdicts": [
    {{"claim": "<forbidden claim>", "asserted": true/false, "reasoning": "<explanation>"}}
  ]
}}

CRITICAL for forbidden claims:
- A forbidden claim is ONLY violated if the answer ASSERTS it as TRUE.
- If the answer DENIES or NEGATES a forbidden claim (e.g., "does NOT offer unlimited PTO"), \
that is NOT a violation. The answer is correctly refuting the claim.
- If the answer says "the policy is 20 days, not unlimited", that is NOT asserting "unlimited PTO".
- Only mark asserted=true if the answer genuinely states the forbidden claim as fact.

Return ONLY valid JSON. No markdown fences."""

FACTUAL_USER_TEMPLATE = """\
## RAG Answer
{answer}

## Expected Facts (check each one)
{expected_facts}

## Forbidden Claims (check if ASSERTED as true, not merely mentioned or denied)
{forbidden_claims}

Evaluate each fact and forbidden claim individually."""


@dataclass
class FactVerdict:
    """Verdict for a single expected fact.

    Attributes:
        fact: The expected fact text.
        found: Whether the fact was found in the answer.
        evidence: Quote or explanation supporting the verdict.
    """

    fact: str
    found: bool
    evidence: str


@dataclass
class ForbiddenVerdict:
    """Verdict for a single forbidden claim.

    Attributes:
        claim: The forbidden claim text.
        asserted: Whether the claim was asserted as true (not denied).
        reasoning: Explanation of the verdict.
    """

    claim: str
    asserted: bool
    reasoning: str


@dataclass
class GradeResult:
    """Structured result from grading a single RAG response.

    Attributes:
        eval_id: Identifier for the eval question.
        question: The question that was asked.
        category: Eval category (e.g. factual_accuracy, unanswerable).
        factual_score: Proportion of expected facts present (0.0-1.0).
        source_score: Proportion of expected sources found (0.0-1.0).
        hallucination_score: 1.0 if no forbidden claims asserted, 0.0 otherwise.
        confidence_correct: Whether confidence matches expected.
        overall_pass: True if all criteria met for the category.
        reasoning: Summary of grading reasoning.
        fact_verdicts: Per-fact verdict details.
        forbidden_verdicts: Per-forbidden-claim verdict details.
    """

    eval_id: str
    question: str
    category: str
    factual_score: float
    source_score: float
    hallucination_score: float
    confidence_correct: bool
    overall_pass: bool
    reasoning: str
    fact_verdicts: list[FactVerdict] = field(default_factory=list)
    forbidden_verdicts: list[ForbiddenVerdict] = field(default_factory=list)


def _parse_json_response(text: str) -> dict[str, Any]:
    """Parse JSON from the grader's response, handling markdown fences.

    Args:
        text: Raw response text that may contain JSON wrapped in markdown.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        ValueError: If JSON cannot be parsed.
    """
    cleaned = text.strip()

    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse grader JSON: {e}\nRaw: {text}") from e


def _grade_factual_and_hallucination(
    llm: ChatGoogleGenerativeAI,
    answer: str,
    expected_facts: list[str],
    forbidden_claims: list[str],
) -> tuple[list[FactVerdict], list[ForbiddenVerdict]]:
    """Use LLM to evaluate factual accuracy and forbidden claims.

    Single LLM call evaluates both dimensions with per-claim verdicts.
    Forbidden claim checking is negation-aware.

    Args:
        llm: Gemini LLM instance for grading.
        answer: The RAG answer text.
        expected_facts: List of facts that should be present.
        forbidden_claims: List of claims that should NOT be asserted.

    Returns:
        Tuple of (fact_verdicts, forbidden_verdicts).
    """
    facts_text = "\n".join(
        f"{i+1}. {f}" for i, f in enumerate(expected_facts)
    ) or "(none — unanswerable question)"

    forbidden_text = "\n".join(
        f"{i+1}. {c}" for i, c in enumerate(forbidden_claims)
    ) or "(none)"

    user_msg = FACTUAL_USER_TEMPLATE.format(
        answer=answer,
        expected_facts=facts_text,
        forbidden_claims=forbidden_text,
    )

    prompt = f"{FACTUAL_GRADING_PROMPT}\n\n{user_msg}"
    response = llm.invoke(prompt)
    scores = _parse_json_response(response.content)

    # Parse fact verdicts
    fact_verdicts: list[FactVerdict] = []
    for v in scores.get("verdicts", []):
        fact_verdicts.append(FactVerdict(
            fact=str(v.get("fact", "")),
            found=bool(v.get("found", False)),
            evidence=str(v.get("evidence", "")),
        ))

    # Parse forbidden claim verdicts
    forbidden_verdicts: list[ForbiddenVerdict] = []
    for v in scores.get("forbidden_verdicts", []):
        forbidden_verdicts.append(ForbiddenVerdict(
            claim=str(v.get("claim", "")),
            asserted=bool(v.get("asserted", False)),
            reasoning=str(v.get("reasoning", "")),
        ))

    return fact_verdicts, forbidden_verdicts


def _grade_unanswerable(
    llm: ChatGoogleGenerativeAI,
    answer: str,
    forbidden_claims: list[str],
) -> tuple[bool, list[ForbiddenVerdict], str]:
    """Evaluate an unanswerable question response.

    Checks that the answer declines gracefully and doesn't fabricate info.

    Args:
        llm: Gemini LLM instance for grading.
        answer: The RAG answer text.
        forbidden_claims: Claims that should NOT be asserted.

    Returns:
        Tuple of (declined_gracefully, forbidden_verdicts, reasoning).
    """
    prompt = f"""\
You are evaluating whether a RAG system correctly declined to answer \
a question it should not be able to answer.

## RAG Answer
{answer}

## Forbidden Claims (should NOT be asserted as true)
{chr(10).join(f'- {c}' for c in forbidden_claims) or '(none)'}

Evaluate:
1. Did the answer decline gracefully (said it doesn't have enough info, \
can't answer, etc.)? Or did it fabricate an answer?
2. For each forbidden claim: did the answer ASSERT it as true? \
(Mentioning it to deny it does NOT count as asserting.)

Return JSON:
{{
  "declined_gracefully": true/false,
  "forbidden_verdicts": [
    {{"claim": "...", "asserted": true/false, "reasoning": "..."}}
  ],
  "reasoning": "brief explanation"
}}

Return ONLY valid JSON. No markdown fences."""

    response = llm.invoke(prompt)
    scores = _parse_json_response(response.content)

    declined = bool(scores.get("declined_gracefully", False))
    reasoning = str(scores.get("reasoning", ""))

    forbidden_verdicts: list[ForbiddenVerdict] = []
    for v in scores.get("forbidden_verdicts", []):
        forbidden_verdicts.append(ForbiddenVerdict(
            claim=str(v.get("claim", "")),
            asserted=bool(v.get("asserted", False)),
            reasoning=str(v.get("reasoning", "")),
        ))

    return declined, forbidden_verdicts, reasoning


def grade_response(
    llm: ChatGoogleGenerativeAI,
    eval_entry: dict[str, Any],
    answer: str,
    sources: list[dict[str, Any]],
    actual_confidence: str,
) -> GradeResult:
    """Grade a single RAG response against evaluation criteria.

    Uses a hybrid approach:
    - LLM: per-claim factual evaluation + negation-aware forbidden claim checking
    - Deterministic: source matching (alias map) + confidence comparison

    Args:
        llm: LangChain Gemini LLM instance for grading.
        eval_entry: Entry from the eval dataset with expected criteria.
        answer: The RAG system's answer text.
        sources: List of source dicts returned by the RAG system.
        actual_confidence: Confidence level returned by RAG ("high" or "low").

    Returns:
        GradeResult with scores, verdicts, and pass/fail determination.

    Raises:
        ValueError: If grader response cannot be parsed.
    """
    expected_facts = eval_entry.get("expected_facts", [])
    expected_sources = eval_entry.get("expected_sources", [])
    forbidden_claims = eval_entry.get("forbidden_claims", [])
    expected_confidence = eval_entry.get("expected_confidence", "high")
    category = eval_entry.get("category", "unknown")

    # --- Deterministic checks ---
    source_score = _check_sources(expected_sources, answer, sources)
    confidence_correct = actual_confidence == expected_confidence

    # --- LLM-based checks ---
    if category == "unanswerable":
        declined, forbidden_verdicts, reasoning = _grade_unanswerable(
            llm, answer, forbidden_claims,
        )
        any_asserted = any(v.asserted for v in forbidden_verdicts)
        hallucination_score = 0.0 if any_asserted else 1.0
        overall_pass = declined and hallucination_score == 1.0 and actual_confidence == "low"

        return GradeResult(
            eval_id=eval_entry["id"],
            question=eval_entry["question"],
            category=category,
            factual_score=1.0 if declined else 0.0,
            source_score=source_score,
            hallucination_score=hallucination_score,
            confidence_correct=confidence_correct,
            overall_pass=overall_pass,
            reasoning=reasoning,
            fact_verdicts=[],
            forbidden_verdicts=forbidden_verdicts,
        )

    # Answerable questions: evaluate facts + forbidden claims
    fact_verdicts, forbidden_verdicts = _grade_factual_and_hallucination(
        llm, answer, expected_facts, forbidden_claims,
    )

    # Compute factual score from per-fact verdicts
    if expected_facts:
        facts_found = sum(1 for v in fact_verdicts if v.found)
        factual_score = facts_found / len(expected_facts)
    else:
        factual_score = 1.0

    # Hallucination: 1.0 if no forbidden claims asserted
    any_asserted = any(v.asserted for v in forbidden_verdicts)
    hallucination_score = 0.0 if any_asserted else 1.0

    # Build reasoning summary
    failed_facts = [v.fact for v in fact_verdicts if not v.found]
    asserted_forbidden = [v.claim for v in forbidden_verdicts if v.asserted]
    reasoning_parts: list[str] = []
    if failed_facts:
        reasoning_parts.append(f"Missing facts: {failed_facts}")
    if asserted_forbidden:
        reasoning_parts.append(f"Forbidden claims asserted: {asserted_forbidden}")
    if source_score < 1.0:
        reasoning_parts.append(f"Source score: {source_score:.1f}")
    if not confidence_correct:
        reasoning_parts.append(
            f"Confidence mismatch: actual={actual_confidence}, expected={expected_confidence}"
        )
    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "All checks passed"

    overall_pass = (
        factual_score >= 0.8
        and hallucination_score == 1.0
        and source_score >= 0.5
    )

    return GradeResult(
        eval_id=eval_entry["id"],
        question=eval_entry["question"],
        category=category,
        factual_score=factual_score,
        source_score=source_score,
        hallucination_score=hallucination_score,
        confidence_correct=confidence_correct,
        overall_pass=overall_pass,
        reasoning=reasoning,
        fact_verdicts=fact_verdicts,
        forbidden_verdicts=forbidden_verdicts,
    )
