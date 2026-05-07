from typing import Literal

from tgtg_cli.apis.base import BaseClient
from tgtg_cli.cli.config import Config
from tgtg_cli.utils.models import ThreeDS2Status

URL: str = "https://peterschwps.com/api/tgtg"

Status = Literal[
    "completed",
    "awaiting_confirmation",
    "awaiting_selection",
]

class Endpoints:
    ENCRYPTOR = URL + "/encryptor"
    FINGERPRINT = URL + "/fingerprint"
    THREE_DS_CHALLENGE = URL + "/3ds"


class Cryptography(BaseClient):

    def __init__(self, config: Config):
        super().__init__(
            config=config,
            headers={"Accept": "*/*"},
        )

    def get_encryptor(self) -> tuple[str, str]:
        """
        Retrieves an unique AES key and initialization vector for encrypting
        the card details before submitting them to Adyen's /binLookup endpoint
        and TooGoodToGo's /pay endpoint.

        Returns:
            tuple[str, str]: AES key and initialization vector encoded as a
                             url-safe base64 string.
        """
        response = self._get(url=Endpoints.ENCRYPTOR)
        payload = response.json()
        aes_key = payload["aesKey"]
        iv = payload["initializationVector"]
        return aes_key, iv


    def get_fingerprint(self, token: str) -> str:
        """
        Retrieves an unique, encrypted fingerprint to submit to
        Adyen's /submitThreeDS2Fingerprint endpoint.

        Args:
            token (str): Token from TooGoodToGo's /api/payment/v4 endpoint.
                         This token can be found inside the 'payload' field
                         of the response as soon as the 'state' field changes
                         to 'ADDITIONAL_AUTHORIZATION_REQUIRED'.

        Returns:
            str: Encrypted fingerprint string to be submitted to Adyen. This
                 value should be set as the 'fingerprintResult' parameter of
                 the payload.
        """
        response = self._post(
            url=Endpoints.FINGERPRINT,
            json={"token": token}
        )
        fingerprint = response.json()["fingerprint"]
        return fingerprint

    def get_3ds_challenge_data(
        self,
        token: str,
        action: Literal["initialize", "select", "confirm"],
        selection: str | None = None
    ) -> tuple[str, str]:
        """
        Retrieves the URL of the 3DS challenge and the encrypted payload to
        submit to it. The payload can initiate the challenge, submit
        additional selections or confirm the challenge.

        Args:
            token (str): Token from Adyen's /submitThreeDS2Fingerprint
                         endpoint. This is the 'token' field which can be found
                         inside the 'action' field of the response.
            action (Literal[
                "initialize",
                "select",
                "confirm",
            ]): If 'initialize' the payload will trigger a new 3DS challenge.
                If 'select' then a selection string needs to be provided which
                will be used to complete further steps required by the card
                issuer (e.g. trusting the merchant).
                If 'confirm' the payload will indicate that the challenge has
                been confirmed by the user and signal the server to process the
                payment.
            selection (str | None): An additional selection made to complete
                                    further steps during the 3DS process.
                                    Defaults to None.

        Raises:
            RuntimeError: If action was set to 'select' but no selection was
                          provided.

        Returns:
            tuple[str, str]: The challenge URL and the challenge data to submit
                             to it.
        """
        # Configure payload
        data = {"token": token}
        if action == "select":
            if not selection:
                raise RuntimeError(
                    "Used action=select without providing a selection."
                )
            data["selection"] = selection

        # Submit request
        response = self._post(
            url=f"{Endpoints.THREE_DS_CHALLENGE}/{action}",
            json=data
        )
        payload = response.json()
        challenge_url = payload["challengeUrl"]
        challenge_data = payload["challengeData"]
        return challenge_url, challenge_data

    def get_3ds_challenge_status(
        self,
        token: str,
        challenge_response: str,
    ) -> ThreeDS2Status:
        """
        Retrieves the current status of a 3DS challenge. This requires the 3DS
        challenge to be initiated.

        Args:
            token (str): Token from Adyen's /submitThreeDS2Fingerprint
                         endpoint. This is the 'token' field which can be found
                         inside the 'action' field of the response.
            challenge_response (str): Response of the server handling the 3DS
                                      challenge after sending data to it.

        Returns:
            ThreeDS2Status: Dataclass object with the current status and an
                            optional selection attribute if additional steps
                            are required during the 3DS challenge.
        """
        response = self._post(
            url=f"{Endpoints.THREE_DS_CHALLENGE}/status",
            json={"token": token, "challengeResponse": challenge_response},
        )
        payload = response.json()
        if "selection" in payload:
            selection = payload["selection"]
            return ThreeDS2Status(
                status=payload["status"],
                challenge_info_label=selection["challenge_info_label"],
                challenge_info_text=selection["challenge_info_text"],
                challenge_select_info=selection["challenge_select_info"],
            )
        return ThreeDS2Status(
            status=payload["status"],
        )
