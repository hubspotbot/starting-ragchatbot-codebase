# Frontend Changes — Dark/Light Theme Toggle

## Files Modified

### `frontend/index.html`
- Added `data-theme="dark"` attribute to `<html>` element so the default dark theme is set before any JS runs (prevents flash of unstyled content).
- Added a `<button id="themeToggle" class="theme-toggle">` fixed-position button immediately inside `<body>`, containing two inline SVG icons:
  - `.icon-sun` — shown in dark mode (click to switch to light)
  - `.icon-moon` — shown in light mode (click to switch to dark)
  - Both icons have `aria-hidden="true"`; the button itself carries the accessible label.

### `frontend/style.css`
- **`:root, [data-theme="dark"]`** — converted the existing `:root` block to explicitly target the dark theme. Added six new variables used by other rules:
  - `--code-bg`, `--chip-bg`, `--chip-border`, `--chip-color`, `--chip-hover-bg`, `--chip-hover-border`, `--chip-hover-color`
- **`[data-theme="light"]`** — new block with light-mode overrides:
  - `--background: #f8fafc`, `--surface: #ffffff`, `--surface-hover: #f1f5f9`
  - `--text-primary: #0f172a`, `--text-secondary: #64748b`, `--border-color: #e2e8f0`
  - Lighter shadow, softer code backgrounds, blue-tinted chip colors
- **`.source-chip`** — replaced hardcoded `rgba(255,255,255,…)` values with `var(--chip-*)` variables so chips adapt to both themes.
- **`.message-content code` / `pre`** — replaced hardcoded `rgba(0,0,0,0.2)` with `var(--code-bg)`.
- **`.theme-toggle`** button styles:
  - `position: fixed; top: 1rem; right: 1rem; z-index: 1000`
  - 40×40 px circular button with border, surface background, and shadow
  - Hover: primary-color border + scale(1.1); focus: focus-ring outline; active: scale(0.95)
- **Icon visibility rules** — `[data-theme="dark"] .icon-moon` and `[data-theme="light"] .icon-sun` are hidden so the correct icon always shows.
- **Smooth transition rule** — a selector list covering `body`, sidebar, chat containers, input, messages, buttons, and sidebar items applies `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` for seamless theme switching.

### `frontend/script.js`
- Added `themeToggle` to the DOM element variables.
- **`initTheme()`** — called on `DOMContentLoaded`; reads `localStorage.getItem('theme')` (defaults to `'dark'`) and calls `applyTheme()`.
- **`applyTheme(theme)`** — sets `data-theme` on `document.documentElement`, writes the preference to `localStorage`, and updates the button's `aria-label` and `title` to describe the opposite action.
- **`toggleTheme()`** — reads the current `data-theme` value and calls `applyTheme()` with the opposite value.
- Wired `themeToggle.addEventListener('click', toggleTheme)` in `setupEventListeners()`.

## Behaviour
- Default theme is **dark** (set in HTML, confirmed by JS on load).
- Preference persists across page refreshes via `localStorage`.
- Button is keyboard-navigable (native `<button>`, focus-ring visible).
- All theme-sensitive properties animate over 300 ms for a smooth crossfade.

---

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

---

# Frontend Code Quality Changes

## What was added

### Tooling setup (`frontend/`)

| File | Purpose |
|---|---|
| `package.json` | Dev dependencies (Prettier 3, ESLint 8) and npm scripts |
| `.prettierrc` | Prettier config — 4-space indent, single quotes, trailing commas, LF line endings |
| `.eslintrc.json` | ESLint config — browser environment, recommended rules, `no-var`, `eqeqeq`, `no-console` warning |
| `.prettierignore` | Excludes `node_modules/` and `package-lock.json` from formatting |

### Dev scripts (`package.json`)

| Script | Command | Description |
|---|---|---|
| `npm run format` | `prettier --write` | Auto-format JS, HTML, CSS |
| `npm run format:check` | `prettier --check` | Verify formatting (CI-safe, no writes) |
| `npm run lint` | `eslint **/*.js` | Lint JavaScript |
| `npm run check` | format:check + lint | Full quality gate |

### Root convenience script

`format.sh` — wraps `npm run check` from any directory.  
`./format.sh --fix` — auto-formats files then runs ESLint.

## Files reformatted by Prettier

- `frontend/index.html` — attribute alignment, consistent indentation
- `frontend/script.js` — trailing commas added, multiline expressions broken at 80-char limit, quote style normalised to single quotes
- `frontend/style.css` — whitespace and rule consistency

## Code fixes applied during setup

`frontend/script.js`:
- Removed two debug `console.log` statements from `loadCourseStats()` that would trigger the `no-console` ESLint rule (the UI already displays error states to the user)
- Removed a stale "Removed removeMessage function" comment that referenced deleted code

## How to use

```bash
# From the repo root — check everything
./format.sh

# Auto-fix formatting, then lint
./format.sh --fix

# From frontend/ directory
npm run check        # full gate
npm run format       # fix formatting only
npm run lint         # lint only
```
