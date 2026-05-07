import base64
import json
import re
from typing import Any, cast
from uuid import uuid4

from bs4 import BeautifulSoup

from tgtg_cli.apis.base import BaseClient
from tgtg_cli.cli.config import Config
from tgtg_cli.cli.types import (
    BinLookupResult,
    ThreeDS2FingerprintResultAction,
    ThreeDS2FingerprintResultCompleted,
)
from tgtg_cli.utils.exceptions import UnexpectedResponse

CHECKOUT_SHOPPER_URL = "https://checkoutshopper-live.adyen.com/"
CHECKOUT_ANALYTICS_URL = "https://checkoutanalytics-live.adyen.com/"
TGTG_CLIENT_KEY = "live_VPX45BIMLFAIVARYVKEDNC7OXIFBRQZ5"

OKHTTP_VERSION = "5.3.2"
ADYEN_VERSION = "5.17.0"


class Endpoints:
    BIN_LOOKUP = (
        CHECKOUT_SHOPPER_URL
        + f"checkoutshopper/v2/bin/binLookup?clientKey={TGTG_CLIENT_KEY}"
    )
    CHECKOUT_ATTEMPT = (
        CHECKOUT_ANALYTICS_URL
        + f"checkoutanalytics/v3/analytics?clientKey={TGTG_CLIENT_KEY}"
    )
    CHECKOUT_DETAILS = (
        CHECKOUT_ANALYTICS_URL
        + "checkoutanalytics/v3/analytics/{checkout_attempt_id}"
        + f"?clientKey={TGTG_CLIENT_KEY}"
    )
    PUBLIC_KEY = (
        CHECKOUT_SHOPPER_URL
        + f"checkoutshopper/v1/clientKeys/{TGTG_CLIENT_KEY}"
    )
    SUBMIT_3DS2_FINGERPRINT = (
        CHECKOUT_SHOPPER_URL
        + "checkoutshopper/v1/submitThreeDS2Fingerprint"
        + f"?token={TGTG_CLIENT_KEY}"
    )


