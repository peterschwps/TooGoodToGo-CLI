import importlib.metadata
import sys

from tgtg_cli.apis.tgtg import TGTG
from tgtg_cli.cli.config import Config


def test_package_metadata_available() -> None:
    """
    The package must be installed and its metadata queryable.
    """
    metadata = importlib.metadata.metadata("TGTG-CLI")

    assert metadata["Name"] == "TGTG-CLI"
    assert metadata["Version"]


def test_console_scripts_registered() -> None:
    """
    All console-script entry points must be registered.
    """
    entry_points = importlib.metadata.entry_points(
        group="console_scripts"
    )
    names = {ep.name for ep in entry_points}

    assert "tgtg" in names
    assert "tgtg-cli" in names
    assert "toogoodtogo" in names
    assert "toogoodtogo-cli" in names


def test_container_definition_is_inert(mocker) -> None:
    """
    Importing the dependency container must not eagerly instantiate
    Config or TGTG. Both providers must remain lazy until resolved
    explicitly via container.config() / container.tgtg().
    """
    config_init = mocker.patch.object(
        Config, "__init__", return_value=None
    )
    tgtg_init = mocker.patch.object(
        TGTG, "__init__", return_value=None
    )

    # Force a fresh import of the container module
    sys.modules.pop("tgtg_cli.container", None)
    from tgtg_cli.container import Container  # noqa: F401

    config_init.assert_not_called()
    tgtg_init.assert_not_called()
