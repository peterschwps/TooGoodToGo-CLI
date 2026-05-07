import sys
from collections.abc import Callable
from enum import Enum, auto
from time import sleep

from capsolver.error import CapsolverError

from tgtg_cli.cli import console
from tgtg_cli.utils.exceptions import (
    AuthorizationError,
    InvalidSession,
    RetryLimitReached,
    TooManyRequests,
    UnexpectedResponse,
    UnsupportedIssuer,
)


class Failure(Enum):
    """
    Possible outcomes when a method execution with run_safely() fails.
    """
    KEYBOARD_INTERRUPT = auto()
    KNOWN_ERROR = auto()
    UNHANDLED = auto()


type Result[Value] = Value | Failure


# Labels of know exceptions to display in the console
ERROR_LABELS: dict[type[Exception], str] = {
    AuthorizationError: "Authorization error",
    InvalidSession: "Invalid session",
    RetryLimitReached: "Retry limit reached",
    TooManyRequests: "Too many requests",
    UnexpectedResponse: "Unexpected response",
    UnsupportedIssuer: "Unsupported provider"
}


def render_exception(error: Exception) -> bool:
    """
    Displays an exception specific message in the console if the exception is
    recognized. Otherwise, returns False.

    Args:
        error (Exception): Exception to handle.

    Returns:
        bool: True if the exception was recognized, otherwise False.
    """
    # Handle custom exceptions
    for exception_type, label in ERROR_LABELS.items():
        if isinstance(error, exception_type):
            console.error(f"{label}: {str(error).rstrip('.')}.")
            if isinstance(error, InvalidSession):
                console.warning(
                    "Session has been reset. Please restart the application "
                    "and log in again.",
                    show_time=False,
                )
            return True

    # Handle CapSolver exceptions
    if isinstance(error, CapsolverError):
        message = (
            f"{error._message}" if hasattr(error, "_message") else str(error)
        )
        message = message.rstrip(".")
        message = message[0].upper() + message[1:]
        console.error(f"CapSolver error: {message}.")
        console.warning(
            "Please check your solver settings and make sure you have enough "
            "balance on your CapSolver account.",
            show_time=False,
        )
        return True
    return False


def run_safely[Value](method: Callable[[], Value]) -> Result[Value]:
    """
    Executes a method and renders any raised exception with render_exception().
    Adds an additional notice for unhandled exceptions.

    Args:
        method (Callable[[], Value]): Method to execute.

    Returns:
        Result[Value]: The return value of the method if it ran successfully,
                       otherwise one of the Failure variants.
    """
    try:
        return method()
    except KeyboardInterrupt:
        return Failure.KEYBOARD_INTERRUPT
    except Exception as e:
        console.clear()
        if render_exception(e):
            return Failure.KNOWN_ERROR
        else:
            console.error("\n[b]An unhandled exception occurred:[b]\n")
            console.print_exception()
            return Failure.UNHANDLED


def cleanup(result: Result, exit_afterwards: bool) -> None:
    """
    Handles the cleanup after executing a method. Prints follow-up messages,
    prompts the user to return to the menu or exits the program.

    Args:
        result (Result): Result of the executed method.
        exit_afterwards (bool): If the program should exit after executing
                                the method. Otherwise the user will be asked
                                if the program should return to the menu.
    """
    # Print to console depending on outcome of method execution
    if result is Failure.UNHANDLED:
        console.warning(
            "\nPlease open an issue on GitHub if this is issue persists."
        )
        sys.exit(1)
    elif result is Failure.KNOWN_ERROR:
        console.warning(
            "\nRefer to the documentation for more information."
            "\nIf you think this is a bug, please open an issue on GitHub."
        )

    # Prompt user to return to menu if an exit after function execution
    # is not enabled
    if not exit_afterwards:
        if result is Failure.KEYBOARD_INTERRUPT:
            console.clear()
        else:
            console.blank()
        return_to_menu = console.confirm_prompt.ask("Return to menu")
        if not return_to_menu:
            sys.exit(0)
        else:
            console.clear()
    else:
        console.blank()
        with console.waiting("Exiting...", show_time=False):
            sleep(1)
        sys.exit(0)


def execute_selected_method(
    method: Callable[[], None],
    exit_afterwards: bool = False,
) -> None:
    """
    Main method to execute any method that the user selected and handle all
    errors that occur during the execution at top level.

    Args:
        method (Callable[[], None]): Method to execute.
        exit_afterwards (bool, optional): If the program should exit after
                                          executing the method. Otherwise the
                                          user will be asked if the program
                                          should return to the menu. Defaults
                                          to False.
    """
    result = run_safely(method)
    cleanup(result, exit_afterwards)
