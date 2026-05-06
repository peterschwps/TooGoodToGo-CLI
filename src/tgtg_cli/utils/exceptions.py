class AuthorizationError(Exception):
    pass


class InvalidSession(Exception):
    pass


class RetryLimitReached(Exception):
    pass


class SettingsError(Exception):
    pass


class TooManyRequests(Exception):
    def __init__(self):
        super().__init__(
            "Please try again later or use a proxy to change your IP address."
            "\nMake sure the retry delay you are using is high enough to "
            "prevent further rate limiting. This temporary block should be "
            "lifted after an hour."
        )


class UnexpectedResponse(Exception):
    pass


class UnsupportedIssuer(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Issuer is currently not supported. Please refer to the "
            "documentation for a list of supported providers. Open an issue "
            "on GitHub if you think that it is worth adding support for this "
            "issuer."
        )
