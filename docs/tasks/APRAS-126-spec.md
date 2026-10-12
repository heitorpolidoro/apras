# APRAS-126 — Add frontend/.vitest/ to frontend/.gitignore

One-line change: append a `.vitest/` entry to `frontend/.gitignore`, next to the existing `dist` and `coverage` entries, so vitest's cache/output directory never shows in `git status`.

Files touched: `frontend/.gitignore` (add `.vitest/`). No code, config, or tracked-file changes; if `frontend/.vitest/` is already tracked, it is out of scope.

Test criteria: `grep -x '.vitest/' frontend/.gitignore` matches; after running vitest in `frontend/`, `git status --porcelain -- frontend/.vitest` prints nothing (`git check-ignore frontend/.vitest/x` exits 0).

## Expected Results
- [ ] `frontend/.gitignore` contains a `.vitest/` line alongside `dist` and `coverage`.
- [ ] After running vitest, `git status --porcelain` lists no path under `frontend/.vitest/`.
