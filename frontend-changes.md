# Testing Framework Changes

## Files Added / Modified

### `backend/tests/conftest.py` (new)
Shared pytest fixtures used across all test files:
- `mock_rag` — MagicMock for `RAGSystem` with pre-configured return values for `query`, `session_manager`, and `get_course_analytics`
- `test_app` — minimal FastAPI app that mirrors the `/api/query` and `/api/courses` endpoints from `app.py` but **omits the static-file mount**, avoiding the missing `frontend/` directory issue in CI/test environments
- `client` — `starlette.testclient.TestClient` wrapping `test_app`
- `sample_query_payload` / `sample_query_with_session` — ready-to-use request payloads

### `backend/tests/test_api_endpoints.py` (new)
21 tests across two classes:

**`TestQueryEndpoint`** — covers `POST /api/query`:
- 200 on valid request; 422 on missing `query` field; 500 when RAGSystem raises
- Session creation when no `session_id` is provided
- Session passthrough when `session_id` is provided
- Answer and sources propagated correctly from RAGSystem
- Error detail surfaced in 500 response body

**`TestCoursesEndpoint`** — covers `GET /api/courses`:
- 200 with correct `total_courses` / `course_titles` fields
- Empty catalog edge case
- 500 with error detail when analytics raises
- `get_course_analytics` called exactly once per request

### `pyproject.toml` (modified)
Added pytest configuration and `httpx` dev dependency (required by Starlette's `TestClient`):

```toml
[tool.pytest.ini_options]
testpaths = ["backend/tests"]
pythonpath = ["backend"]
addopts = "-v"

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "httpx>=0.27",
]
```

## Test Results
All 50 tests pass (`uv run pytest`).
