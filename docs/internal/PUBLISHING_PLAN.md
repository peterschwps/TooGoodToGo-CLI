# Plan: TGTG-CLI — Private Draft → Public Open Source (GitHub + PyPI)

## 1. Context

Python 3.12+ CLI, src-layout, hatchling backend, UV deps. Ruff already configured (line-length 79, double quotes, rules E/F/UP/B/SIM/G/I). GitHub remote `peterschwps/TooGoodToGo-Monitor` is private + empty.

**Critical gaps**: no LICENSE, no real README, no tests, no CI, no contribution docs, no security policy, no pre-commit, no issue templates, no release pipeline. pyproject.toml has placeholder description, no classifiers/URLs/license metadata, no dev extras.

This plan turns it into a publishable, contributable, defensible OSS release. Opinionated — one recommendation per area, alternatives briefly noted.

---

## 2. Critical Pre-Flight (DECIDED)

### 2.1 Naming — KEEP AS-IS, accept risk + disclaimer

**Decision**: PyPI dist `TGTG-CLI`, module `tgtg_cli`, console script `tgtg-cli`, repo `TooGoodToGo-Monitor` all unchanged. Disclaimer in README.

**Acknowledged risks** (user accepts):
- "Too Good To Go" + logo registered EU trademark (EUIPO, Too Good To Go ApS, DK). "TGTG" treated as protected abbreviation. PyPI takedown on trademark complaint possible.
- TGTG ToS forbids reverse engineering / automated access. Account termination + EU-contract-law liability risk.
- Capsolver / 3DS-bypass code raises CFAA / §202a StGB concerns.

**Disclaimer block** (place prominently in README, top of file):
```markdown
> **⚠️ Unofficial Third-Party Tool**
>
> This project is **not affiliated with, endorsed by, or connected to Too Good To Go ApS** in any way.
> "Too Good To Go" and "TGTG" are trademarks of Too Good To Go ApS, used here only nominatively
> to identify the service this tool interacts with. Use at your own risk; using this tool may
> violate the Too Good To Go Terms of Service and result in account termination.
```

Also add `NOTICE` file at repo root with same text (some lawyers/scanners look for it).

### 2.2 License — MIT (DECIDED)

SPDX text from <https://spdx.org/licenses/MIT.html>, save as `LICENSE` (no extension). Year + "Peter Schwips" in copyright line.

---

## 3. Repository Hygiene

| File | Purpose |
|---|---|
| `LICENSE` | MIT text + current year + your name |
| `README.md` | Badges, description, **disclaimer**, install (`pipx`/`uv tool`), quickstart, configuration, dev, contributing, license |
| `CHANGELOG.md` | "Keep a Changelog" format, start with `## [Unreleased]` + `## [0.1.0] — YYYY-MM-DD` |
| `CONTRIBUTING.md` | Dev setup (`uv sync --all-extras`), pre-commit, branch + commit conventions, PR checklist |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1, copy verbatim from contributor-covenant.org |
| `SECURITY.md` | Use GitHub *private vulnerability reporting* (`Security → Report a vulnerability`). Contact email. Supported versions (latest minor). |
| `.gitignore` | GitHub `Python.gitignore` template + `.env`, `*.log`, `.coverage*`, `htmlcov/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.venv/` |
| `.gitattributes` | Verify `* text=auto eol=lf` |

**Working notes** (`IDEAS.md`, `NOTES.md`, `TODO.md`): move to `docs/internal/` (excluded from wheel) or delete. They shouldn't ship in PyPI artifact.

---

## 4. pyproject.toml Completion

