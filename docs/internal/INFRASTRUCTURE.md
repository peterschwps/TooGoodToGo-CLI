# Infrastructure Reference

Comprehensive overview of every piece of infrastructure, configuration, and
automation in this repository. Maintainer-facing reference; not shipped in
the wheel.

---

## 1. Tool Stack

### `uv` — package and project manager

Fast Rust-based replacement for `pip` + `pip-tools` + `virtualenv`. Reads
`pyproject.toml` and writes a deterministic `uv.lock`. All developer
commands run through `uv run …` so contributors do not need a manually
activated venv. Project sync: `uv sync`. Editable install is automatic.

### `hatchling` — build backend

Configured in `[build-system]` of `pyproject.toml`. Produces wheels and
sdists from the `src/`-layout. Handles `py.typed` and license files
according to the modern PEP 639 / PEP 660 standards without extra
configuration.

### `ruff` — linter and formatter

Single tool replacing `flake8`, `isort`, `pyupgrade`, `bugbear`, `simplify`,
and `flake8-logging-format`. Configured in `[tool.ruff]` of
`pyproject.toml` with `line-length = 79` and `indent-width = 4`. The
formatter (`ruff format`) is intentionally not invoked by any hook or CI
job; it stays available for ad-hoc use only.

### `ty` — type checker

Astral's new Rust-based type checker, in preview. Configured nowhere yet
(default settings, follow-up tracked in `PUBLISHING_PLAN.md`). Run via
`uv run ty check` locally or in CI.

### `pytest` — test runner

Configured in `[tool.pytest.ini_options]` with strict markers and config,
test discovery scoped to `tests/`. Coverage measurements are configured in
`[tool.coverage.run]` (branch-coverage on, scoped to `src/tgtg_cli`) but
coverage is not enforced in any job yet.

### `pre-commit` — Git hook framework

Reads `.pre-commit-config.yaml`, runs hooks at the configured Git stage
(`pre-commit` or `commit-msg`). Each contributor must run
`uv run pre-commit install` and
`uv run pre-commit install --hook-type commit-msg` once after cloning.

---

## 2. Project Structure

```
.
├── .github/                      ← GitHub-specific config + community files
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml
│   │   ├── config.yml
│   │   └── enhancement.yml
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── release.yml
│   │   └── release-please.yml
│   ├── CONTRIBUTING.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── SECURITY.md
├── .vscode/                      ← shared editor config
│   ├── extensions.json           ← recommended extensions
│   ├── launch.json
│   └── settings.json             ← only the 79-char ruler
├── docs/
│   └── internal/                 ← maintainer notes, not shipped
│       ├── INFRASTRUCTURE.md     ← this file
│       └── PUBLISHING_PLAN.md
├── src/
│   └── tgtg_cli/                 ← actual package
│       └── py.typed              ← PEP 561 type-checking opt-in marker
├── tests/                        ← pytest test suite
├── .commitlintrc.json            ← commitlint config (extends conventional)
├── .editorconfig                 ← editor-agnostic formatting
├── .gitattributes
├── .gitignore
├── .pre-commit-config.yaml       ← pre-commit hooks definition
├── .release-please-config.json   ← release-please bump rules
├── .release-please-manifest.json ← release-please current-version state
├── CHANGELOG.md                  ← maintained by release-please
├── LICENSE                       ← MIT
├── README.md
├── pyproject.toml
└── uv.lock
```

`IDEAS.md`, `NOTES.md`, `TODO.md` at the root are temporary working notes;
they will be migrated to GitHub Issues / Discussions and removed.

---

## 3. Code Conventions

### Conventional Commits

