import importlib.metadata


def test_package_metadata_available() -> None:
    """
    The package must be installed and its metadata queryable.
    """
    metadata = importlib.metadata.metadata("TGTG-CLI")

    assert metadata["Name"] == "TGTG-CLI"
    assert metadata["Version"]


def test_console_script_registered() -> None:
    """
    The `tgtg-cli` console-script entry point must be registered.
    """
    entry_points = importlib.metadata.entry_points(
        group="console_scripts"
    )

    assert any(ep.name == "tgtg-cli" for ep in entry_points)