```toml
[project]
name = "TGTG-CLI"
version = "0.1.0"
description = "Unofficial CLI for Too Good To Go. Not affiliated with Too Good To Go ApS."
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"                      # PEP 639 SPDX expression (hatchling >=1.27)
license-files = ["LICENSE"]
authors = [{ name = "Peter Schwips", email = "peter.schwips@gmail.com" }]
keywords = ["cli", "monitor", "food-waste", "surplus"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Utilities",
]
dependencies = [ ... ]               # unchanged

[project.urls]
# NOTE: these point to the *final* publish target (TGTG-CLI), not the working dev repo (TooGoodToGo-Monitor).
# Populate now so the URLs are correct from the first PyPI release.
Homepage   = "https://github.com/peterschwps/TGTG-CLI"
Repository = "https://github.com/peterschwps/TGTG-CLI"
Issues     = "https://github.com/peterschwps/TGTG-CLI/issues"
Changelog  = "https://github.com/peterschwps/TGTG-CLI/blob/main/CHANGELOG.md"

[project.scripts]
tgtg-cli = "tgtg_cli.cli.__main__:main"

[project.optional-dependencies]
dev = [
    "pytest>=8.3", "pytest-cov>=5", "pytest-mock>=3.14",
    "responses>=0.25",
    "mypy>=1.13", "types-requests", "types-beautifulsoup4",
    "pre-commit>=4.0", "ruff>=0.8", "build>=1.2",
]

[tool.hatch.version]
path = "src/tgtg_cli/__init__.py"   # single source: __version__ = "0.1.0"

[tool.pytest.ini_options]
addopts = "-ra --strict-markers --cov=tgtg_cli --cov-report=term-missing"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["src/tgtg_cli"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src", "tests"]
```

UV: `uv sync --all-extras` reads optional-dependencies natively.

---

## 5. Pre-Commit Configuration

Astral's official hook: **`https://github.com/astral-sh/ruff-pre-commit`** (rev tags follow ruff versions).

`.pre-commit-config.yaml`:

```yaml
default_language_version:
  python: python3.12

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: mixed-line-ending
        args: [--fix=lf]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.6.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
```

Install:
```
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
uv run pre-commit run --all-files
```

Document in CONTRIBUTING.md.

---

## 6. Commit + Branch Naming

**Recommendation: migrate from `Feat:`/`Fix:` to Conventional Commits.**

Why: lingua franca of OSS, off-the-shelf enforcement, unlocks **release-please** / **python-semantic-release** for auto changelog + version bumping.

Format: `type(optional-scope): subject`
Types: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `revert`.
Breaking: `feat!:` or `BREAKING CHANGE:` footer.

Examples:
- `feat(monitor): add multi-store watch list`
- `fix(api): retry on capsolver timeout`
- `docs: clarify pipx install path`

Migration: don't rewrite history. Mark adoption with `chore: adopt Conventional Commits`.

**Branch naming**: `<type>/<short-kebab-desc>` — `feat/multi-watch`, `fix/3ds-timeout`, `chore/release-tooling`.

**Enforcement**:
- Commit msgs: `conventional-pre-commit` locally + `wagoid/commitlint-github-action@v6` on PRs.
- Branch names: `pull_request` workflow regex `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`.

---

## 7. Branching Strategy

**Recommendation: trunk-based** — `main` always releasable, short-lived feature branches, squash-merge.

GitFlow (`develop`/`release/*`/`hotfix/*`) overkill: solo project, tag-driven releases, no parallel maintenance.

**Actions**:
- `main` is default + only protected long-lived branch.
- Delete `dev` after merging anything still useful into a feature branch off `main`.
- Existing `new-architecture`, `settings-handling`, `settings-usage`: rebase onto `main`, open PRs, squash-merge, delete.
- Future work: `git checkout -b feat/<thing>` from up-to-date `main`.

---

## 8. GitHub Repository Configuration

**General**:
- Default branch `main`.
- Issues ON, Discussions ON, Wiki OFF.
- PRs: allow squash merge **only** (linear history). Auto-delete head branches.

**Branch protection for `main`** (Settings → Branches):
- Require PR before merging
- Require approvals: 1 (or 0 if strictly solo + admin override; rely on status checks instead)
- Dismiss stale approvals on new commits
- Required status checks: `lint`, `type-check`, `test (3.12)`, `test (3.13)`, `commitlint`, `branch-name`
- Require branches up to date
- Require conversation resolution
- Require linear history
- Block force pushes
- Block deletions
- *Optional*: signed commits (GPG/SSH key on GitHub)
- Include administrators OFF for solo (admin override useful)

**Tag protection** (Settings → Tags): protect `v*` from delete/force-update — load-bearing for release workflow.

**Security tab** (free for public repos):
- Dependency graph ON
- Dependabot alerts ON
- Dependabot security updates ON
- Secret scanning + push protection ON
- CodeQL ON (default workflow)
- Private vulnerability reporting ON

**Actions permissions** (Settings → Actions): allow `actions/*` and `astral-sh/*`. Default workflow permissions: read; jobs request more explicitly.

---

## 9. Issue & PR Templates