All commit messages must match the [Conventional
Commits](https://www.conventionalcommits.org/) format:
`<type>(<optional-scope>): <subject>`. Allowed types: `feat`, `fix`,
`chore`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
`revert`. Breaking changes are flagged with a trailing `!` on the type
(e.g. `feat!:`) or a `BREAKING CHANGE:` footer.

The `commit-msg` pre-commit hook enforces the format locally; the
`Commit messages` job in CI re-checks every commit on every PR.

### Branch naming

Format: `<type>/<short-kebab-description>` where `<type>` is the same set
as commit types. Enforced by the `Branch name` CI job (regex
`^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`).

### Code style

* Line length: **79** (PEP 8 strict)
* Quotes: **double** (`"…"`)
* Indentation: 4 spaces, LF line endings, UTF-8
* Type hints: comprehensive, modern Python 3.12+ syntax
  (`int | None`, not `Optional[int]`)
* Docstrings: Google-style with a blank-line-padded triple-quoted block
  even for one-line bodies (matches existing codebase style)

`ruff` enforces line length and a curated rule set; everything else is
convention. `.editorconfig` ensures non-VSCode editors honour indent /
EOL / final-newline / trailing-whitespace rules.

---

## 4. `pyproject.toml` Sections

### `[project]`

PEP 621 metadata. The fields PyPI consumes:

* `name`, `version`, `description`, `readme` — basic identity.
* `requires-python = ">=3.12"` — runtime floor; pip rejects older Pythons.
* `license = "MIT"` + `license-files = ["LICENSE"]` — PEP 639 SPDX
  expression, replaces the deprecated `License ::` classifier.
* `authors`, `keywords`, `classifiers` — PyPI search and discovery.
* `dependencies` — runtime deps with lower-bound pins (`>=X`).

### `[project.urls]`

Sidebar links rendered on the PyPI page. Pre-populated to point at the
final `peterschwps/TGTG-CLI` repository.

### `[project.scripts]`

`tgtg-cli = "tgtg_cli.cli.__main__:main"` — registers the console
script. After install, users get a `tgtg-cli` binary on `$PATH` that
calls `main()`.

### `[build-system]`

`hatchling` build backend. No further hatch configuration is needed for
src-layout + simple metadata.

### `[tool.ruff]` and `[tool.ruff.lint]`

* `line-length = 79`, `indent-width = 4`
* Lint rule set: `E` (pycodestyle), `F` (Pyflakes), `UP` (pyupgrade),
  `B` (bugbear), `SIM` (simplify), `G` (logging-format), `I` (isort)

The formatter is configured nowhere — when invoked, it falls back to
defaults (also double quotes; identical effect).

### `[tool.pytest.ini_options]`

* `addopts = "-ra --strict-markers --strict-config"` — show summary of
  all non-passing outcomes; reject unknown markers and config.
* `testpaths = ["tests"]` — restrict discovery to `tests/`, faster
  collection and clearer test boundary.

### `[tool.coverage.run]`

* `branch = true` — measure branch coverage as well as line coverage.
* `source = ["src/tgtg_cli"]` — restrict coverage to project code, not
  third-party deps.

### `[dependency-groups]` (PEP 735)

* `dev` — pytest stack, ty, pre-commit, ruff. Installed by default with
  `uv sync`. Skip with `uv sync --no-dev`.

PEP 735 dependency groups are a UV-native feature; they do not appear in
the wheel metadata, so end users never see them.

---

## 5. Pre-Commit Hooks

`.pre-commit-config.yaml` enables three hook bundles.

### `pre-commit/pre-commit-hooks` (v5.0.0)

Generic Git hygiene:

* `trailing-whitespace` — strip trailing whitespace from text files.
* `end-of-file-fixer` — ensure each file ends with exactly one newline.
* `check-yaml`, `check-toml` — parse YAML / TOML to catch syntax errors.
* `check-added-large-files` — block files larger than 500 KB by default.
* `check-merge-conflict` — fail if a file still contains `<<<<<<<`
  markers.
* `mixed-line-ending --fix=lf` — normalize line endings to LF, including
  on Windows checkouts.

### `astral-sh/ruff-pre-commit` (v0.15.12)

* `ruff` with `args: [--fix]` — lint + apply auto-fixable rules. Pinned
  to the same minor as the dev dependency to avoid drift between local
  and CI runs.

The formatter hook (`ruff-format`) is intentionally absent.

### `compilerla/conventional-pre-commit` (v3.6.0)

* `conventional-pre-commit` at `stages: [commit-msg]` — validates the
  proposed commit message against the Conventional Commits regex with
  the default type set. Blocks the commit if it does not match.

This is why contributors run `pre-commit install --hook-type commit-msg`
in addition to the regular install.

---

## 6. CI Pipeline (`.github/workflows/ci.yml`)

Triggers: `push` to `main`, all `pull_request`s. Concurrency group is
`ci-<ref>` with `cancel-in-progress: true` so superseded runs on the same
branch are aborted.

### `Lint (ruff)`

`uv sync --no-dev` plus `uv run --with ruff ruff check .`. Minimal
install, fastest job, blocks merge.

### `Type check (ty)`

`uv sync` (full dev deps) plus `uv run ty check`. Runs with
`continue-on-error: true` — the job may report failure but does not
block the PR. This is intentional while `[tool.ty]` is unconfigured;
the follow-up to remove the override is tracked in `PUBLISHING_PLAN.md`.

### `Test (Python <ver> on <os>)`

3 × 3 matrix: Ubuntu / macOS / Windows times Python 3.12 / 3.13 / 3.14.
Each cell does `uv python install <ver>`, `uv sync --python <ver>`, then
`uv run pytest`. `fail-fast: false` so one failure does not cancel the
other eight cells.

### `Commit messages`

PR-only. Calls `wagoid/commitlint-github-action@v6` with
`configFile: .commitlintrc.json` (extends `@commitlint/config-conventional`).
Runs once per PR and validates every commit between base and head.
Requires job-level `pull-requests: read` permission.

### `Branch name`

PR-only. Bash regex on `${{ github.head_ref }}`. Fails the job with a
`::error::` annotation if the branch does not match the convention.

---

## 7. Release Pipeline (`.github/workflows/release.yml`)

Triggers on any pushed tag matching `v*`. Four sequential jobs.

### `Build distributions`

`uv build` produces a wheel (`.whl`) and an sdist (`.tar.gz`) from the
current `pyproject.toml`'s version. Uploaded as a workflow artifact
named `dist`.

### `Publish to TestPyPI`

Downloads the `dist` artifact and publishes it to TestPyPI via
`pypa/gh-action-pypi-publish@release/v1` against the
`https://test.pypi.org/legacy/` endpoint. Uses the `testpypi`
environment (Trusted Publishing OIDC). `skip-existing: true` makes the
job idempotent across re-runs and against versions already present.

### `Publish to PyPI`

Same action without the `repository-url` override (defaults to real
PyPI). Uses the `pypi` environment. Skipped if the tag name ends in
`-testpypi` — that suffix marks dry-run tags whose only purpose is to
exercise the build + TestPyPI half of the pipeline without polluting
real PyPI.

### `Create GitHub Release`

`softprops/action-gh-release@v2` with `generate_release_notes: true`
attaches the `dist/*` files to a new GitHub Release. Also skipped for
`-testpypi` tags.

---

## 8. release-please

`.github/workflows/release-please.yml` runs `googleapis/release-please-action@v4`
on every push to `main`. The action scans Conventional Commits since the
last release tag and:

1. Computes the next semver version using the rules in
   `.release-please-config.json`.
2. Opens or updates a single open PR titled `chore: release X.Y.Z`. The
   PR bumps `version` in `pyproject.toml`, regenerates `CHANGELOG.md`,
   and updates `.release-please-manifest.json`.
3. When the maintainer merges that PR, release-please tags the release
   commit `vX.Y.Z` and creates a GitHub Release.
4. The new tag triggers `release.yml`, which publishes to PyPI.

### `.release-please-config.json`

* `release-type: python` — knows about `pyproject.toml` and how to bump
  it.
* `bump-minor-pre-major: false` and
  `bump-patch-for-minor-pre-major: true` — pre-1.0 versioning is
  conservative: `feat`, `fix`, `perf`, `refactor` all bump patch.
  `feat!` (breaking) bumps minor. The 1.0.0 jump is explicit.
* `include-component-in-tag: false` — tag names are `v0.1.2`, not
  `tgtg-cli-v0.1.2`.
* `pull-request-title-pattern: "chore: release ${version}"` — the
  release PR title matches Conventional Commits so commitlint is happy.
* `changelog-sections` — `feat`, `fix`, `perf`, `refactor`, `docs`
  appear in the changelog under headed sections; `ci`, `chore`, `test`,
  `style`, `build` are hidden as noise.

### `.release-please-manifest.json`

`{ ".": "0.1.0" }` — the version release-please considers "currently
released". Bumped automatically by the action when a release PR is
merged.

---

## 9. PyPI Trusted Publishing (OIDC)

PyPI verifies, via OIDC, that an upload comes from a specific repo +
workflow + environment combination. **No API tokens are stored anywhere
in the repository or in GitHub Secrets.**

### Pending publishers

Set up once on PyPI and TestPyPI for the project name, repo, workflow
filename (`release.yml`), and environment (`pypi` / `testpypi`). The
first successful upload converts the "pending publisher" into a real
"trusted publisher".

### `id-token: write` permission

Granted **only** on the publish jobs in `release.yml`, never globally.
This follows the least-privilege principle: only those jobs can mint
the OIDC token PyPI requires.

---

## 10. GitHub Repository Configuration

### General settings

* Default branch: `main`.
* Issues: enabled; Discussions: enabled; Wiki: disabled (Discussions
  carries the Q&A use case).
* Merge methods: **squash only**. Merge commits and rebase merges are
  disabled to keep `main` linear.
* `squash_merge_commit_title = PR_TITLE`,
  `squash_merge_commit_message = BLANK` — the squashed commit message is
  exactly the PR title (Conventional Commits format) without the PR
  body.
* Auto-delete head branches after merge: enabled.

### Branch protection on `main`

* Require pull request before merging.
* Required approving review count: **0** (solo project; the PR
  workflow itself is the gate, not human review).
* Dismiss stale approvals on new commits.
* Required status checks (12 total): `Lint (ruff)`, all 9 `Test (…)`
  matrix cells, `Commit messages`, `Branch name`. `Type check (ty)` is
  intentionally excluded while continue-on-error is in place.
* Strict status checks (`strict: true`) — branch must be up-to-date
  before merging.
* Required conversation resolution: enabled.
* Required linear history: enabled.
* Force pushes: blocked. Branch deletion: blocked.
* Include administrators: **disabled** — solo escape hatch for emergency
  pushes.

### Environments

* `testpypi`: no protection rules.
* `pypi`: created without reviewer-protection (free-plan private repos
  cannot enable that rule). Once the repo goes public, a required
  reviewer (the maintainer) will be added so a deploy to real PyPI
  cannot ship without an explicit approval click.

### Security toggles

* Dependabot vulnerability alerts: enabled (free for private repos).
* Dependabot automated security fixes: enabled.
* Secret scanning + push protection: deferred — unavailable on free
  private plans, will be enabled on public-switch.
* CodeQL Default setup: deferred — same reason.

---

## 11. Issue and PR Templates

`.github/ISSUE_TEMPLATE/config.yml` disables blank issues and routes
non-issue traffic via two contact links: usage questions go to the
Discussions Q&A category, security reports go to the private advisory
form. Contributors clicking "New issue" see those cards before they see
templates, which keeps the issue tracker focused.

`bug_report.yml` is a structured YAML form with required fields for
version, OS, Python version, repro steps, and expected behaviour. It
also asks the reporter to confirm they have searched existing issues
and redacted personal data (tokens, emails, payment info) from any
pasted logs.

`enhancement.yml` covers new features, improvements, refactors,
performance work, and documentation in a single template. The Type
dropdown drives triage. Motivation and proposed solution are required;
alternatives and additional context are optional.

`PULL_REQUEST_TEMPLATE.md` is markdown rather than YAML — less friction
for the author. It asks for a 1–3 sentence summary, a change-type
checkbox, and a checklist (branch naming, CC commits, tests, pre-commit,
optional CHANGELOG entry).

---

## 12. Dependabot

Currently **UI-managed**, no `.github/dependabot.yml` is committed.
Vulnerability alerts notify the maintainer when a CVE lands in a
declared dependency. Automated security fixes open PRs that bump the
affected package to the smallest patched version. Proactive
non-vulnerability version-update PRs are intentionally not enabled — the
review burden was judged disproportionate for a hobby project.

---

## 13. Health Files

* `.github/CONTRIBUTING.md` — dev setup, branch naming, CC, local
  test/lint commands, PR expectations. GitHub auto-detects this path
  and surfaces it on the "New pull request" page.
* `.github/SECURITY.md` — minimal vulnerability-reporting policy
  pointing to GitHub's private advisories. Surfaced on the Security tab
  and as a banner on "New issue".
* `LICENSE` — MIT, kept at repo root because PyPI / GitHub UI / OSS
  scanners look there first.
* `CHANGELOG.md` — Keep-a-Changelog format, maintained by
  release-please.
* `README.md` — public-facing; currently minimal with a prominent
  unofficial-tool disclaimer (trademark, ToS).

---

## 14. Common Workflows

### Adding a feature

1. `git checkout -b feat/<short-desc>` from up-to-date `main`.
2. Implement, write tests under `tests/`.
3. Run `uv run pre-commit run --all-files` and `uv run pytest`.
4. Commit with `feat(<scope>): <subject>`.
5. Push, open PR, wait for CI to be green.
6. Squash-merge once required checks pass.

### Cutting a release

1. Merge feature/fix PRs into `main` over time.
2. release-please opens / updates a "chore: release X.Y.Z" PR.
3. Review the proposed CHANGELOG and version bump.
4. Squash-merge the release PR.
5. release-please tags `vX.Y.Z` and drafts a GitHub Release.
6. `release.yml` runs: build → TestPyPI → PyPI → GitHub Release
   assets.
7. Verify the new version on PyPI and the rendered release notes on
   GitHub.

### TestPyPI dry-run

`git tag v0.0.0aN-testpypi && git push origin v0.0.0aN-testpypi`. The
suffix triggers the TestPyPI-only branch of `release.yml`. Real PyPI is
untouched.

### Hotfix

For a bug found in production: branch `fix/<short-desc>` from `main`,
fix it, PR, merge. release-please will pick it up on the next release
PR. If you need an immediate release without batching other commits,
just merge the fix and merge the release PR right after.

### Updating a dependency

Edit `pyproject.toml`, run `uv lock`. For a Dependabot security PR,
review the diff in the auto-generated PR and merge once CI is green.

---

## 15. Verifying the Setup

Quick checklist commands to confirm everything is wired up:

```bash
# Install everything
uv sync

# Lint + tests
uv run ruff check .
uv run pytest

# Pre-commit on all files
uv run pre-commit run --all-files

# Build a local wheel
uv build
uv run python -m twine check dist/*

# Confirm CI status of latest commit
gh run list --repo peterschwps/TGTG-CLI --limit 5

# Confirm branch protection contexts
gh api /repos/peterschwps/TGTG-CLI/branches/main/protection \
  --jq '.required_status_checks.contexts'
```
