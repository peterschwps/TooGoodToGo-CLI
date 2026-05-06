from datetime import datetime

import rich.default_styles
from rich.style import Style

# This has to be configured before importing the console
rich.default_styles.DEFAULT_STYLES["prompt"] = Style(
    color="white",
)
rich.default_styles.DEFAULT_STYLES["prompt.choices"] = Style(
    color="blue",
    bold=True,
)

from rich.console import Console  # noqa: E402
from rich.live import Live  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.prompt import Confirm, IntPrompt, Prompt  # noqa: E402
from rich.status import Status  # noqa: E402
from rich.style import StyleType  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402


class CustomizedPrompt(Prompt):

    def __init__(self, *args, console: "CustomizedConsole", **kwargs):
        super().__init__(*args, console=console, **kwargs)
        self.console: CustomizedConsole  # only for the type checker 

    # Override error message
    def on_validate_error(self, value: str, *args, **kwargs):
        """
        Renders a custom validation error message for invalid prompt inputs.

        Args:
            value (str): Value entered by the user.
        """
        self.console.print("\nPlease enter a valid value.", style="bold red")

    # Extend ask() method
    def ask(self, *args, **kwargs) -> str:
        """
        Sets an additional flag to signal that the console is currently waiting
        for input from the user.
        """
        self.console._awaiting_input = True
        result = super().ask(*args, **kwargs)
        self.console._awaiting_input = False
        return result


class CustomizedIntPrompt(IntPrompt):

    def __init__(self, *args, console: "CustomizedConsole", **kwargs):
        super().__init__(*args, console=console, **kwargs)
        self.console: CustomizedConsole  # only for the type checker     

    # Override error message
    def on_validate_error(self, value: str, *args, **kwargs):
        """
        Renders a custom validation error message for invalid integer inputs.

        Args:
            value (str): Value entered by the user.
        """
        self.console.print("\nPlease enter a valid number.", style="bold red")

    # Extend ask() method
    def ask(self, *args, **kwargs) -> int:
        """
        Sets an additional flag to signal that the console is currently waiting
        for input from the user.
        """
        self.console._awaiting_input = True
        result = super().ask(*args, **kwargs)
        self.console._awaiting_input = False
        return result


class CustomizedConfirmPrompt(Confirm):

    def __init__(self, *args, console: "CustomizedConsole", **kwargs):
        super().__init__(*args, console=console, **kwargs)
        self.console: CustomizedConsole  # only for the type checker 

    # Override error message
    def on_validate_error(self, value: str, *args, **kwargs):
        """
        Renders a custom validation error message for invalid confirm inputs.

        Args:
            value (str): Value entered by the user.
        """
        self.console.print(
            "\nPlease enter only 'y' or 'n'.\n",
            style="bold red",
            highlight=False,
        )

    # Extend ask() method
    def ask(self, *args, **kwargs) -> bool:
        """
        Sets an additional flag to signal that the console is currently waiting
        for input from the user.
        """
        self.console._awaiting_input = True
        result = super().ask(*args, **kwargs)
        self.console._awaiting_input = False
        return result


