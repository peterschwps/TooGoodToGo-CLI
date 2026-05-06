# Publishing Plan — Open TODOs

The full historical bootstrap plan that took TGTG-CLI from a private
draft to its current state has been fulfilled. The complete reference
of *what was set up and how it works* now lives in
[`INFRASTRUCTURE.md`](./INFRASTRUCTURE.md).

This file tracks only the **outstanding TODOs** that still need to be
done before — and right after — flipping the repository to public and
publishing `v0.1.0` to PyPI.

---

## Before going public

### 1. Optional: smoke-test the TestPyPI dry-run

The `v0.0.0a1-testpypi` tag has already been pushed and the workflow
published `TGTG-CLI 0.1.0` to TestPyPI (PyPI itself stayed empty). To
verify a clean install in a fresh environment:

```bash
uvx --index https://test.pypi.org/simple/ \
    --index-strategy unsafe-best-match \
    --from TGTG-CLI tgtg-cli
```

`--index-strategy unsafe-best-match` is required because TestPyPI does
not host runtime dependencies; pulling them from real PyPI is the only
working option.

### 2. Configure `[tool.ty]` and re-enable the type-check gate

`type-check` runs with `continue-on-error: true` so ty does not block
PRs while its default strictness is unconfigured.

1. Add a `[tool.ty]` block in `pyproject.toml`. Scope to `src` and
   `tests`. Suppress noisy categories as needed until the existing
   findings reduce to actionable signal.
2. Fix or `# type: ignore[...]` the remaining real findings.
3. Remove `continue-on-error: true` from the `type-check` job in
   `.github/workflows/ci.yml`.
4. Add `Type check (ty)` to the required status checks in branch
   protection (Settings → Branches → `main`).

### 3. Prepare release content

User-facing work the maintainer wants to land before publishing:

* Implement the minimal feature set planned for v0.1.0.
* Write the public-facing documentation (extend `README.md`, add
  install instructions, configuration guide, examples).
* Migrate the contents of `IDEAS.md`, `NOTES.md`, `TODO.md` into
  GitHub Issues / Discussions, then delete the files from the repo
  root.

---

## Public switch

When all of the above is done:

1. **Settings → General → Danger Zone → Change repository visibility →
   Public.** GitHub will prompt twice; confirm.
2. Refresh the local `gh` cache: `gh repo view peterschwps/TGTG-CLI
   --json visibility`.

---

## Right after going public

### 4. Enable the security features that need a public repo

GitHub Free plan unlocks these only on public repositories:

```bash
REPO=peterschwps/TGTG-CLI

# Secret scanning + push protection
gh api -X PATCH "/repos/$REPO" \
  -F 'security_and_analysis[secret_scanning][status]=enabled' \
  -F 'security_and_analysis[secret_scanning_push_protection][status]=enabled'

# CodeQL "Default setup"
gh api -X PATCH "/repos/$REPO/code-scanning/default-setup" \
  -f state=configured \
  -f query_suite=default
```

### 5. Add reviewer protection to the `pypi` deployment environment

Free-plan **private** repos cannot configure required reviewers on a
deployment environment; **public** repos can. Once public, do this so a
publish to real PyPI cannot slip out unattended:

```bash
USER_ID=$(gh api /users/peterschwps --jq '.id')
gh api -X PUT /repos/peterschwps/TGTG-CLI/environments/pypi --input - <<EOF
{
  "reviewers": [
    {"type": "User", "id": $USER_ID}
  ]
}
EOF
```

### 6. (Optional) protect the `v*` tag namespace

Settings → Tags → New rule → pattern `v*` → restrict who can push and
prevent deletion / force-update. Keeps released tags immutable.

---

## Cutting `v0.1.0`

The first real PyPI release. Two paths.

### Path A — let release-please drive (recommended once features land)

1. Land feature / fix PRs on `main` with Conventional Commit messages.
2. release-please opens a `chore: release X.Y.Z` PR with the version
   bump and CHANGELOG entry.
3. Review and squash-merge.
4. release-please tags `vX.Y.Z` and creates a GitHub Release.
5. The tag triggers `release.yml` → build → TestPyPI (skipped on
   collision via `skip-existing`) → PyPI → GitHub Release assets.
6. Verify on <https://pypi.org/project/TGTG-CLI/>.

### Path B — manual first tag

If `0.1.0` should be the first published version regardless of what
release-please calculates:

```bash
cd /Users/admin/Development/TGTG-CLI
git checkout main
git pull
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

The Trusted Publisher and the `pypi` environment are already
configured, so the workflow will succeed without any further setup.

---

## Reference

For the full description of every config block, every CI job, every
release knob, and every repo setting, see
[`INFRASTRUCTURE.md`](./INFRASTRUCTURE.md).
