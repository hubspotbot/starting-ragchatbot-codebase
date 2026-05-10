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
