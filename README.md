# Ask Your Docs — RAG Knowledge Base

A cloud-deployed RAG (Retrieval-Augmented Generation) system that answers questions across multiple internal documents with source attribution. Built as a portfolio demo using a fictional "Acme Corp" knowledge base.

## What Makes This Different

- **Cross-document reasoning**: Synthesizes answers from 5 different internal documents (HR, engineering, onboarding, product, security)
- **Source attribution**: Every answer cites specific documents and sections, so you can verify the information
- **Confidence scoring**: Indicates when the system is less certain about an answer
- **Production architecture**: Cloud-deployed with a proper API, vector database, and React frontend

## Architecture

```
User → React Frontend → FastAPI Backend → Google Gemini 2.5 Flash
                                        → Pinecone (vector search)
                                        → HuggingFace Embeddings (MiniLM-L6-v2)
```

| Component | Technology | Hosting |
|-----------|-----------|---------|
| Frontend | React + TypeScript + Tailwind CSS | Vercel |
| Backend API | FastAPI + LangChain | Render |
| LLM | Google Gemini 2.5 Flash | Google AI API |
| Vector Store | Pinecone (384 dims, cosine) | Pinecone Starter |
| Embeddings | all-MiniLM-L6-v2 | Loaded at runtime |

## Knowledge Base

5 Acme Corp documents with cross-references between them:

| Document | Type | Content |
|----------|------|---------|
| Employee Handbook | HR | PTO, remote work, expenses, benefits, 401k |
| Engineering Runbook | Engineering | Incident response (P1-P4), on-call, deployments, SLOs |
| Onboarding Guide | Onboarding | Day 1 checklist, team structure, 30/60/90 expectations |
| Product Docs | Product | Acme Analytics API, data model, pricing, integrations |
| Security Policy | Security | Encryption (AES-256/TLS 1.3), RBAC, SOC 2, password policy |

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) package manager
- Google AI API key
- Pinecone API key

### Backend

```bash
# Install dependencies
uv sync

# Copy and fill in environment variables
cp .env.example .env

# Ingest documents into Pinecone
uv run python scripts/ingest.py

# Start the API server
uv run uvicorn api.app:app --reload
```

API available at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI available at `http://localhost:5173`.

### Tests

```bash
# Backend tests
uv run python -m pytest api/tests/ -v

# Original local RAG tests
uv run python -m pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ask` | Ask a question, returns answer + sources |
| POST | `/ask/stream` | Stream an answer via SSE |
| GET | `/health` | Service health check |
| GET | `/documents` | List indexed documents |
| GET | `/documents/{slug}` | Get full document content |

## Deploy Your Own

### Backend (Render)

1. Create a new Web Service on [Render](https://render.com)
2. Connect your repo, select Docker environment
3. Set environment variables: `GOOGLE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`

### Frontend (Vercel)

1. Import repo on [Vercel](https://vercel.com)
2. Set root directory to `frontend/`
3. Set build command: `npm run build`, output: `dist`
4. Add env var: `VITE_API_URL=https://your-backend.onrender.com`

### Cost

| Service | Plan | Cost |
|---------|------|------|
| Render | Free tier | $0 |
| Vercel | Hobby | $0 |
| Pinecone | Starter | $0 |
| Gemini | Free tier (15 RPM) | $0 |

## Original Local RAG

The local Ollama-based RAG system is still available:

```bash
# Start Ollama
ollama serve && ollama pull llama3.1:latest

# Ask a question against local PDFs
uv run python ask.py "How does binary search work?"
```

## Built By

[Alex Bancu](https://github.com/alexbancu)