class CustomizedRenderable:
    """
    CustomizedRenderable to use in Rich's Live display.
    """

    def __init__(self, text: str, add_ellipsis: bool = True, show_time = True):
        """
        Initializes the CustomizedRenderable class.

        Args:
            text (str): Text that should be displayed in the console. A prefix
                        which shows the current time is added automatically.
            add_ellipsis (bool, optional): If an ellipsis (three dots) should
                                           be added to the end of the message.
                                           This will automatically remove
                                           trailing dots and replace them.
                                           Defaults to True.
            show_time (bool, optional): If a timestamp should be added as a
                                        prefix to the message.
                                        Defaults to True.
        """
        self.text = text
        self._add_ellipsis = add_ellipsis
        self._show_time = show_time
        self._frame = 0

        # Remove trailing ellipsis if it should be automatically added
        if self._add_ellipsis and self.text.endswith("..."):
            self.text = self.text.rstrip(".")

    def __rich__(self) -> Text:
        """
        Renders the console output. Adds a prefix which shows the current time.
        Adds a suffix which displays a varying ellipsis (. / .. / ...).

        Returns:
            Text: Fully rendered console output with prefix and suffix.
        """
        dots = None
        if self._add_ellipsis:
            dots = "." * (self._frame % 3 + 1)
            self._frame += 1
        prefix = f"{self._get_current_time()} - " if self._show_time else ""
        return Text(
            f"{prefix}{self.text}{dots if dots else ''}",
            style="white",
        )
    
    def _get_current_time(self) -> str:
        """
        Returns the current local time formatted for console output.

        Returns:
            str: Current timestamp in YYYY-MM-DD HH:MM:SS format.
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class CustomizedLive(Live):

    def __init__(
            self,
            renderable: CustomizedRenderable,
            *,
            add_ellipsis: bool = True,
            transient: bool = False,
            **kwargs,
        ):
        """
        Initializes the CustomizedLive class which inherits from Rich's Live
        class.

        Args:
            renderable (CustomizedRenderable): Text that should be displayed in
                                               the console.
            add_ellipsis (bool, optional): If an ellipsis (three dots) should
                                           be added to the end of the message.
                                           Defaults to True.
            transient (bool, optional): If the message should disappear after
                                        exiting the Live display.
                                        Defaults to False.
        """
        self.add_ellipsis = add_ellipsis
        super().__init__(renderable=renderable, transient=transient, **kwargs)

    def stop(self) -> None:
        """
        Overrides the default stop() method of Rich's Live class.
        Adds an option to ensure the latest rendered message in the console has
        an ellipsis (...). This behavior can be enabled by default through the
        add_ellipsis=True parameter when instantiating the class.
        """
        if self.add_ellipsis and not self.transient:
            renderable = self.get_renderable()
            if isinstance(renderable, CustomizedRenderable):
                renderable._frame = 2
                self.update(renderable)
        super().stop()


class CustomizedStatus(Status):

    def __init__(self, *args, **kwargs):
        """
        Initializes the CustomizedStatus class which inherits from Rich's
        Status class.
        Overrides Rich's hardcoded transient=True behavior so the last rendered
        frame remains in the terminal scrollback after stopping the animation.
        """
        super().__init__(*args, **kwargs)
        self._live.transient = False

    def stop(self) -> None:
        """
        Overrides the default stop() method of Rich's Status class.
        Removes the spinner from the last rendered message in the console
        before stopping the animation.
        """
        self._live.update(self._spinner.text)
        super().stop()


class CustomizedConsole(Console):
    
    def __init__(self):
        super().__init__(highlight=False)
        self.prompt = CustomizedPrompt(console=self, show_choices=False)
        self.int_prompt = CustomizedIntPrompt(console=self, show_choices=False)
        self.confirm_prompt = CustomizedConfirmPrompt(console=self)
        self._awaiting_input = False

    def _get_current_time(self) -> str:
        """
        Returns the current local time formatted for console output.

        Returns:
            str: Current timestamp in YYYY-MM-DD HH:MM:SS format.
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _add_timestamp(self, message: str):
        """
        Prefixes a message with the current timestamp.

        Args:
            message (str): Message to add the timestamp to.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} - {message}"
        return message
    
    def _print(self, message: str, show_time: bool = True, **kwargs):
        """
        Adds an option to prefix a message with a timestamp when calling the
        print() method of Rich's console class.

        Args:
            message (str): Message to display in the console.
            show_time (bool, optional): If a timestamp should be added as a 
                                        prefix. This only works on string 
                                        messages!
                                        Defaults to True.
        """
        if show_time:
                message = self._add_timestamp(message=message)
        super().print(message, **kwargs)

    def clear(self, home: bool = True) -> None:
        """
        Clears the screen. Adds a visual separator for the previous page if the
        terminal supports scrollback.

        Args:
            home (bool, optional): If the cursor should move to the top-left
                                   of the cleared viewport. Defaults to True.
        """
        if self.is_terminal and not self.is_dumb_terminal:
            # Add empty line if console is awaiting input to prevent the
            # separator from being printed directly after the prompt
            if self._awaiting_input:
                self.blank()
            self.print(f"{' previous page ':-^{self.width}}", style="dim")
        super().clear(home=home)

    def waiting(
            self,
            status: str,
            refresh_per_second: float = 4,
            transient: bool = False,
            add_ellipsis: bool = True,
            show_time: bool = True,
        ) -> CustomizedLive:
        """
        Creates a CustomizedLive (inherits from Rich's Live display) which
        refreshes the status text displayed in the console. 

        Args:
            status (str): Text to show in the console.
            refresh_per_second (float, optional): Amount of refreshes per
                                                  second.
                                                  Defaults to 4.
            transient (bool, optional): If the message should disappear after
                                        exiting the Live display.
                                        Defaults to False.
            add_ellipsis (bool, optional): If an ellipsis (three dots) should
                                           be added to the end of the message.
                                           Defaults to True.
            show_time (bool, optional): If a timestamp should be added as a
                                        prefix to the message.
                                        Defaults to True.

        Returns:
            CustomizedLive: Instance of the CustomizedLive class (which 
                            inherits from Rich's Live class) and can be used
                            with a context manager. 
        """
        renderable = CustomizedRenderable(
            text=status,
            add_ellipsis=add_ellipsis,
            show_time=show_time,
        )
        return CustomizedLive(
            renderable=renderable,
            console=self,
            refresh_per_second=refresh_per_second,
            add_ellipsis=add_ellipsis,
            transient=transient,
        ) 
    
    def loading(
        self,
        status: str,
        spinner: str = "dots",
        spinner_style: StyleType = "white",
        speed: float = 1.0,
        refresh_per_second: float = 12.5,
    ) -> CustomizedStatus:
        """
        Implements Rich's status() method of the console class. Adds a white
        spinner as a prefix to the message and changes its text to white.
        Otherwise the text would be displayed slightly gray, when using the
        Live display.

        Args:
            status (str): Message to display in the console.
            spinner (str, optional): Name of spinner animation (see python -m 
                                     rich.spinner). Defaults to "dots".
            spinner_style (StyleType, optional): Style of spinner.
                                                 Defaults to "white".
            speed (float, optional): Speed factor for spinner animation.
                                     Defaults to 1.0.
            refresh_per_second (float, optional): Number of refreshes per
                                                  second. Defaults to 12.5.

        Returns:
            CustomizedStatus: CustomizedStatus object that sets transient=False
                              so the last rendered frame remains in the
                              terminal scrollback after stopping the animation.
                              This object can also be used as a context
                              manager.
        """
        text = Text(text=status, style="white")
        return CustomizedStatus(
            text,
            console=self,
            spinner=spinner,
            spinner_style=spinner_style,
            speed=speed,
            refresh_per_second=refresh_per_second,
        )

    def blank(self):
        """
        Prints a blank line to the console.
        """
        self.print("")
    
    def info(
            self,
            message: str | Panel | Table,
            show_time: bool = True,
        ) -> None:
        """
        Prints white text to the console.

        Args:
            message (str | Panel | Table): Element to print to console.
            show_time (bool, optional): If a timestamp should be added as a 
                                        prefix. This only works on string 
                                        messages!
                                        Defaults to True.
        """
        if isinstance(message, Panel | Table):
            self.print(message)
        else:
            self._print(message, show_time=show_time, style="white")

    def success(self, message: str, show_time: bool = True) -> None:
        """
        Prints green text to the console.

        Args:
            message (str): Message to print to console.
            show_time (bool, optional): If a timestamp should be added as a 
                                        prefix.
                                        Defaults to True.
        """
        self._print(message, show_time=show_time, style="green")

    def warning(self, message: str, show_time: bool = False) -> None:
        """
        Prints yellow text to the console.

        Args:
            message (str): Message to print to console.
            show_time (bool, optional): If a timestamp should be added as a 
                                        prefix.
                                        Defaults to False.
        """
        self._print(message, show_time=show_time, style="yellow")

    def error(self, message: str, show_time: bool = False) -> None:
        """
        Prints red text to the console.
        show_time (bool, optional): If a timestamp should be added as a 
                                        prefix.
                                        Defaults to False.

        Args:
            message (str): Message to print to console.
        """
        self._print(message, show_time=show_time, style="red")

    def critical(self, message: str) -> None:
        """
        Prints bold red text to the console.

        Args:
            message (str): Message to print to console.
        """
        self.print(message, style="bold red")
