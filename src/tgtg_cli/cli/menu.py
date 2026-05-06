import string
from collections.abc import Iterable
from enum import Enum
from typing import cast

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from tgtg_cli.cli import console


class MenuOptions(Enum):
    #  Register = ("Register", False)
    Login = ("Login", False)
    Monitor = ("Monitor", True)
    Logout = ("Logout", True)
    Settings = ("Settings", None)
    Exit = ("Exit", None)

    def __init__(self, label: str, requires_login: bool | None):
        """
        Unpacks the tuple values of the Enum members into descriptive
        attributes for better readability.

        Args:
            label (str): Description of the menu option.
            requires_login (bool | None): If the menu option requires the user
                                          to be logged in to be visible.
                                          If None, the option is visible
                                          regardless of the login state.
        """
        self.label = label
        self.requires_login = requires_login

    def is_visible(self, user_logged_in: bool) -> bool:
        """
        Checks if the menu option is visible for the given login state.

        Args:
            user_logged_in (bool): True if the user is currently logged in.

        Returns:
            bool: True if the option should be shown in the menu, otherwise
                  False.
        """
        return (
            self.requires_login is None
            or self.requires_login == user_logged_in
        )


def show_menu_with_selection(user_logged_in: bool) -> MenuOptions:
    """
    Creates the header and main menu after starting the application. Prompts
    the user to make a selection.

    Args:
        user_logged_in (bool): If the user is logged in. This value is used to
                               determine which menu options to show.

    Returns:
        MenuOptions: Menu option selected by the user.
    """
    console.info(
        message=Panel(
            Group(
                Text(text="TooGoodToGo", style="bold", justify="center"),
                Text.from_markup(
                    text=(
                        "by [link=https://github.com/peterschwps]@peterschwps"
                        "[/link]"
                    ),
                    style="bright_black",
                    justify="center"
                ),
            )
        ),
        show_time=False,
    )
    console.blank()
    menu = tuple(
        option for option in MenuOptions if option.is_visible(user_logged_in)
    )
    selection = show_selection(menu)
    return menu[cast(int, selection)]

def show_selection(
        options: Iterable[Enum | str],
        multi_selection: bool = False,
    ) -> int | list[int]:
    """
    Creates a menu and prompts the user to make a selection.

    Args:
        options (Iterable[Enum | str]): Options to show in the menu.
        multi_selection (bool, optional): If the user can select multiple 
                                          options. Defaults to False.

    Returns:
        int | list[int]: Selection made by the user. Value is a single integer 
                         if multi_selection is False or a list of integers if
                         multi_selection is True.
                         The integers represent the index of the selected
                         option(s) in the options parameter.
    """
    # Validate choice (digits only and in available range)
    def is_valid_choice(choice: int) -> bool:
        return bool(
            all(
                num in string.digits for num in str(choice))
                and choice in range(1, len(list(options)) + 1)
            )

    # Load prompt until valid choice is entered
    while True:
        for num, option in enumerate(options, start=1):
            label = (
                getattr(option, "label", option.value)
                if isinstance(option, Enum) else option
            )
            console.info(f"{num}. {label}", show_time=False)

        # Handle multi-selection
        if multi_selection:
            choices = console.prompt.ask(
                "\nEnter your choices (separated by plus sign, e.g.: 1+3+4)"
            )
            choices_list = choices.split("+")
            invalid_choice = False
            for choice in choices_list:
                if (
                    not choice.strip().isdigit()
                    or not is_valid_choice(int(choice.strip()))
                ):
                    invalid_choice = True
                    console.error(
                        f"\nInvalid choice: '{choice}'. "
                        f"Please only enter numbers from the list below.\n"
                    )
                    break

            if invalid_choice:
                continue

            console.clear()
            return [int(choice.strip())-1 for choice in choices_list]

        # Handle single selection
        else:
            choice = console.int_prompt.ask("\nEnter your choice")
            if is_valid_choice(choice):
                console.clear()
                return choice-1
            else:
                console.error(
                    "\nInvalid choice. "
                    "Please enter a number from the list below.\n"
                )
