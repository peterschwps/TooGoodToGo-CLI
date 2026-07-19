# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

TGTG-CLI is an unofficial CLI for Too Good To Go (TGTG) that monitors items in a given area and can automatically check them out, including handling 3DS payment challenges. It's a Typer-based interactive terminal application (Python 3.12+), published to PyPI as `TGTG-CLI` with console-script entry points `tgtg`, `tgtg-cli`, `toogoodtogo`, `toogoodtogo-cli` (all pointing to `tgtg_cli.cli.__main__:main`).

## Commands

Uses `uv` for dependency management (requires Python 3.12+).

```bash
uv sync                              # install all deps into project-local venv
uv run tgtg                          # run the CLI locally
uv run pytest                        # run all tests
uv run pytest tests/test_imports.py::test_container_definition_is_inert  # run a single test
uv run ruff check .                  # lint
uv run ruff check --fix .            # lint with autofix
uv run pre-commit install            # one-time: install git hooks
uv run pre-commit install --hook-type commit-msg
uv run pre-commit run --all-files    # run all pre-commit checks (ruff, gitleaks, conventional-commit, etc.)
```

Always run the CLI via `uv run tgtg` (or the installed console script), not `python src/tgtg_cli/...` directly — running it as a loose script causes a `sys.path` shadowing issue since the package name is `tgtg_cli` but the module is nested under `cli/`.

CI (`.github/workflows/ci.yml`) runs ruff lint, pytest across Python 3.12/3.13/3.14 on Linux/macOS/Windows, commitlint, and a branch-name check on every PR.

## Commit / branch conventions

- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/) — `<type>(<optional-scope>): <subject>`. Enforced locally by the `commit-msg` pre-commit hook and in CI via commitlint.
- Branch names: `<type>/<short-kebab-description>` (e.g. `feat/multi-watch`, `fix/3ds-timeout`). Allowed types: `feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `revert`. Enforced by the `branch-name` CI job.
- Squash-merge is the only allowed merge style.
- `CHANGELOG.md` is maintained automatically by release-please from commit messages — never edit it by hand.
- Keep PRs small and focused on one change.

## Architecture

### Dependency injection

`src/tgtg_cli/container.py` defines a `dependency_injector` `Container` wiring together the app's singletons/factories: `Config` → `TGTG` (API client) → `AccountService` / `ProductService` (singletons) and `OrderService` (factory, new instance per checkout). Providers are lazy; `container.config()` and `container.tgtg()` must be explicitly resolved once at startup in `cli/app.py`, which is where `SettingsError`/`ConnectionError` from initial config/token validation are caught. Tests assert the container stays inert until resolved (`tests/test_imports.py`).

### CLI layer (`src/tgtg_cli/cli/`)

- `app.py` — Typer entry point (`main()`). Builds the `Container`, resolves `Config`/`TGTG`, then runs the interactive menu loop, dispatching to service methods based on the selected `MenuOptions`.
- `menu.py` — `MenuOptions` enum (each option knows whether it requires login) and the numbered-selection prompt UI (`show_menu_with_selection`, `show_selection`, including multi-select).
- `executor.py` — `run_safely()` wraps a service method call, catching `KeyboardInterrupt` and known exceptions (mapped via `ERROR_LABELS`) vs. unhandled ones (`Failure` enum: `KEYBOARD_INTERRUPT` / `KNOWN_ERROR` / `UNHANDLED`). `execute_selected_method()` combines `run_safely()` with `cleanup()`, which decides whether to exit, return to the menu, or prompt the user. This is the central place where new custom exceptions need an entry in `ERROR_LABELS` to get a friendly message.
- `config.py` — Pydantic models (`SettingsModel`, `SessionModel`, `DeviceModel`) plus the `Config` class that loads/creates/validates `settings.ini` (via `configparser`), the cached session (`session.json`), and a randomized device fingerprint (`device.json`) from OS-native config/cache dirs (`platformdirs`). Settings validation failures raise `SettingsError`, which is rendered as a per-field message list and reopens the settings file.
- `console.py` — Rich-based console helpers (colors, spinners, prompts) used everywhere instead of raw `print`.
- `types.py` — `TypedDict`s mirroring TGTG's JSON API responses (used for `.json()` return type hints on `apis/tgtg.py` methods).

### Services (`src/tgtg_cli/services/`)

Business logic layer, each service takes `Config` and `TGTG` in its constructor:

- `AccountService` — login/register/logout flows (email-code based), session persistence.
- `ProductService` — search filter configuration, item search/pagination, and the `monitor()` polling loop that checks item availability and hands off to `OrderService` when checkout is enabled.
- `OrderService` — the full checkout state machine: creates the order, encrypts card data, initiates payment via Adyen, and handles both 3DS2 (fingerprint/challenge/confirm flow, notifying the user via ntfy for manual confirmation steps) and legacy redirect 3DS1 authorization (in-browser challenge handled automatically for supported issuers, or via a webhook link for unsupported ones). Lazily builds `AccessControlServer`, `Adyen`, and `Cryptography` API clients via `cached_property` since they're only needed once checkout actually starts.

### API clients (`src/tgtg_cli/apis/`)

- `base.py` — `BaseClient`: shared `requests.Session` wrapper with retry logic (`_send`), optional request/response logging, and a `_handle_internal_errors` hook that subclasses override for site-specific error handling (called on every request before returning to the caller).
- `tgtg.py` — `TGTG(BaseClient)`, the main API client for `api.toogoodtogo.com`. Overrides `_handle_internal_errors` to: refresh expired JWTs and retry once (guarded by `quit_on_failed_retry` to avoid infinite loops), and handle Datadome captcha challenges (hardcoded delay retry → Datadome SDK cookie fetch → CapSolver solve, the latter only ever attempted on the login endpoint to avoid burning CapSolver credits during monitoring). Also scrapes the Play Store (with APK Mirror as fallback) to spoof the current app version in its `User-Agent`.
- `adyen.py` / `acs.py` / `cryptography.py` — Adyen payment API, the 3DS Access Control Server (per-issuer challenge submission, e.g. Bunq/DKB), and payload encryption/fingerprinting for the 3DS/checkout flow respectively.

### Utils (`src/tgtg_cli/utils/`)

Pydantic dataclasses/models (`models.py`) for internal state (`SessionTokens`, `CheckoutDetails`, `OrderDetails`, etc.), custom exceptions (`exceptions.py`), ntfy.sh notifications/webhooks with interactive actions (`notifications.py`), captcha solving via CapSolver (`captcha.py`), random Android device fingerprint generation (`devices.py`), file logging setup (`logging.py`), and card-encryption helpers (`encryption.py`).

### Error handling flow

Custom exceptions (`utils/exceptions.py`: `AuthorizationError`, `InvalidSession`, `RetryLimitReached`, `SettingsError`, `TooManyRequests`, `UnexpectedResponse`, `UnsupportedIssuer`) propagate up from the API/service layers and are caught centrally in `cli/executor.py`'s `run_safely()`/`render_exception()`, which maps them to user-facing console messages via `ERROR_LABELS`. Unrecognized exceptions fall through to a full traceback print plus an "open an issue on GitHub" notice.

## Local data locations

Settings live in `settings.ini` under the OS config dir (`platformdirs.user_config_dir`); session tokens, device fingerprint, and logs live under the OS cache dir (`platformdirs.user_cache_dir`). See README's Configuration/FAQ sections for exact paths and the full settings schema.

## Notes for making changes

- `page_size` in `TGTG.get_items`/`ProductService._get_items` must stay `20` — changing it causes missing/duplicate items in paginated search results (documented gotcha in the code).
- New known exceptions should be added to `ERROR_LABELS` in `cli/executor.py` so they render a friendly message instead of a raw traceback.
- CapSolver-based captcha solving must only be triggered on the login endpoint (`Endpoints.AUTH_BY_EMAIL`), never during monitoring, to avoid excessive solve costs.
- Ruff config enforces a 79-char line length; rule set is `E, F, UP, B, SIM, G, I` (see `pyproject.toml`).
