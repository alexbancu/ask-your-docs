# RAG System Improvement Plan: ask-your-docs

## Context

This plan addresses the gap between "demo that works" and "system clients trust and pay for." Based on web research, clients care most about: answer accuracy, hallucination prevention, source traceability, evaluation metrics, production reliability, and security. The current system has solid foundations (typed code, good tests, source attribution, confidence scoring) but lacks the production hardening and quality measurement layers that differentiate a paid product.

The improvements are ordered by impact-to-effort ratio — quick wins first, strategic investments last.

---

## Tier 1: Quick Wins (0.5–2 days each)

### 1. Structured Logging with Request IDs

- **What**: JSON structured logging + unique request ID per HTTP request via middleware
- **Why clients care**: Production debugging is impossible without request tracing. Table-stakes for any client evaluation
- **How**: Add `python-json-logger` dep. Create `api/middleware.py` with `RequestIDMiddleware` using `contextvars.ContextVar` + `uuid4()`. Replace `logging.basicConfig` in `api/app.py` with JSON formatter. Log structured fields in `api/rag_service.py` (`question_length`, `top_score`, `num_relevant`, `confidence`). Add latency tracking with `time.perf_counter()` in `api/routes.py`
- **Effort**: 1 day
- **Impact**: High trust, Medium UX (indirect), Low answer quality
- **Dependencies**: None

### 2. Query Result Caching

- **What**: In-memory TTL cache for identical queries to avoid redundant Pinecone + Gemini calls
- **Why clients care**: Instant responses for repeated questions. Protects Gemini's 15 RPM free-tier limit
- **How**: Add `cachetools` dep. Add `TTLCache(maxsize=256, ttl=3600)` to `CloudRAGService.__init__` in `api/rag_service.py`. Cache key = `question.strip().lower()`. Add `POST /cache/clear` admin endpoint in `api/routes.py`. Log cache hits/misses as structured events
- **Effort**: 0.5 days
- **Impact**: High UX, Medium trust, Low answer quality
- **Dependencies**: None

### 3. Rate Limiting

- **What**: Per-IP and global rate limiting on `/ask` endpoint
- **Why clients care**: Prevents single user/bot from exhausting Gemini quota and causing 429s for everyone
- **How**: Add `slowapi` dep. Configure `Limiter(key_func=get_remote_address)` in `api/app.py`. Decorate `/ask` with `@limiter.limit("10/minute")` per IP, global 14/minute. Add env-configurable limits to `api/config.py`. Return 429 with `Retry-After` header
- **Effort**: 0.5 days
- **Impact**: High trust, Low UX, Low answer quality
- **Dependencies**: None

### 4. User Feedback Mechanism (Thumbs Up/Down)

- **What**: Thumbs up/down on each answer. Store feedback for quality tracking
- **Why clients care**: Enables reporting "92% of answers rated helpful." Identifies bad answers for fixing. Without this, you're blind on quality
- **How**: Add `FeedbackRequest` model to `api/models.py` (question, answer_id, rating, optional comment). Add `POST /feedback` endpoint in `api/routes.py`. Log as structured JSON. Add `answer_id: str` (UUID) to `AskResponse`. Create `FeedbackButtons.tsx` component, embed in `MessageBubble.tsx` below answers. Add `feedbackGiven` state to `Message` type. Add `submitFeedback()` to `frontend/src/api/client.ts`
- **Effort**: 1 day
- **Impact**: High trust, Medium answer quality (future), Low UX
- **Dependencies**: Structured logging (1) makes feedback data more useful

### 5. Metadata Filtering on Queries

- **What**: Let users filter by document type (hr, engineering, security, etc.) — metadata already exists in Pinecone
- **Why clients care**: Searching "security policy" shouldn't return onboarding results. Precision without model changes
- **How**: Add optional `document_type: Optional[str]` to `AskRequest` in `api/models.py`. Pass Pinecone filter `{"document_type": document_type}` in `api/rag_service.py`. Add filter chips in `ChatInterface.tsx` reusing `TYPE_STYLES` from `SourcePanel.tsx`. Pass filter in `askQuestion()` call
- **Effort**: 1 day
- **Impact**: Medium answer quality, High UX, Medium trust
- **Dependencies**: None

