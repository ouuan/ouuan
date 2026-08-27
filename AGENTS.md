# AGENTS.md

## Project

GitHub profile README for [@dllen](https://github.com/dllen). Auto-updated via GitHub Actions workflows (WakaTime stats, blog posts, starred repos, followers).

## Structure

- `README.md` — profile page, updated by CI
- `src/` — helper scripts (Python, JS) for data fetching
- `.github/workflows/` — GitHub Actions (wakatime, blog-posts, star-fork, followers, etc.)
- `AWESOME-STARS.md` — curated starred repos list
- `CVE.md` — CVE notes

## Conventions

- Python scripts target 3.x; keep deps minimal (stdlib + requests)
- JS scripts use Node.js; no build step
- Workflows use pinned action SHAs where possible
- Secrets are managed via repo/org secrets — never hardcode tokens
- README sections between `<!--START_SECTION:-->` / `<!--END_SECTION:-->` markers are auto-generated; do not hand-edit them
- Commit messages: imperative, lowercase (`update wakatime stats`)

## Testing

No test suite. Verify workflows locally with `act` if needed, or trigger `workflow_dispatch` on a branch.

## Do NOT

- Commit secrets or API keys
- Modify auto-generated README sections by hand
- Add heavy dependencies to `src/` scripts
