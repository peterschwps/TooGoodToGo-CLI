import re
from typing import cast
from urllib.parse import urlsplit

from tgtg_cli.apis.base import BaseClient
from tgtg_cli.cli.config import Config
from tgtg_cli.utils.exceptions import UnexpectedResponse, UnsupportedIssuer
from tgtg_cli.utils.models import DKB, Bunq, Issuer
from tgtg_cli.utils.parsing import HTMLFormParser


class AccessControlServer(BaseClient):
    def __init__(self, config: Config, user_agent: str):
        """
        Initializes the class.

        Args:
            config (Config): Instance of the Config class.
            user_agent (str): User agent to use. Should be the same as the one
                              used for the TGTG client.
        """
        super().__init__(
            config=config,
            headers={
                "Accept": "*/*",
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip",
            },
            proxy=config.settings.account.proxy,
        )

    @staticmethod
    def detect_issuer(acs_url: str) -> type[Issuer]:
        """
        Detects the issuer based on the ACS URL. Raises an UnsupportedIssuer
        exception if the authorization flow is not yet supported. This
        indicates that the full redirect URL should be sent to the user to
        complete the flow manually.

        Args:
            acs_url (str): URL of the ACS.

        Raises:
            UnsupportedIssuer: If the issuer is not supported.

        Returns:
            type[Issuer]: Class object of the issuing bank.
        """
        if "bunq" in acs_url:
            return Bunq
        if "dkb" in acs_url:
            return DKB
        raise UnsupportedIssuer

    def submit_challenge_data(
        self,
        challenge_url: str,
        challenge_data: str,
    ) -> str:
        """
        Submits an encrypted payload to a given URL (Access Control Server).
        This should be used to request a manual 3DS2 challenge, submit
        selections or complete a pending challenge after it has been manually
        accepted/declined by the user.

        Args:
            challenge_url (str): URL to submit the encrypted payload to.
            challenge_data (str): Encrypted payload to submit.

        Returns:
            str: Response from the Access Control Server.
        """
        response = self._post(
            url=challenge_url,
            data=challenge_data,
            headers={"Content-Type": "application/jose;charset=UTF-8"},
        )
        return response.text

    def submit_challenge_request_browser(
        self,
        issuing_bank: type[Issuer],
        acs_url: str,
        creq: str,
    ) -> Issuer:
        """
        Submits the CReq payload to the ACS URL provided in the challengeToken
        of the initial in-browser form submission.
        Parses the polling URL and all other required parameters to fetch the
        status of the challenge request and builds the Issuer dataclass.

        Args:
            issuing_bank (type[Issuer]): Class object of the issuing bank.
            acs_url (str): URL of the challenge request endpoint of the ACS.
            creq (str): Base64url-encoded CReq payload.

        Raises:
            UnexpectedResponse: If any error occurs when parsing the required
                                parameters.
            UnsupportedIssuer: If the issuer is not supported. This is only for
                               the type checker and shouldn't happen as the
                               error should be raised earlier in the
                               authorization flow.

        Returns:
            Issuer: A dataclass of the issuer. This class contains the polling
                    URL and any other parameters required to poll the status of
                    the challenge request.
        """
        # Submit CReq
        response = self._post(
            url=acs_url,
            data={"creq": creq},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Parse polling URL and payload (if required) from the response
        error_message = (
            "Unable to fetch the response of the challenge request submission."
        )
        if issuing_bank is Bunq:
            # Parse polling URL
            base_match = re.search(
                r'var\s+baseApiUrl\s*=\s*["\']([^"\']+)["\']',
                response.text,
            )
            endpoint_match = re.search(
                r'baseApiUrl\s*\+\s*["\']([^"\']+)["\']',
                response.text,
            )
            if base_match is None or endpoint_match is None:
                raise UnexpectedResponse(error_message)
            hostname = base_match.group(1).rstrip("/")
            endpoint = endpoint_match.group(1)
            polling_url = hostname + endpoint
            return Bunq(polling_url=polling_url)

        elif issuing_bank is DKB:
            # Create form parser from response
            parser = HTMLFormParser(
                html=response.text,
                form_id="mainForm",
                error_message=error_message,
            )

            # Parse polling URL
            parts = urlsplit(acs_url)
            endpoint = cast(str, parser.form["action"]).lstrip("/")
            polling_url = f"{parts.scheme}://{parts.netloc}/{endpoint}"

            # Parse payload
            session_id = parser.parse_html_form_input(name="sessionid")
            request_id = parser.parse_html_form_input(name="requestid")
            return DKB(
                polling_url=polling_url,
                session_id=session_id,
                request_id=request_id,
            )

        else:
            raise UnsupportedIssuer

    def submit_initial_polling_request(self, issuer: Issuer) -> None:
        """
        Sends the initial request to the ACS to fetch the current state of a
        challenge request. This starts the 3DS challenge that the user has to
        accept. Updates any parameters in-place for the final polling request
        after the user has confirmed the challenge.
        This request should only be sent once!

        The response is currently not used as it would require a different
        implementation for each ACS. This means that the status of the request
        should be regarded as "pending".

        Args:
            issuer (Issuer): Issuer dataclass with the URL and additional
                             parameters to use for polling the status.

        Raises:
            UnsupportedIssuer: If the issuer is not supported. This is only for
                               the type checker and shouldn't happen as the
                               error should be raised earlier in the
                               authorization flow.
        """
        # Send request depending on the issuer
        match issuer:
            case Bunq():
                self._get(url=issuer.polling_url)

            case DKB():
                data = {
                    "oobContinue": (None, "POLL"),
                    "sessionid": (None, issuer.session_id),
                    "requestid": (None, issuer.request_id),
                    "isSpcSupportedByBrowser": (None, "false"),
                }
                response = self._post(url=issuer.polling_url, files=data)

                # Update request ID from response
                parser = HTMLFormParser(
                    html=response.text,
                    form_id="mainForm",
                    error_message=(
                        "Unable to parse the response form of the initial "
                        "status polling request."
                    ),
                )
                issuer.request_id = parser.parse_html_form_input(
                    name="requestid",
                )

            case _:
                raise UnsupportedIssuer

    def submit_final_polling_request(self, issuer: Issuer) -> str:
        """
        Sends the final request to the ACS to fetch the current state of a
        challenge request after the user has confirmed the 3DS challenge. The
        response of this request will contain the CRes which needs to be sent
        to Adyen to complete the payment.
        This request should only be sent once!

        Args:
            issuer (Issuer): Issuer dataclass with the URL and additional
                             parameters to use for polling the status.

        Raises:
            UnsupportedIssuer: If the issuer is not supported. This is only for
                               the type checker and shouldn't happen as the
                               error should be raised earlier in the
                               authorization flow.

        Returns:
            str: Challenge response (CRes) to submit to Adyen to complete the
                 payment.
        """
        # Send request depending on the issuer
        match issuer:
            case Bunq():
                response = self._get(url=issuer.polling_url)
                response = response.json()["Response"][0]
                cres = response[list(response)[0]]["challenge_result"]
                return cres

            case DKB():
                data = {
                    "oobContinue": (None, "POLL"),
                    "sessionid": (None, issuer.session_id),
                    "requestid": (None, issuer.request_id),
                    "isSpcSupportedByBrowser": (None, "false"),
                }
                response = self._post(url=issuer.polling_url, files=data)

                # Parse CRes from response
                parser = HTMLFormParser(
                    html=response.text,
                    form_id="3dsform",
                    error_message=(
                        "Unable to parse the response form of the final "
                        "status polling request."
                    ),
                )
                cres = parser.parse_html_form_input(name="cres")
                return cres

            case _:
                raise UnsupportedIssuer
