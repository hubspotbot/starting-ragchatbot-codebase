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
