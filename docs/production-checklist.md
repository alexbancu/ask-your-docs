# RAG Production Checklist (High-Level)

## The 10 Moving Parts

### 1. DATA SOURCE
- **Now:** Static PDF file
- **Production:** Real-time API connection with sync pipeline

### 2. DATA PIPELINE
- **Now:** One-time load
- **Production:** Scheduled refresh, incremental updates, validation

### 3. VECTOR DATABASE
- **Now:** FAISS (local file)
- **Production:** Managed DB (Pinecone/Qdrant) with scaling & backups

### 4. RETRIEVAL
- **Now:** Basic vector search
- **Production:** Hybrid search (vector + keyword) + re-ranking

### 5. LLM
- **Now:** Local Ollama
- **Production:** Cloud API or scaled local with fallbacks

### 6. API LAYER
- **Now:** CLI script
- **Production:** REST API with auth, rate limits, streaming

### 7. INFRASTRUCTURE
- **Now:** Local machine
- **Production:** Containers, auto-scaling, load balancing

### 8. SECURITY
- **Now:** None
- **Production:** Auth, encryption, input sanitization, audit logs

### 9. OBSERVABILITY
- **Now:** Print statements
- **Production:** Logging, metrics, tracing, alerting

### 10. EVALUATION
- **Now:** Manual testing (10 questions)
- **Production:** Automated test suite in CI/CD

---

## Priority Order

**Phase 1 - Make it work:**
1. API client + data pipeline
2. Production vector DB
3. REST API with auth

**Phase 2 - Make it reliable:**
4. Observability (logs, metrics)
5. Security hardening
6. Automated evaluation

**Phase 3 - Make it fast:**
7. Caching layer
8. Hybrid search + re-ranking
9. Auto-scaling
