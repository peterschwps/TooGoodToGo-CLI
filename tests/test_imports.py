import importlib.metadata


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