class Adyen(BaseClient):

    def __init__(self, config: Config):
        # IMPORTANT: The user agent header can't be fetched dynamically and
        #            needs to be updated manually if it changes in newer
        #            versions of the Adyen SDK.
        super().__init__(
            config=config,
            headers={
                "User-Agent": f"okhttp/{OKHTTP_VERSION}",
                "Accept-Encoding": "gzip",
            },
            proxy=config.settings.account.proxy,
        )

    def get_public_key(self) -> str:
        """
        Retrieves Adyen's public key used for client-side card encryption.

        Returns:
            str: Public key string.
        """
        response = self._get(url=Endpoints.PUBLIC_KEY)
        return response.json()["publicKey"]

    def get_checkout_attempt_id(
        self,
        device_brand: str,
        device_model: str,
        system_version: str,
        screen_width: int,
        code: str,
        minor_units: int,
    ) -> str:
        """
        Retrieves a checkout attempt ID from Adyen.

        Args:
            device_brand (str): Device brand, e.g. "google".
            device_model (str): Device model, e.g. "Pixel 8 Pro".
            system_version (str): API level of the Android version, e.g. "34".
            screen_width (int): Native portrait screen width in pixels.
            code (str): 3-letter ISO 4217 currency code.
            minor_units (int): Payment amount in minor units, e.g. 1000
                               for EUR 10.00.

        Returns:
            str: Checkout attempt ID.
        """
        data = {
            "version": ADYEN_VERSION,
            "channel": "android",
            "platform": "android",
            "locale": "en-GB",
            "component": "scheme",
            "flavor": "components",
            "level": "all",
            "deviceBrand": device_brand,
            "deviceModel": device_model,
            "referrer": "com.app.tgtg",
            "systemVersion": system_version,
            "screenWidth": screen_width,
            "paymentMethods": ["scheme"],
            "amount": {"currency": code, "value": minor_units},
        }
        response = self._post(Endpoints.CHECKOUT_ATTEMPT, json=data)
        return response.json()["checkoutAttemptId"]

    def get_credit_card_details(self, encrypted_bin: str) -> BinLookupResult:
        """
        Retrieves card metadata from the encrypted BIN number. The response
        contains the brand of the credit card.

        Args:
            encrypted_bin (str): Encrypted card BIN number.

        Returns:
            BinLookupResult: Response with card metadata.
        """
        data = {
            "encryptedBin": encrypted_bin,
            "requestId": str(uuid4()),
            "supportedBrands": ["maestro", "mc", "visa"],
            "type": "scheme",
        }
        response = self._post(url=Endpoints.BIN_LOOKUP, json=data)
        return response.json()

    def submit_3ds2_fingerprint(
        self, fingerprint_result: str, payment_data: str
    ) -> ThreeDS2FingerprintResultAction | ThreeDS2FingerprintResultCompleted:
        """
        Submits the 3DS2 fingerprint.

        Args:
            fingerprint_result (str): Encrypted fingerprint payload.
            payment_data (str): Payment data of the current checkout attempt.

        Returns:
            ThreeDS2FingerprintResultAction |
            ThreeDS2FingerprintResultCompleted: Response of the 3DS2
                                                fingerprint submission
                                                signalizing whether a manual
                                                3DS challenge is required or
                                                not.
        """
        data = {
            "fingerprintResult": fingerprint_result,
            "paymentData": payment_data,
        }
        response = self._post(
            url=Endpoints.SUBMIT_3DS2_FINGERPRINT,
            json=data,
        )
        return response.json()

    def get_redirect_form_data(
        self,
        redirect_url: str,
    ) -> tuple[str, dict[str, str]]:
        """
        Retrieves the form data from Adyen's 3DS1 redirect URL. This includes
        the action URL and all hidden inputs (e.g. MD, PaReq) that need to be
        submitted.

        Args:
            redirect_url (str): URL of the redirect bridge as provided by
                                TooGoodToGo's API.

        Raises:
            UnexpectedResponse: If the bridge form could not be found in the
                                response.

        Returns:
            tuple[str, dict[str, str]]: Action URL of the bridge form and the
                                        payload to submit to it.
        """
        # Load redirect URL
        response = self._get(url=redirect_url)

        # Parse form URL and input values from response
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form", id="pageform")
        if form is None:
            raise UnexpectedResponse(
                "Unable to parse form of Adyen's 3DS1 redirect URL."
            )
        action_url = form["action"]
        payload = {
            field["name"]: field["value"]
            for field in form.find_all("input", type="hidden")
        }
        return cast(str, action_url), cast(dict[str, str], payload)

    def submit_redirect_form(
        self,
        action_url: str,
        payload: dict[str, str],
    ) -> tuple[dict[str, Any], str, str]:
        """
        Submits the form from Adyen's 3DS1 redirect URL. Extracts the embedded
        challenge token from the response and decodes it. This token contains
        all required fields to build the CReq payload (acsURL, acsTransID,
        threeDSServerTransID, messageVersion). Parses the originKey and the
        returnURL from the response.

        Args:
            action_url (str): URL to submit the form to.
            payload (dict[str, str]): Payload to submit to the action_url.

        Raises:
            UnexpectedResponse: If any of the required values could not be
                                parsed from the form submission response.

        Returns:
            tuple[dict[str, Any], str]: Decoded challenge token, the origin key
                                        and the return URL to load after the
                                        challenge was accepted.
        """
        # Submit form
        response = self._post(url=action_url, data=payload)

        # Load 'challengeToken' from response
        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = None
        for elem in soup.find_all("script"):
            if elem.string and "hydrateClient" in elem.string:
                script_tag = elem.string
                break
        else:
            raise UnexpectedResponse(
                "Unable to parse response of the form submission of Adyen's "
                "3DS1 redirect URL."
            )

        # Parse params from script
        match = re.search(
            pattern=r"window\.hydrateClient\(\s*(\{.*?\})\s*\);",
            string=script_tag,
            flags=re.DOTALL,
        )
        if not match:
            raise UnexpectedResponse(
                "Unable to parse 3DS redirect bridge response."
            )

        # Quote unquoted keys
        literal = match.group(1)
        literal = re.sub(r'([{,]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', literal)
        data = json.loads(literal)

        # Parse challengeToken and decode it
        challenge_token = data.get("challengeToken")
        if challenge_token is None:
            raise UnexpectedResponse(
                "Unable to parse 3DS redirect bridge response. "
                "Challenge token not found."
            )
        challenge_data = json.loads(base64.b64decode(challenge_token))

        # Parse originKey
        origin_key = data.get("originKey")
        if origin_key is None:
            raise UnexpectedResponse(
                "Unable to parse 3DS redirect bridge response. "
                "Origin key not found."
            )

        # Parse returnUrl
        return_url = data.get("returnUrl")
        if return_url is None:
            raise UnexpectedResponse(
                "Unable to parse 3DS redirect bridge response. "
                "Return URL not found."
            )
        return challenge_data, origin_key, return_url

    def submit_3dnotif(
        self,
        origin_key: str,
        psp_reference: str,
        cres: str,
    ) -> None:
        """
        Notifies Adyen that the 3DS challenge has been completed by submitting
        the CRes payload.

        Args:
            origin_key (str): Origin key from the redirect bridge response.
            psp_reference (str): PSP reference of the payment.
            cres (str): Base64url-encoded CRes payload (challenge result).
        """
        self._post(
            url=(
                f"{CHECKOUT_SHOPPER_URL}checkoutshopper/3dnotif.shtml"
                f"?originKey={origin_key}&pspReference={psp_reference}"
            ),
            data={"cres": cres, "threeDSSessionData": ""},
        )

    def submit_payment_authentication_request(
        self,
        trans_status: str,
        pa_req: str,
    ) -> str:
        """
        Submits a payment authentication request (PaReq) after the user has
        accepted the 3DS challenge.

        Args:
            trans_status (str): Status of the transaction, e.g. "Y".
            pa_req (str): Encrypted payment authentication request as provided
                          by Adyen in the redirect URL.

        Returns:
            str: Payment authentication response (PaRes).
        """
        response = self._post(
            url=(
                "https://checkoutshopper-live.adyen.com/checkoutshopper/"
                "finish.shtml"
            ),
            data={
                "transStatus": (None, trans_status),
                "PaReq": (None, pa_req),
            }
        )
        return response.json()["PaRes"]

    def submit_payment_authentication_response(
            self,
            return_url: str,
            md: str,
            pa_res: str,
        ) -> None:
        """
        Submits the PaRes to the return URL. Loads the form values of the
        response and submits it again. This finalizes the payment process.

        Args:
            return_url (str): URL to submit PaRes and form data to.
            md (str): Merchant data (MD) as provided by Adyen in the redirect
                      URL.
            pa_res (str): Payment authentication response (PaRes) received
                          after submitting the payment authentication request.

        Raises:
            UnexpectedResponse: If the response form could not be found after
                                submitting the PaRes.

        """
        # Submit PaRes (Return #1)
        response = self._post(
            url=return_url,
            data={
                "MD": md,
                "PaRes": pa_res,
            },
        )

        # Parse values from response
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form", id="pageform")
        if form is None:
            raise UnexpectedResponse("Unable to submit form in return step 2.")
        payload = {
            field["name"]: field["value"]
            for field in form.find_all("input", type="hidden")
        }

        # Submit form (Return #2)
        response = self._post(
            url=return_url,
            data=payload,
        )