### 6. Reranking with FlashRank

- **What**: After retrieving 20 chunks from Pinecone, rerank to best 5 using a cross-encoder
- **Why clients care**: Single highest-impact improvement for answer quality. 5-15% precision improvement in benchmarks. Better answers, better sources
- **How**: Add `flashrank` dep (free, local, no API key). Change `retrieval_k` from 6 to 20 in `api/config.py`. Add `rerank_top_k: int = 5`. Initialize `Ranker(model_name="ms-marco-MiniLM-L-12-v2")` in `CloudRAGService.__init__`. After relevance filtering in `api/rag_service.py`, rerank and take top-k. Update tests to mock Ranker
- **Effort**: 1–2 days
- **Impact**: High answer quality, Medium trust, Low UX
- **Dependencies**: None (synergizes with metadata filtering)

---

## Tier 2: Medium Effort (3–5 days each)

### 7. Streaming Responses (SSE)

- **What**: Stream LLM tokens to frontend via Server-Sent Events instead of waiting for full response
- **Why clients care**: Users perceive streaming as 3-5x faster. Every major AI product streams. Users expect it
- **How**: Add `ask_stream()` method in `api/rag_service.py` using `self.llm.stream(prompt)`. Add `POST /ask/stream` endpoint in `api/routes.py` returning `StreamingResponse(media_type="text/event-stream")`. Send `sources` event first, then `token` events, then `done` event. Keep existing `/ask` for backward compat. Add `askQuestionStream()` in `frontend/src/api/client.ts` using `fetch` + `response.body.getReader()`. Update `ChatInterface.tsx` to accumulate tokens progressively
- **Effort**: 3 days
- **Impact**: High UX, Medium trust, Low answer quality
- **Dependencies**: None

### 8. Input Sanitization & Prompt Injection Defense

- **What**: Input sanitization, injection pattern detection, output filtering for leaked system prompt content
- **Why clients care**: OWASP #1 risk for LLM apps. Client security teams ask about this during evaluation
- **How**: Create `api/security.py` with: `sanitize_input()` (strip control chars, normalize Unicode), `detect_injection()` (regex blocklist for "ignore previous instructions", role-switching), `filter_output()` (detect leaked system prompt fragments, PII patterns). Wire into `api/routes.py` before service call (400 on injection). Wire output filter in `api/rag_service.py` before returning. Add `api/tests/test_security.py`. Log blocked attempts as security events
- **Effort**: 3 days
- **Impact**: High trust, Low UX, Low answer quality
- **Dependencies**: Structured logging (1) for security event tracking

### 9. Evaluation Framework (RAGAS)

- **What**: Automated evaluation pipeline measuring retrieval quality and generation faithfulness with curated test set
- **Why clients care**: Clients ask "how good is this system?" and need a number, not a feeling. Prevents regressions when making changes
- **How**: Add `ragas` + `datasets` to dev deps. Create `eval/` directory with: `test_set.json` (20-30 Q&A pairs per document type), `run_evaluation.py` (runs questions through service, computes RAGAS metrics: faithfulness, answer_relevancy, context_precision, context_recall), `conftest.py` (service fixtures). Store results as JSON for trend tracking. Add CI step for PR evaluation
- **Effort**: 4–5 days
- **Impact**: High answer quality, High trust, Low UX
- **Dependencies**: Feedback (4) provides real-world signal alongside synthetic eval

### 10. Frontend Tests

- **What**: Vitest + React Testing Library test suite for all 6 components
- **Why clients care**: Frontend bugs erode trust. Tests prevent regressions and enable faster iteration
- **How**: Add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `msw` to frontend devDeps. Create `frontend/src/__tests__/` with test files for ChatInterface, MessageBubble, SourcePanel, DocumentSidebar, ExampleChips. Use MSW for API mocks. Add `"test": "vitest"` to package.json scripts
- **Effort**: 3–4 days
- **Impact**: Medium trust, Medium UX (prevents regressions), Low answer quality
- **Dependencies**: None

