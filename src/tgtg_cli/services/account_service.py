import string

from tgtg_cli import config, tgtg
from tgtg_cli.cli import console
from tgtg_cli.utils.exceptions import AuthorizationError, InvalidSession
from tgtg_cli.utils.models import SessionTokens


class AccountService:
    """
    Grouping of all account-related functions.
    """

    @staticmethod
    def is_logged_in() -> bool:
        """
        Checks if the session tokens are set and valid. Sends a request to the
        onStartup endpoint to validate the current tokens.
        Clears the session file and resets the tokens if the session is
        invalid.

        Returns:
            bool: True if the user is logged in, else False.
        """
        if tgtg.tokens is None:
            return False
        else:
            try:
                startup_response_code = tgtg.on_startup()
            except InvalidSession as error:
                config.generate_new_session_file()
                raise InvalidSession(
                    "Unable to log into the account."
                ) from error

            if startup_response_code != 200:
                console.warning("Session invalid.")
                config.generate_new_session_file()
                tgtg.tokens = None
            return tgtg.tokens is not None

    @staticmethod
    def logout():
        """
        Logs out the user by clearing the current session tokens and generating
        a new session file with empty default values.
        """
        config.generate_new_session_file()
        tgtg.tokens = None
        console.success("Successfully logged out!", show_time=False)

    @staticmethod
    def login(device_type: str = "ANDROID") -> None:
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
        email = config.settings.account.email
        login_response = tgtg.initiate_login(
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
        login_response = tgtg.complete_login(
            device_type=device_type,
            email=email,
            code=email_verification_code,
            polling_id=polling_id
        )

        # Login process completed
        if "access_token" in login_response:
            tgtg.tokens = SessionTokens.from_api(login_response)
            if tgtg.tokens:
                config.save_session(tgtg.tokens)
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
