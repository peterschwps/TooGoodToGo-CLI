import sys

from tgtg_cli import config
from tgtg_cli.cli.executor import Failure, execute_selected_method, run_safely
from tgtg_cli.cli.menu import (
    MenuOptions,
    show_menu_with_selection,
)
from tgtg_cli.services.account_service import AccountService
from tgtg_cli.services.product_service import ProductService
from tgtg_cli.utils.version import check_for_update


def main():
    """
    Runs the main loop and starts the selected menu options. Checks if a newer
    version is available before starting the loop.
    """
    check_for_update()
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


if __name__ == "__main__":
    main()

# TODOs:
# TODO: in Docs vermerken --> dass Tools wie z.B. CleanMyMac den Cache und
#       damit auch die Login Session löschen
# TODO: nochmal Rich Optionen für Console und Live Display angucken, ist immer
#       random, wann man welche der letzten Konsoleausgaben sieht und sieht
#       nicht sauber aus
# TODO: noch bestes Delay für Monitoren rausfinden
# TODO: base.py auslagern oder als Protokoll?
