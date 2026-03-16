# Multi-Demo System

Supports multiple isolated document sets (one per client/demo) within a single deployment. Each demo gets its own Pinecone namespace, resource folder, and shareable URL.

## Architecture

- **URL routing:** `/demo/{slug}` — each demo has a unique URL
- **Pinecone namespaces:** one index, many namespaces (free on Starter plan)
- **Demo config:** each demo folder has a `demo.json` with name + document metadata
- **Backwards compat:** old endpoints (`/ask`, `/documents`) still work as aliases for `acme-corp`

## Folder Structure

```
resources/
├── acme-corp/
│   ├── demo.json
│   ├── employee-handbook.md
│   ├── engineering-runbook.md
│   └── ...
└── hooli/
    ├── demo.json
    ├── sales-playbook.md
    └── ...
```

## demo.json Schema

```json
{
  "name": "Acme Corp",
  "documents": {
    "employee-handbook": { "type": "hr", "owner": "HR Team" },
    "engineering-runbook": { "type": "engineering", "owner": "Platform Engineering" }
  }
}
```

- `name` — display name shown in the UI
- `documents` — keys are markdown filename stems, `type` maps to sidebar styling, `owner` shown in document viewer

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /demos` | List all available demos |
| `POST /demos/{demo}/ask` | Ask a question (scoped to demo) |
| `POST /demos/{demo}/ask/stream` | Stream an answer (scoped to demo) |
| `GET /demos/{demo}/documents` | List documents for a demo |
| `GET /demos/{demo}/documents/{slug}` | Get a single document |
| `GET /health` | Health check (unchanged) |

Legacy endpoints (`/ask`, `/documents`, `/documents/{slug}`, `/ask/stream`) still work and route to `acme-corp`.

## Frontend Routes

| URL | Page |
|-----|------|
| `/` | Redirects to `/demo/acme-corp` |
| `/demo/{slug}` | Chat interface for that demo |
| `/demo/{slug}/documents/{doc}` | Document viewer |

A demo switcher dropdown appears in the sidebar when 2+ demos are available.

## Adding a New Demo

```bash
# 1. Create folder with markdown docs
mkdir resources/hooli
# ... add .md files ...

# 2. Create demo.json
cat > resources/hooli/demo.json << 'EOF'
{
  "name": "Hooli",
  "documents": {
    "sales-playbook": { "type": "sales", "owner": "Sales Team" }
  }
}
EOF

# 3. Ingest into Pinecone namespace
uv run python scripts/ingest.py --demo hooli

# 4. Deploy (or auto-deploy via git push)
# 5. Share URL: https://app.com/demo/hooli
```

## Ingestion

The ingest script is now namespace-aware. It clears only the target demo's namespace (not the whole index) before upserting.

```bash
# Ingest a single demo
uv run python scripts/ingest.py --demo acme-corp

# Ingest all demos
uv run python scripts/ingest.py --all
```

**Important:** After deploying this change, you must re-ingest existing demos so their vectors move into the correct namespace:

```bash
uv run python scripts/ingest.py --demo acme-corp
```

## Files Changed

**Created:**
- `resources/acme-corp/demo.json`
- `frontend/src/contexts/DemoContext.tsx`

**Backend:**
- `api/document_loader.py` — `DemoConfig`, `load_demo_config()`, `list_demos()`
- `api/models.py` — `DemoInfo`, `DemosResponse`
- `api/rag_service.py` — `demo_slug` param on all methods, Pinecone namespaces
- `api/routes.py` — demo-scoped endpoints + `GET /demos`
- `scripts/ingest.py` — `--demo` / `--all` args, namespace-aware

**Frontend:**
- `frontend/src/types/index.ts` — `DemoInfo` type
- `frontend/src/api/client.ts` — `demoSlug` param on all API calls, `getDemos()`
- `frontend/src/App.tsx` — `/demo/:demoSlug` routing with `DemoProvider`
- `frontend/src/components/DocumentSidebar.tsx` — demo switcher dropdown
- `frontend/src/components/DocumentViewer.tsx` — demo-aware links and API calls
- `frontend/src/components/SourcePanel.tsx` — demo-aware source links
- `frontend/src/components/ChatInterface.tsx` — dynamic demo name in header