`.github/ISSUE_TEMPLATE/config.yml` (URLs already point at final repo):
```yaml
blank_issues_enabled: false
contact_links:
  - name: Question / Discussion
    url: https://github.com/peterschwps/TGTG-CLI/discussions
    about: For usage questions, use Discussions.
  - name: Security Vulnerability
    url: https://github.com/peterschwps/TGTG-CLI/security/advisories/new
    about: Report security issues privately.
```

`.github/ISSUE_TEMPLATE/bug_report.yml`:
```yaml
name: Bug report
description: Report something that doesn't work as expected.
title: "bug: "
labels: ["bug", "triage"]
body:
  - type: input
    id: version
    attributes:
      label: Version
      description: Output of `tgtg-cli --version`
    validations: { required: true }
  - type: dropdown
    id: os
    attributes:
      label: Operating system
      options: [macOS, Linux, Windows, Other]
    validations: { required: true }
  - type: textarea
    id: what-happened
    attributes: { label: What happened? }
    validations: { required: true }
  - type: textarea
    id: reproduce
    attributes:
      label: Steps to reproduce
      placeholder: |
        1. Run `tgtg-cli ...`
        2. ...
    validations: { required: true }
  - type: textarea
    id: expected
    attributes: { label: Expected behaviour }
    validations: { required: true }
  - type: textarea
    id: logs
    attributes:
      label: Logs
      description: Redact tokens, emails, payment data.
      render: shell
  - type: checkboxes
    id: terms
    attributes:
      label: Confirmation
      options:
        - { label: "I have searched existing issues.", required: true }
        - { label: "I have redacted personal data from logs.", required: true }
```

`feature_request.yml`: analogous (problem, proposed solution, alternatives, context, label `enhancement`).
`task.yml`: simple form for internal TODOs migrated from `TODO.md`, label `task`.

`.github/PULL_REQUEST_TEMPLATE.md`:
```markdown
## Summary
<!-- 1–3 sentences -->

## Type
- [ ] feat
- [ ] fix
- [ ] docs
- [ ] refactor / chore
- [ ] BREAKING CHANGE

## Checklist
- [ ] Branch named `<type>/<short-desc>`
- [ ] Commits follow Conventional Commits
- [ ] Tests added/updated
- [ ] `pre-commit run --all-files` passes
- [ ] CHANGELOG entry under `## [Unreleased]`

## Related
Closes #
```

---

## 10. CI Workflows (`.github/workflows/`)

### `ci.yml` — push to main + PRs
```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:
permissions: { contents: read }
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { enable-cache: true }
      - run: uv sync --all-extras
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - run: uv run mypy

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest]
        python-version: ["3.12", "3.13"]
        include:
          - { os: macos-latest,   python-version: "3.12" }
          - { os: windows-latest, python-version: "3.12" }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with: { enable-cache: true }
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync --all-extras --python ${{ matrix.python-version }}
      - run: uv run pytest

  commitlint:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: wagoid/commitlint-github-action@v6

  branch-name:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - run: |
          echo "${{ github.head_ref }}" \
            | grep -Eq '^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$' \
            || (echo "Branch must match <type>/<kebab-desc>" && exit 1)
```

### `release.yml` — tag-driven, Trusted Publishing, no API token
```yaml
name: Release
on:
  push:
    tags: ["v*"]
