import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import typer
from typer import rich_utils

from tgtg_cli import config, console
from tgtg_cli.cli.executor import (
    Failure,
    execute_selected_method,
    run_safely,
)
from tgtg_cli.cli.menu import MenuOptions, show_menu_with_selection
from tgtg_cli.services.account_service import AccountService
from tgtg_cli.services.product_service import ProductService
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
    flags/options. Runs the main loop with the interactive menu.

    Args:
        _ (Annotated[bool, typer.Option, optional): Additional --version option
                                                    for the application.
    """
    console.clear()
    while True:
        # Check if user is logged in to display corresponding menu options)
        result = run_safely(AccountService.is_logged_in)
        if isinstance(result, Failure):
            sys.exit(0 if result is Failure.KEYBOARD_INTERRUPT else 1)

        # Load menu and prompt user for action
        method_to_run = show_menu_with_selection(user_logged_in=result)

        # Call selected method
        match method_to_run:
            case MenuOptions.Exit:
                sys.exit(0)

            case MenuOptions.Login:
                execute_selected_method(AccountService.login)

            case MenuOptions.Logout:
                execute_selected_method(AccountService.logout)

            case MenuOptions.Monitor:
                execute_selected_method(ProductService.monitor)

            case MenuOptions.Settings:
                execute_selected_method(
                    config.open_settings_file,
                    exit_afterwards=True,
                )
