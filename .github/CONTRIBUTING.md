# Contributing to TooGoodToGo-CLI

Thanks for your interest in contributing!

## Development setup

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
git clone https://github.com/peterschwps/TooGoodToGo-CLI.git
cd TooGoodToGo-CLI
uv sync
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

## Branch naming

Use `<type>/<short-kebab-description>`:

- `feat/multi-watch`
- `fix/3ds-timeout`
- `chore/release-tooling`

Allowed types: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`,
`perf`, `test`, `build`, `ci`, `revert`.

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/).
Format:

```
<type>(<optional-scope>): <subject>
```

Examples:

- `feat(monitor): add multi-store watch list`
- `fix(api): retry on capsolver timeout`
- `docs: clarify pipx install path`

The commit-msg pre-commit hook enforces this locally. CI re-checks
on every PR. The VSCode extension
[`vivaxy.vscode-conventional-commits`](https://marketplace.visualstudio.com/items?itemName=vivaxy.vscode-conventional-commits)
helps with the format.

## Tests and linting

```bash
uv run pytest                # run tests
uv run ruff check .          # lint
uv run pre-commit run --all-files   # everything pre-commit checks
```

## Pull requests

- Keep PRs small and focused on one change.
- Make sure CI passes before requesting review.
- `CHANGELOG.md` is maintained automatically by release-please from
  the commit messages — no manual changelog edits needed.
- Squash-merge is the only allowed merge style.
