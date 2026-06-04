# CI/CD workflows (reference copies)

These are the real GitHub Actions workflows for this project. They live here (instead
of `.github/workflows/`) only because the token used for the initial push lacked the
`workflow` OAuth scope (see BLOCKERS.md, step 10).

**To enable Actions-based CI + Pages deploy:** with a `workflow`-scoped token,

```bash
mkdir -p .github/workflows
git mv deploy/ci.yml      .github/workflows/ci.yml
git mv deploy/deploy.yml  .github/workflows/deploy.yml
git commit -m "Enable GitHub Actions workflows"
git push
```

- `ci.yml` — validate the data on every push (pipeline/validate.py).
- `deploy.yml` — build viz/ and deploy to GitHub Pages (configure-pages,
  upload-pages-artifact, deploy-pages; permissions contents:read, pages:write,
  id-token:write). Vite base is derived from the repo name.

Until then, the live site is published from the `gh-pages` branch (static bundle).
