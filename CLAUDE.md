# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Start the server (from project root)
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app is available at http://localhost:8000 and Swagger UI at http://localhost:8000/docs.

**Setup:** Copy `.env.example` to `.env` and add your `ANTHROPIC_API_KEY`.

There is no test suite or lint configuration in this project.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about course content using Claude's tool-use API. It uses Python 3.13 with `uv` as the package manager.

### Component responsibilities

| File | Role |
|---|---|
| `backend/app.py` | FastAPI app; serves static frontend and exposes `POST /api/query` and `GET /api/courses` |
| `backend/rag_system.py` | Orchestrator that wires together all sub-components; handles document loading and query routing |
| `backend/ai_generator.py` | Calls Claude Sonnet 4 (`claude-sonnet-4-20250514`) with tool use; temperature 0 |
| `backend/vector_store.py` | ChromaDB dual-collection store (`course_catalog` + `course_content`); semantic search via local SentenceTransformer (`all-MiniLM-L6-v2`) |
| `backend/document_processor.py` | Parses `.txt`/`.pdf`/`.docx` files, extracts course metadata from first 3 lines, splits content into overlapping chunks (800 chars, 100 overlap) |
| `backend/search_tools.py` | Defines `search_course_content` tool that Claude calls; formats vector results with course/lesson context |
| `backend/session_manager.py` | In-memory conversation history; auto-truncates at `max_history * 2` messages |
| `backend/models.py` | Pydantic request/response models |
| `frontend/` | Static single-page app served by FastAPI; uses Fetch API + Marked.js for markdown |

### Query flow

```
User message → POST /api/query
  → RAGSystem.query()
    → AIGenerator.generate_response()
      → Claude decides to call search_course_content tool
        → CourseSearchTool.execute() → VectorStore.search() (ChromaDB)
      → Tool results returned to Claude
    → Claude generates final answer
  → Answer + sources returned to frontend
```

### Document format

Course files in `/docs` must follow this structure:
- Line 1: Course title
- Line 2: Instructor link (URL)
- Line 3: Instructor name
- Body: `Lesson N: Title` headers followed by lesson content

ChromaDB persists to `./chroma_db`. Documents are deduplicated by title on load.

### Key design decisions

- Claude uses tool calling to decide when to search — the AI determines if a question is course-related before invoking the vector search
- Embeddings are generated locally (no external embedding API)
- Sessions are in-memory only — they do not survive server restarts
- CORS is open (all origins) for development