---

## Tier 3: Strategic Investments (1–2 weeks each)

### 11. Hybrid Search (Dense + BM25)

- **What**: Combine vector search with BM25 keyword matching for better recall on exact terms (policy names, acronyms like "SOC 2")
- **Why clients care**: Pure vector search misses exact matches. 1-9% recall improvement in benchmarks. Reduces false "I don't know" responses
- **How**: Recommended approach — application-level fusion (avoids re-ingestion). Add `rank_bm25` dep. Load chunked documents into a BM25 index at startup. At query time, get top-K from both Pinecone and BM25, fuse with Reciprocal Rank Fusion (RRF) in a new `_hybrid_search()` method in `api/rag_service.py`. Add `hybrid_search_enabled: bool = True` and `bm25_weight: float = 0.3` to `api/config.py`
- **Effort**: 3–4 days
- **Impact**: Medium answer quality, Low UX, Medium trust
- **Dependencies**: Evaluation framework (9) to measure improvement. Synergizes with reranking (6)

### 12. Multi-Turn Conversation

- **What**: Follow-up questions with conversation history. "What about part-time employees?" after asking about PTO
- **Why clients care**: Most requested feature in knowledge base products. Separates "search box" from "AI assistant"
- **How**: Add `session_id: Optional[str]` to `AskRequest` and `AskResponse` in `api/models.py`. Create `api/session.py` with in-memory `SessionStore` (dict with TTL). Add `_reformulate_query()` method in `api/rag_service.py` that uses LLM to produce standalone query from conversation context. Cap at 5 turns. Generate session_id (UUID) on frontend chat init in `ChatInterface.tsx`, include in every request
- **Effort**: 5–7 days
- **Impact**: High UX, High answer quality, Medium trust
- **Dependencies**: Streaming (7) should be done first for complete conversational UX

### 13. Semantic Chunking

- **What**: Replace fixed-size `RecursiveCharacterTextSplitter` with structure-aware markdown chunking
- **Why clients care**: Bad chunking = bad answers, silently. Better chunking improves every downstream metric
- **How**: In `api/document_loader.py`, replace with custom `MarkdownSemanticSplitter`: split on `##` boundaries first, then `###`, then `\n\n`. Prepend parent heading to sub-chunks. Add rich metadata (`heading_hierarchy`, `chunk_type`, `token_count`). Rerun ingestion via `scripts/ingest.py`. A/B test with evaluation framework
- **Effort**: 5–7 days (including re-ingestion and evaluation)
- **Impact**: High answer quality, Medium trust, Low UX
- **Dependencies**: Evaluation framework (9) critical to measure improvement. Requires Pinecone re-ingestion

### 14. Analytics Dashboard

- **What**: Admin dashboard showing query patterns, quality metrics, popular topics, failure rates, feedback trends
- **Why clients care**: "340 questions last week, 89% helpful, top topic: incident response" is a powerful retention tool
- **How**: Create `api/analytics.py` with `AnalyticsStore` aggregating structured logs. Add `GET /admin/analytics` endpoint with basic auth. Create separate `/admin` route in frontend with React Router + recharts for charts: queries over time, confidence distribution, top documents, recent low-confidence queries
- **Effort**: 7–10 days
- **Impact**: High trust, Medium UX (admins), Medium answer quality (identifies weak areas)
- **Dependencies**: Structured logging (1), feedback (4), evaluation framework (9)

---

## Recommended Implementation Order

