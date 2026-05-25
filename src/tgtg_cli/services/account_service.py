import string

from rich import box
from rich.table import Table

from tgtg_cli.apis.tgtg import TGTG
from tgtg_cli.cli import console
from tgtg_cli.cli.config import Config
from tgtg_cli.utils.exceptions import AuthorizationError, InvalidSession
from tgtg_cli.utils.models import SessionTokens


class AccountService:
    def __init__(self, config: Config, tgtg: TGTG):
        self._config = config
        self._tgtg = tgtg

    def is_logged_in(self) -> bool:
        """
        Checks if the session tokens are set and valid. Sends a request to the
        onStartup endpoint to validate the current tokens.
        Clears the session file and exits the program if the session is
        invalid.

        Returns:
            bool: True if the user is logged in, else False.
        """
        if self._tgtg.tokens is None:
            return False
        else:
            try:
                self._tgtg.on_startup()
            except InvalidSession as error:
                self._config.generate_new_session_file()
                raise InvalidSession(
                    "Unable to log into the account."
                ) from error
            return self._tgtg.tokens is not None

    def logout(self):
        """
        Logs out the user by clearing the current session tokens and generating
        a new session file with empty default values.
        """
        self._config.generate_new_session_file()
        self._tgtg.tokens = None
        console.success("Successfully logged out!", show_time=False)

    def login(self, device_type: str = "ANDROID") -> None:
        """
        Logs in an existing user by email. Requests a verification code and
        prompts the user to enter it. Then submits the code and stores the
        session tokens in the session file.

        Args:
            device_type (str): Device type to use in the login request.
                               Defaults to "ANDROID".

        Raises:
            AuthorizationError: If an error occured during the login process.
        """
        email = self._config.settings.account.email
        login_response = self._tgtg.initiate_login(
            device_type=device_type, email=email
        )

        # Check if account is not registered yet
        if (
            "polling_id" not in login_response
            and login_response.get("state") == "TERMS"
        ):
            console.error("This email is not registered yet.")
            console.warning(
                "Please complete the registration first.",
                show_time=False,
            )
            return

        # Email verification code requested
        if "polling_id" in login_response:
            polling_id = login_response["polling_id"]

        # Unexpected response
        else:
            raise AuthorizationError(
                f"Failed to request an email verification code. "
                f"Response: {login_response}"
            )

        # Complete login
        self._complete_login(
            device_type=device_type,
            email=email,
            polling_id=polling_id,
        )

    def register(self, device_type: str = "ANDROID") -> None:
        """
        Registers a new user by email. Requests a verification code and prompts
        the user to enter it. Then submits the code and stores the session
        tokens in the session file.

        Args:
            device_type (str): Device type to use in the registration
                               request. Defaults to "ANDROID".

        Raises:
            AuthorizationError: If an error occured during the registration
                                process.
        """
        email = self._config.settings.account.email
        login_response = self._tgtg.initiate_login(
            device_type=device_type, email=email
        )

        # Check if account is already registered
        if (
            "polling_id" in login_response
            and login_response.get("state") == "WAIT"
        ):
            console.error("This email is already registered.")
            console.warning(
                "Please use the login option instead.",
                show_time=False,
            )
            return

        # Fetch supported countries from the onStartup endpoint and translate
        # the ISO codes to the corresponding country names
        countries = {
            "Australia": "AU",
            "Austria": "AT",
            "Belgium": "BE",
            "Canada": "CA",
            "Czechia": "CZ",
            "Denmark": "DK",
            "Germany": "DE",
            "Faroe Islands": "FO",
            "France": "FR",
            "Ireland": "IE",
            "Italy": "IT",
            "Japan": "JP",
            "Poland": "PL",
            "Portugal": "PT",
            "Netherlands": "NL",
            "New Zealand": "NZ",
            "Norway": "NO",
            "Spain": "ES",
            "Sweden": "SE",
            "Switzerland": "CH",
            "United Kingdom": "GB",
            "United States": "US",
        }

        # Print country table to console
        table = Table(box=box.DOUBLE_EDGE, show_lines=True)
        table.add_column("#", justify="center")
        table.add_column("Country", justify="left")
        for num, country in enumerate(countries, start=1):
            table.add_row(str(num), country)
        console.print(table)

        # Ask for country selection
        while True:
            selection = console.int_prompt.ask("\nSelect your country")
            if not (
                all(num in string.digits for num in str(selection))
                and selection in range(1, len(countries) + 1)
            ):
                console.error(
                    "\nInvalid selection. "
                    "Please enter a number from the table above."
                )
                continue
            else:
                country_iso_code = countries[list(countries)[selection - 1]]
                break

        # Finish registration
        register_response = self._tgtg.initialize_registration(
            device_type=device_type,
            email=email,
            country_id=country_iso_code,
        )

        # Complete login
        self._complete_login(
            device_type=device_type,
            email=email,
            polling_id=register_response["polling_id"],
        )

    def _complete_login(
        self,
        device_type: str,
        email: str,
        polling_id: str,
    ) -> None:
        """
        Completes the login to create an active session. Stores the session
        tokens in the session file. This method can either be called after
        logging in an existing user or after registering a new user.

        Args:
            device_type (str): Device type to use in the login request.
            email (str): Email of the user to log in.
            polling_id (str): Polling ID of the initiated login or registration
                              process.

        Raises:
            AuthorizationError: If the session tokens could not be retrieved
                                from the response.
            AuthorizationError: If the submission of the email verification
                                code was not successful.
        """
        # Prompt for user input
        email_verification_code = console.prompt.ask(
            "Enter the email verification code"
        )

        # Check for missing fields
        while len(email_verification_code) != 6 or not all(
            num in string.digits for num in email_verification_code
        ):
            console.error(
                "Invalid email verification code. "
                "Make sure to enter a 6-digit code.\n"
            )
            email_verification_code = console.prompt.ask(
                "Enter the email verification code"
            )

        # Submit email verification code
        login_response = self._tgtg.complete_login(
            device_type=device_type,
            email=email,
            code=email_verification_code,
            polling_id=polling_id,
        )

        # Login process completed
        if "access_token" in login_response:
            self._tgtg.tokens = SessionTokens.from_api(login_response)
            if self._tgtg.tokens:
                self._config.save_session(self._tgtg.tokens)
                console.clear()
                console.success("Successfully logged in!", show_time=False)
            else:
                raise AuthorizationError(
                    "Failed to save session tokens to cache."
                )

        # Errors, e.g. wrong email / polling ID / verification code
        else:
            raise AuthorizationError(
                f"Failed to submit email verification code. "
                f"Response: {login_response}"
            )
