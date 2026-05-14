from tgtg_cli.cli.app import app
from tgtg_cli.utils.version import check_for_update


def main() -> None:
    """
    Entry point of the program.
    Runs the PyPI version check and starts the Typer app with the main loop.
    """
    check_for_update()
    app()


if __name__ == "__main__":
    main()