```
Phase 1 — Foundation (Week 1):
  1. Structured Logging with Request IDs     [1 day]
  2. Query Result Caching                     [0.5 day]
  3. Rate Limiting                            [0.5 day]
  4. User Feedback Mechanism                  [1 day]

Phase 2 — Answer Quality (Week 2):
  5. Reranking with FlashRank                 [1-2 days]
  6. Metadata Filtering on Queries            [1 day]

Phase 3 — UX & Security (Weeks 3-4):
  7. Streaming Responses (SSE)                [3 days]
  8. Input Sanitization & Prompt Injection    [3 days]

Phase 4 — Measurement (Weeks 5-6):
  9. Evaluation Framework                     [4-5 days]
 10. Frontend Tests                           [3-4 days]

Phase 5 — Advanced Features (Weeks 7+):
 11. Hybrid Search                            [3-4 days]
 12. Multi-Turn Conversation                  [5-7 days]
 13. Semantic Chunking                        [5-7 days]
 14. Analytics Dashboard                      [7-10 days]
```

**Sequencing rationale**:
- Logging first → every subsequent item benefits from debuggability
- Caching + rate limiting → protect Gemini free tier immediately
- Feedback before eval → starts collecting signal while eval framework is built
- Reranking before streaming → stream better answers, not just faster ones
- Eval framework before hybrid search + semantic chunking → need measurement to prove value
- Multi-turn after streaming → combined = complete conversational experience
- Analytics last → requires accumulated data from all prior items

---

## Key Files Modified

| File | Items |
|------|-------|
| `api/rag_service.py` | 1, 2, 5, 6, 7, 9, 11, 12, 13 |
| `api/routes.py` | 1, 2, 3, 4, 7, 8 |
| `api/models.py` | 4, 5, 12 |
| `api/app.py` | 1, 3 |
| `api/config.py` | 3, 6, 11 |
| `api/prompts.py` | 8 (output filter reference) |
| `api/document_loader.py` | 13 |
| `frontend/src/components/ChatInterface.tsx` | 5, 7, 12 |
| `frontend/src/components/MessageBubble.tsx` | 4 |
| `frontend/src/api/client.ts` | 4, 5, 7 |
| `frontend/src/types/index.ts` | 4, 5, 12 |

**New files**: `api/middleware.py` (1), `api/security.py` (8), `api/session.py` (12), `api/analytics.py` (14), `frontend/src/components/FeedbackButtons.tsx` (4), `eval/` directory (9), `frontend/src/__tests__/` (10)

---

## Sources

- [Low-Hanging Fruit for RAG Search — Jason Liu](https://jxnl.co/writing/2024/05/11/low-hanging-fruit-for-rag-search/)
- [The Ultimate RAG Blueprint 2025/2026](https://langwatch.ai/blog/the-ultimate-rag-blueprint-everything-you-need-to-know-about-rag-in-2025-2026)
- [RAG at Scale: Production AI Systems 2026](https://redis.io/blog/rag-at-scale/)
- [RAG Evaluation: Complete Guide](https://www.getmaxim.ai/articles/complete-guide-to-rag-evaluation-metrics-methods-and-best-practices-for-2025/)
- [RAG Hallucinations Explained](https://www.mindee.com/blog/rag-hallucinations-explained)
- [User Feedback in RAG: Continuous Improvement Loop](https://apxml.com/courses/optimizing-rag-for-production/chapter-6-advanced-rag-evaluation-monitoring/user-feedback-rag-improvement)
- [How to Implement a Reranker in LangChain](https://docs.bswen.com/blog/2026-02-25-langchain-reranker-implementation/)
- [Mastering RAG: How to Select a Reranking Model](https://galileo.ai/blog/mastering-rag-how-to-select-a-reranking-model)
- [SSE with FastAPI and React](https://www.softgrade.org/sse-with-fastapi-react-langgraph/)
- [RAG for Business: Full Guide](https://www.meilisearch.com/blog/rag-for-business)
- [Enterprise RAG Evolution 2026-2030](https://nstarxinc.com/blog/the-next-frontier-of-rag-how-enterprise-knowledge-systems-will-evolve-2026-2030/)
- [Detect Hallucinations in RAG with Datadog](https://www.datadoghq.com/blog/llm-observability-hallucination-detection/)
