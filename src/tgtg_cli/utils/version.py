import json
from datetime import datetime, timedelta
from importlib.metadata import PackageNotFoundError, version
from time import sleep

import requests
from packaging.version import InvalidVersion, parse
from pydantic import BaseModel, ValidationError
from requests.exceptions import ConnectionError, Timeout

from tgtg_cli.cli import console
from tgtg_cli.cli.config import CACHE_DIR

PACKAGE_NAME = "TGTG-CLI"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
VERSION_CHECK_FILE_PATH = CACHE_DIR / "version.json"


class VersionCheckModel(BaseModel):
    last_check: datetime
    latest_version: str


def check_for_update() -> None:
    """
    Checks PyPI for a newer version of the package and prints a warning
    if an update is available. Caches the result for 24 hours. Fails silently
    on network or parsing errors.

    Note: Any errors that could likely occur during the version check but would
          not affect the application are supposed to fail silently. This is
          done to prevent unneccessary crashes while starting.
    """
    # Load version of current installation
    try:
        current = version(PACKAGE_NAME)
    except PackageNotFoundError:
        return

    # Fetch latest version from PyPI
    latest = _get_latest_version()
    if latest is None:
        return

    # Compare version and print notice if newer version available
    try:
        if parse(latest) > parse(current):
            console.clear()
            console.warning(
                f"New version available: {current} → {latest}.\n"
                f"Run 'pip install --upgrade {PACKAGE_NAME}' to update."
            )
            sleep(3)
    except InvalidVersion:
        return


def _get_latest_version() -> str | None:
    """
    Returns the latest package version from cache (if still fresh) or PyPI.
    If requesting the version from PyPI fails but an old cache is still present
    it will be used.

    Returns:
        str | None: Latest version string, or None if unavailable.
    """
    # Check if cache still valid
    cached = _load_cache()
    if cached and datetime.now() - cached.last_check < timedelta(hours=24):
        return cached.latest_version

    # Otherwise request latest version from PyPI
    try:
        response = requests.get(url=PYPI_URL, timeout=3)
        latest = response.json()["info"]["version"]
    except (ConnectionError, KeyError, Timeout, ValueError):
        return cached.latest_version if cached else None

    # Save result
    _save_cache(latest)
    return latest


def _load_cache() -> VersionCheckModel | None:
    """
    Loads the version from the cached file. Returns None if the file does not
    exist or can't be read (e.g. due to being corrupt).

    Returns:
        VersionCheckModel | None: Cached version data or None.
    """
    if not VERSION_CHECK_FILE_PATH.exists():
        return
    try:
        with open(VERSION_CHECK_FILE_PATH) as f:
            return VersionCheckModel.model_validate(json.load(f))
    except (json.JSONDecodeError, ValidationError, OSError):
        return


def _save_cache(latest_version: str) -> None:
    """
    Writes the latest version and current timestamp to the cache file. Fails
    silently on write errors.

    Args:
        latest_version (str): Latest version string to cache.
    """
    model = VersionCheckModel(
        last_check=datetime.now(),
        latest_version=latest_version,
    )
    try:
        with open(VERSION_CHECK_FILE_PATH, "w") as f:
            json.dump(model.model_dump(mode="json"), f, indent=4)
    except OSError:
        pass
