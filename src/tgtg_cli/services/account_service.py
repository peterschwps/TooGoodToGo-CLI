import string

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
        Clears the session file and resets the tokens if the session is
        invalid.

        Returns:
            bool: True if the user is logged in, else False.
        """
        if self._tgtg.tokens is None:
            return False
        else:
            try:
                startup_response_code = self._tgtg.on_startup()
            except InvalidSession as error:
                self._config.generate_new_session_file()
                raise InvalidSession(
                    "Unable to log into the account."
                ) from error

            if startup_response_code != 200:
                console.warning("Session invalid.")
                self._config.generate_new_session_file()
                self._tgtg.tokens = None
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
            device_type=device_type,
            email=email
        )

        # Email verification code requested
        if "polling_id" in login_response:
            polling_id = login_response["polling_id"]

        # Unexpected response
        else:
            raise AuthorizationError(
                f"Failed to request an email verification code. "
                f"Response: {login_response}"
            )

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
            polling_id=polling_id
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