permissions:
  contents: write     # for GitHub Release
  id-token: write     # for PyPI OIDC
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: actions/upload-artifact@v4
        with: { name: dist, path: dist/ }

  publish-testpypi:
    needs: build
    runs-on: ubuntu-latest
    environment: testpypi
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1   # OIDC default

  github-release:
    needs: publish-pypi
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/*
          generate_release_notes: true
```

### `codeql.yml`
GitHub default Python CodeQL workflow (Settings → Code scanning → *Set up CodeQL*; commits the workflow). Schedule weekly + on push to `main` + on PR.

### Alternative: pre-commit.ci
Hook up <https://pre-commit.ci/> instead of running pre-commit in `ci.yml`. Auto-fixes on PRs, weekly hook updates. Free for public repos. Add status check to branch protection.

---

## 11. PyPI Publishing

### One-time: Trusted Publishing
1. Build locally first: `uv build` → `dist/*.whl` + `*.tar.gz`.
2. **PyPI**: log in → *Your projects* → *Publishing* → *Add a pending publisher*:
   - Project: `TGTG-CLI`
   - Owner: `peterschwps`
   - Repo: `TGTG-CLI` (the FINAL repo, not the dev repo `TooGoodToGo-Monitor`)
   - Workflow: `release.yml`
   - Environment: `pypi`
3. Same on **TestPyPI** with environment `testpypi`.
4. GitHub *Environments* `pypi` + `testpypi` (Settings → Environments). For `pypi`, deployment protection rule (required reviewer = you) so release can't slip out unattended.
5. First publish via workflow turns *pending* publisher into real one.

### Releasing
1. Bump `__version__` in `src/tgtg_cli/__init__.py` (or `uv run hatch version minor`).
2. Move `## [Unreleased]` content under `## [0.2.0] — 2026-05-12`.
3. PR + merge.
4. Tag + push:
   ```
   git tag -a v0.2.0 -m "v0.2.0"
   git push origin v0.2.0
   ```
5. `release.yml` builds → TestPyPI → PyPI → GitHub Release.

### Version bumping
- **Recommendation: `bump-my-version`** — single config, plays well with hatchling.
- Alternatives: `hatch version <segment>` (built-in), or **`python-semantic-release`** for fully-automated bumps from CC commits.

### Pre-flight: TestPyPI dry run
Push pre-release tag `v0.1.0a1` first. Verify install:
```
pip install -i https://test.pypi.org/simple/ TGTG-CLI==0.1.0a1
```

---

## 12. VSCode Settings + EditorConfig

**Commit a minimal shared `.vscode/`** — team settings, not personal prefs.

`.vscode/settings.json` (commit):
```json
{
  "editor.rulers": [79],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.tabSize": 4
  },
  "python.analysis.typeCheckingMode": "standard"
}
```

`.vscode/extensions.json` (commit):
```json
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "tamasfe.even-better-toml",
    "editorconfig.editorconfig"
  ]
}
```

`.gitignore` (EditorConfig pattern — ignore `.vscode/*` except shared bits):
```
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
!.vscode/launch.json
!.vscode/tasks.json
```

**Add `.editorconfig`** — language-agnostic, works across PyCharm/JetBrains/vim/Sublime/GitHub web editor, so line-length 79 honored even by non-VSCode contributors:
```ini
root = true
[*]
end_of_line = lf
charset = utf-8
indent_style = space
indent_size = 4
trim_trailing_whitespace = true
insert_final_newline = true
[*.py]
max_line_length = 79
[*.{yml,yaml,json,toml}]
indent_size = 2
[*.md]
trim_trailing_whitespace = false
```

Real enforcement is `ruff format` (pre-commit + CI) — authoritative regardless of editor. EditorConfig + shared VSCode settings just make the right thing happen out of the box.

---

## 13. Other Recommended Tooling

| Concern | Recommendation | Alternative |
|---|---|---|
| Dependency updates | **Dependabot** (`.github/dependabot.yml`) — native, free, `pip` + `github-actions` | Renovate |
| Pre-commit in CI | **pre-commit.ci** | Run pre-commit as CI job |
| Coverage | **Codecov** GitHub App + `codecov/codecov-action@v4` | Coveralls |
| Type checking | **mypy --strict** | Pyright |
| Auto changelog + version | **release-please** (DECIDED — see §13a) — opens PR bumping version + updating CHANGELOG from CC commits, merge → tag → triggers `release.yml` | python-semantic-release |
| Docs (later) | **MkDocs Material** (`mkdocs gh-deploy`) | Sphinx |
| Badges | shields.io: PyPI version, Python versions, CI, license, codecov, pre-commit | — |
| Contributors | **all-contributors-bot** (comment commands) | — |

### 13a. release-please (DECIDED)

Replaces manual version bumping + manual CHANGELOG editing. Flow:

1. You push CC commits to `main` (via PRs).
2. `release-please` Action runs on every push to `main`. It scans CC commits since last release and **opens/updates a "release PR"**: bumps version in `pyproject.toml` + `src/tgtg_cli/__init__.py`, regenerates `CHANGELOG.md`.
3. You review + merge the release PR when ready.
4. release-please tags `v0.X.Y` automatically + creates GitHub Release.
5. Tag push triggers `release.yml` (§10) → builds → publishes to TestPyPI then PyPI.

`.github/workflows/release-please.yml`:
```yaml
name: release-please
on:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          release-type: python
          package-name: TGTG-CLI
          # bumps version in pyproject.toml + __init__.py via .release-please-config.json
          config-file: .release-please-config.json
          manifest-file: .release-please-manifest.json
```

`.release-please-config.json`:
```json
{
  "release-type": "python",
  "packages": {
    ".": {
      "package-name": "TGTG-CLI",
      "changelog-path": "CHANGELOG.md",
      "extra-files": [
        "src/tgtg_cli/__init__.py"
      ]
    }
  },
  "include-component-in-tag": false,
  "pull-request-title-pattern": "chore: release ${version}"
}
```

`.release-please-manifest.json` (initial):
```json
{ ".": "0.1.0" }
```

`src/tgtg_cli/__init__.py` must contain a parseable line like:
```python
__version__ = "0.1.0"  # x-release-please-version
```

The trailing comment is the marker release-please uses to find + update the version line.

**Manual override**: you can still tag manually for hotfixes. release-please respects existing tags.

`.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule: { interval: "weekly" }
    groups:
      dev-dependencies:
        dependency-type: "development"
    open-pull-requests-limit: 10
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly" }
```

---

## 13b. Final Repo Migration (TooGoodToGo-Monitor → TGTG-CLI)

**Current state**: working repo is `peterschwps/TooGoodToGo-Monitor` (existing, currently private). Final publish target is a **different empty repo** `peterschwps/TGTG-CLI`. We continue developing on `TooGoodToGo-Monitor` and only at release time push to `TGTG-CLI`.

### What needs to change at migration time

When you switch the `origin` remote from `TooGoodToGo-Monitor` → `TGTG-CLI` (or push to both), every place that hardcodes the old repo URL must be updated. Single search-and-replace target:

```
peterschwps/TooGoodToGo-Monitor  →  peterschwps/TGTG-CLI
```

**Files that contain the old URL and must be updated**:

| File | What to change |
|---|---|
| `pyproject.toml` `[project.urls]` | `Homepage`, `Repository`, `Issues`, `Changelog` URLs |
| `README.md` | Badges (CI, codecov, PyPI, etc.), clone instructions, install-from-source examples, contributing links |
| `CONTRIBUTING.md` | Repo URL in clone instructions |
| `SECURITY.md` | Private vulnerability reporting URL |
| `.github/ISSUE_TEMPLATE/config.yml` | Discussions URL + security advisories URL |
| `CHANGELOG.md` | Compare-link URLs at the bottom (`[Unreleased]: https://github.com/.../compare/v0.1.0...HEAD`) |
| `.github/dependabot.yml` | No URLs needed; safe |
| `.github/workflows/*.yml` | No hardcoded repo URLs (uses `${{ github.repository }}` implicitly); safe |

**Things that need re-doing on the new repo, not just URL-replacement**:

1. **PyPI Trusted Publisher**: re-create the pending publisher on PyPI + TestPyPI with the new owner/repo. The old pending publisher must be deleted, otherwise the new repo can't publish under the same project.
   - PyPI → *Your projects* → `TGTG-CLI` → *Publishing* → delete old → add new (Owner: `peterschwps`, Repo: `TGTG-CLI`, Workflow: `release.yml`, Environment: `pypi`).
2. **Branch protection rules**: must be re-configured on the new repo (settings don't transfer).
3. **Repo settings** (Issues/Discussions on, Wiki off, squash-merge only, auto-delete branches): re-configure.
4. **Security tab settings**: Dependabot, secret scanning, CodeQL, private vulnerability reporting — all re-enable.
5. **GitHub Environments** (`pypi`, `testpypi`) with deployment protection rules: re-create.
6. **Tag protection** for `v*`: re-add.
7. **release-please state**: copy `.release-please-manifest.json` + `CHANGELOG.md` over so release-please knows the last released version. Don't reset it.
8. **CodeQL workflow**: GitHub may regenerate it; if you committed your own `codeql.yml`, just push it.
9. **Existing tags**: if you've tagged anything during dev, push tags too (`git push <new-remote> --tags`).
10. **Issues/PRs/Discussions content from the dev repo**: NOT auto-migrated. Either don't open public-facing issues until you're on the final repo, or use GitHub's *Transfer ownership / repository* feature in Settings if you want to preserve history.

### Two migration approaches

**A) Fresh push** (simplest, recommended if dev repo has sensitive history):
```
git remote set-url origin https://github.com/peterschwps/TGTG-CLI.git
git push -u origin main
git push origin --tags
```
Loses old repo's issues/PRs.

**B) GitHub repo transfer** (preserves issues/PRs/stars):
GitHub Settings → *Transfer ownership* — but that **renames the same repo**, doesn't push to a different empty one. To go from `TooGoodToGo-Monitor` → `TGTG-CLI`:
1. Delete the empty `TGTG-CLI` repo.
2. Settings on `TooGoodToGo-Monitor` → *Rename* → `TGTG-CLI`.
3. Old URL automatically redirects.
4. Update local remote: `git remote set-url origin https://github.com/peterschwps/TGTG-CLI.git`.

Approach B is simpler but means dev history is fully public. Approach A lets you sanitize first (e.g. `git filter-repo` to scrub any leaked secrets) before going public.

**Recommendation**: do approach A for the *first* public push. If you want to preserve dev artifacts later, you can transfer/rename.

### Search-and-replace command (sanity check before push)

```
grep -rn "TooGoodToGo-Monitor" --include="*.toml" --include="*.md" --include="*.yml" --include="*.json" .
```

Should return zero matches before tagging the first release on the new repo.

---

## 14. Push to Empty Repo

Repo empty → first push is normal `-u` push. Run from real checkout (not worktree):

```
git status                             # clean state
git remote -v                          # confirm origin URL
git branch --show-current              # confirm `main`
git push -u origin main                # publishes main + sets upstream
git push origin --tags                 # publish local tags
```

If only `master`:
```
git branch -m master main
git push -u origin main
```

After first push:
1. Configure branch protection (§8) — must do this *after* `main` exists.
2. Push other branches you want to keep.
3. Delete `dev` once content rebased onto `main`.

**Note**: GitHub MCP not available in this session, no `gh` CLI either. Either install `gh` (`brew install gh`) or do GitHub config via web UI. The MCP-related section in your prompt suggests it should be available — if it works in your normal sessions, just use it for the push + repo config.

---

## 15. Verification

- **Pre-commit local**: `uv run pre-commit run --all-files` — passes after one `--fix` round.
- **Lint/type/test local**: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`.
- **Build dry run**: `uv build` → expect `dist/tgtg_cli-0.1.0-py3-none-any.whl` + `.tar.gz`. `unzip -l dist/*.whl` to verify shipped files.
- **Metadata sanity**: `uv run python -m twine check dist/*` — checks PyPI long-description rendering.
- **TestPyPI**: tag `v0.1.0a1` → push → `release.yml` runs → install in clean venv: `uvx --from TGTG-CLI==0.1.0a1 --index https://test.pypi.org/simple/ tgtg-cli --version`.
- **Branch protection**: open throwaway PR with bad commit msg + non-conforming branch name — `commitlint` + `branch-name` checks must fail; merge button blocked.
- **Trusted Publishing**: confirm no `PYPI_API_TOKEN` secret — workflow still publishes via OIDC.
- **Security tab**: Dependabot, secret scanning, CodeQL all show "enabled" with at least one completed scan.
- **Rendering**: GitHub repo page (badges, install, disclaimer) + PyPI page after first publish.

---

## 16. Critical Files List

**Create or modify** (all in current worktree `claude/hopeful-bhabha-e514a3`):
- [pyproject.toml](pyproject.toml) — fill metadata, dev extras, hatch version, pytest/coverage/mypy config (name stays `TGTG-CLI`)
- `LICENSE` — MIT text
- `NOTICE` — trademark disclaimer
- [README.md](README.md) — full rewrite, prominent unofficial disclaimer at top
- `CHANGELOG.md` — Keep a Changelog skeleton (release-please takes over after first commit)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- [.gitignore](.gitignore) — expand
- `.editorconfig`
- `.pre-commit-config.yaml`
- [.vscode/settings.json](.vscode/settings.json) — expand
- `.vscode/extensions.json`
- `.github/dependabot.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/release-please.yml`
- `.github/workflows/codeql.yml`
- `.release-please-config.json`
- `.release-please-manifest.json`
- `.github/ISSUE_TEMPLATE/{config,bug_report,feature_request,task}.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- [src/tgtg_cli/__init__.py](src/tgtg_cli/__init__.py) — add `__version__ = "0.1.0"  # x-release-please-version`
- `tests/__init__.py` + `tests/test_smoke.py` — package import + CLI entry-point smoke test

**Working notes cleanup**: move `IDEAS.md`, `NOTES.md`, `TODO.md` into `docs/internal/` (excluded from wheel) or migrate content to GitHub Issues + delete files.

**Top-5 load-bearing — fix first, rest follow**:
1. `pyproject.toml`
2. `.github/workflows/release.yml`
3. `.github/workflows/release-please.yml`
4. `.pre-commit-config.yaml`
5. `LICENSE`

---

## 17. Implementation Order

Suggested commit-by-commit ordering (each is one PR, all CC-formatted):

1. `chore: adopt Conventional Commits` (just a marker commit on a branch with this plan moved to `docs/internal/`)
2. `docs: add LICENSE + NOTICE + disclaimer in README`
3. `chore: complete pyproject.toml metadata + dev extras`
4. `chore: add .editorconfig + expand .vscode shared settings`
5. `chore: add pre-commit config with ruff + conventional-pre-commit`
6. `test: add tests/test_smoke.py + pytest config`
7. `ci: add ci.yml (lint, type-check, test matrix, commitlint, branch-name)`
8. `ci: add codeql + dependabot`
9. `docs: add CONTRIBUTING + CODE_OF_CONDUCT + SECURITY`
10. `chore: add issue + PR templates`
11. `ci: add release.yml with Trusted Publishing`
12. `ci: add release-please workflow + config`
13. (after first PR merged on GitHub) configure branch protection, security tab, environments, Trusted Publisher
14. Tag `v0.1.0a1` → TestPyPI dry run
15. Tag `v0.1.0` → first real PyPI release

---

## 18. Open Follow-Ups

### Before the first tag (one-time PyPI Trusted Publishing setup)

`.github/workflows/release.yml` uses Trusted Publishing (OIDC). No
API tokens are stored anywhere. PyPI must learn to trust the
workflow up front, otherwise the very first tagged release will be
rejected. Do this once, before pushing any `v*` tag:

1. Create accounts on **PyPI** and **TestPyPI** if you do not already
   have them. They are separate registries with separate logins.
2. PyPI → *Your account* → *Publishing* → *Add a pending publisher*:
   - Project name: `TGTG-CLI`
   - Owner: `peterschwps`
   - Repository: `TGTG-CLI` (the FINAL repo, not `TooGoodToGo-Monitor`)
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
3. Repeat the same on TestPyPI with environment name `testpypi`.
4. In the GitHub repo, create two **Environments** (Settings →
   Environments): `pypi` and `testpypi`. For `pypi`, add a deployment
   protection rule with yourself as required reviewer so a release
   can never slip out unattended.
5. Optional: protect `v*` tags from delete / force-update (Settings
   → Tags → New rule).

### After the first push to the final TGTG-CLI repo

Run these via `gh` CLI (installed at `/opt/homebrew/bin/gh`,
authenticated as `peterschwps`) once `main` is on the public
`peterschwps/TGTG-CLI` repo:

```bash
REPO=peterschwps/TGTG-CLI

# Dependabot vulnerability alerts + auto-PRs for vulnerable deps.
gh api -X PUT "/repos/$REPO/vulnerability-alerts" --silent
gh api -X PUT "/repos/$REPO/automated-security-fixes" --silent

# Secret scanning + push protection (free for public repos).
gh api -X PATCH "/repos/$REPO" \
  -F security_and_analysis[secret_scanning][status]=enabled \
  -F security_and_analysis[secret_scanning_push_protection][status]=enabled

# CodeQL: enable via the UI for the "Default" setup
#   https://github.com/$REPO/settings/security_analysis
# (gh has no API yet for CodeQL Default setup; one click in the UI.)
```

Version-update PRs (proactive Dependabot for non-vulnerable
updates) are intentionally skipped — too noisy for this project.
Only security-driven updates run.

### ty type checker

- `[tool.ty]` block is not yet configured. Default strictness produces
  many warnings on the existing codebase.
- The `type-check` job in `.github/workflows/ci.yml` currently runs
  with `continue-on-error: true` so ty does not block PRs.
- Action items, in order:
  1. Add `[tool.ty]` configuration in `pyproject.toml` (scope to `src`
     and `tests`, suppress noisy categories until the codebase is
     cleaned up).
  2. Fix or `# type: ignore[...]` the remaining real findings.
  3. Remove `continue-on-error: true` from the `type-check` job and
     add it to the required status checks for `main`.
