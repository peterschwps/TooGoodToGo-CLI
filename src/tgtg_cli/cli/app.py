import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import typer
from requests.exceptions import ConnectionError
from typer import rich_utils

from tgtg_cli.cli import console
from tgtg_cli.cli.config import Config
from tgtg_cli.cli.executor import (
    Failure,
    execute_selected_method,
    run_safely,
)
from tgtg_cli.cli.menu import MenuOptions, show_menu_with_selection
from tgtg_cli.container import Container
from tgtg_cli.utils.exceptions import SettingsError
from tgtg_cli.utils.version import PACKAGE_NAME

# Configure styles for help output
rich_utils.STYLE_OPTION = "bold"
rich_utils.STYLE_SWITCH = "bold"
rich_utils.STYLE_USAGE = "bold"
rich_utils.STYLE_USAGE_COMMAND = "bold"
rich_utils.STYLE_HELPTEXT_FIRST_LINE = "bold blue"
rich_utils.STYLE_OPTIONS_PANEL_BORDER = "dim"

# Create Typer app
app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version_callback(value: bool) -> None:
    """
    Prints the installed package version and exits when --version is
    passed. Displays an error message if the version could not be retrieved.

    Reference: https://typer.tiangolo.com/tutorial/options/version/.

    Args:
        value (bool): True if the --version flag was passed.

    Raises:
        typer.Exit: Exits the program after displaying the version or error
                    message. Default way to exit a Typer application.
    """
    if not value:
        return
    try:
        console.info(
            f"\nInstalled version: {version(PACKAGE_NAME)}",
            show_time=False,
        )
    except PackageNotFoundError:
        console.error("Unable to fetch current version.")
    finally:
        raise typer.Exit()


@app.command(
    help=(
        "Unofficial CLI for 'Too Good To Go' to monitor and check out items "
        "as they become available."
    ),
)
def main(
    _: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show the installed version and exit.",
        ),
    ] = False,
) -> None:
    """
    Entry callback that runs if the application is called without any
    flags/options. Builds the dependency-injector container and triggers the
    initialization of the Config class and the TGTG which raise Errors if the
    configuration isn't working.
    Runs the main loop with the interactive menu.

    Args:
        _ (bool, optional): Additional --version option for the application.
                            Handled by version_callback before the body of this
                            function runs.
    """
    console.clear()

    # Build container and initialize Config and TGTG singletons
    # Both providers are lazy and need to be resolved here
    # Initializing the Config class checks the user's settings file for errors
    # and loads all required variables for the application
    container = Container()
    try:
        container.config()
        container.tgtg()

    except SettingsError as e:
        console.clear()
        console.error(f"Settings error: {e}")
        console.blank()
        Config.open_settings_file()
        sys.exit(1)

    except ConnectionError:
        console.clear()
        console.error(
            "Failed to establish a connection. "
            "Make sure you are connected to the internet."
        )
        sys.exit(1)

    # Resolve services
    account_service = container.account_service()
    product_service = container.product_service()

    # Start main loop
    while True:

        # Check if user is logged in to display corresponding menu options)
        result = run_safely(account_service.is_logged_in)
        if isinstance(result, Failure):
            sys.exit(0 if result is Failure.KEYBOARD_INTERRUPT else 1)

        # Load menu and prompt user for action
        method_to_run = show_menu_with_selection(user_logged_in=result)

        # Call selected method
        match method_to_run:
            case MenuOptions.Exit:
                sys.exit(0)

            case MenuOptions.Login:
                execute_selected_method(account_service.login)

            case MenuOptions.Logout:
                execute_selected_method(account_service.logout)

            case MenuOptions.Monitor:
                execute_selected_method(product_service.monitor)

            case MenuOptions.Settings:
                execute_selected_method(
                    Config.open_settings_file,
                    exit_afterwards=True,
                )
