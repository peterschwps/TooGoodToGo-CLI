import base64
import json
from functools import cached_property
from random import randint
from time import sleep, time
from typing import cast
from urllib.parse import parse_qs, urlparse

from pydantic_extra_types.payment import PaymentCardBrand, PaymentCardNumber

from tgtg_cli.apis.acs import AccessControlServer
from tgtg_cli.apis.adyen import Adyen
from tgtg_cli.apis.cryptography import Cryptography
from tgtg_cli.apis.tgtg import TGTG
from tgtg_cli.cli import console
from tgtg_cli.cli.config import Config
from tgtg_cli.cli.types import (
    Error,
    OrderStatusResult,
    ReservedOrder,
    ThreeDS2FingerprintResultAction,
    ThreeDS2FingerprintResultCompleted,
)
from tgtg_cli.utils.encryption import Encryption
from tgtg_cli.utils.exceptions import UnexpectedResponse, UnsupportedIssuer
from tgtg_cli.utils.models import (
    AdditionalAuthorizationDetailsRedirect,
    AdditionalAuthorizationDetailsThreeDS2,
    CheckoutDetails,
    CheckoutState,
    OrderDetails,
    PaymentDetails,
    RedirectDetails,
    ThreeDS2Details,
)
from tgtg_cli.utils.notifications import send_notification, send_webhook


class OrderService:
    def __init__(self, config: Config, tgtg: TGTG):
        self._config = config
        self._tgtg = tgtg
        self._checkout_details: CheckoutDetails
        self._order_details: OrderDetails
        self._payment_details: PaymentDetails

    # Note: All cached properties are only implemented to prevent 'expensive'
    #       initialization of additional classes before creating an order!
    @cached_property
    def _acs(self) -> AccessControlServer:
        return AccessControlServer(
            config=self._config,
            user_agent=self._tgtg.user_agent,
        )

    @cached_property
    def _adyen(self) -> Adyen:
        return Adyen(config=self._config)

    @cached_property
    def _cryptography(self) -> Cryptography:
        return Cryptography(config=self._config)

    def checkout_item(
        self,
        item_id: str,
        item_name: str,
        count: int = 1,
    ) -> bool:
        """
        Checks out an item. Handles the entire checkout process, including the
        payment process.

        Args:
            item_id (str): ID if the item to checkout.
            item_name (str): Displayed name of the item.
            count (int, optional): Number of items to checkout. Defaults to 1.

        Raises:
            ValueError: If 3DS2 is required but no token was found.
            UnexpectedResponse: If an unhandled error occured.

        Returns:
            bool: True if the order was successful, otherwise False.
        """

        # Create order
        # IMPORTANT: This request should be sent as quickly as possible since
        #            it reserves the item for 5 minutes!
        console.info(f"Creating order for item '{item_name}'...")
        self._create_order(item_id=item_id, count=count)
        send_notification(
            topic=self._config.settings.monitor.ntfy_topic,
            title="Item available!",
            message=(
                f"The monitored item '{item_name}' is back in stock.\n"
                f"Starting checkout..."
            ),
            headers={"tag": "bangbang"},
        )

        # Add sleep to mimic human behavior
        # (at this point the item is already reserved for 5 minutes!)
        delay = randint(500, 1000) / 100
        with console.waiting(
            status=f"Sleeping for {delay} seconds before proceeding...",
        ):
            pass
            # sleep(delay)

        # Initiate payment
        with console.waiting(status="Initiating payment..."):
            self._get_payment_details()
            self._initiate_payment()

        # Update checkout state until it changes
        while (
            self._checkout_details.state
            == CheckoutState.AUTHORIZATION_INITIATED
        ):
            self._update_checkout_state()
            sleep(1)

        # Check if additional authorization is required
        # If authorization type is "redirect"
        if (
            self._checkout_details.state
            is CheckoutState.ADDITIONAL_AUTHORIZATION_REQUIRED
            and isinstance(
                self._checkout_details.additional_authorization_details,
                AdditionalAuthorizationDetailsRedirect,
            )
        ):
            # Try to initiate redirect challenge for supported providers
            console.info("In-Browser 3DS challenge required!")
            with console.waiting(status="Starting 3DS challenge...") as status:
                try:
                    self._initiate_redirect_challenge()
                    issuer_is_supported = True

                except UnsupportedIssuer:
                    issuer_is_supported = False

            # If the issuer is not supported, send a webhook with the
            # challenge URL via Ntfy and have the user complete the challenge
            # flow manually (which is usually just loading the page, accepting
            # the 3DS request and waiting for the page to redirect to the
            # return URL)
            if not issuer_is_supported:
                console.warning(
                    "Issuer is not yet supported. Feel free to "
                    "open an issue on GitHub if you think that it is worth "
                    "adding support for this issuer.",
                    show_time=True,
                )
                console.info("Sending Ntfy webhook with challenge URL...")
                with console.waiting(
                    status="Waiting for user to complete the challenge...",
                ) as status:
                    try:
                        send_webhook(
                            topic=self._config.settings.monitor.ntfy_topic,
                            challenge_url=(
                                self._checkout_details \
                                .additional_authorization_details.url
                            ),
                        )
                    except RuntimeError as e:
                        status.stop()
                        console.error(str(e), show_time=True)
                        return False

            # If the provider is supported, complete the challenge flow
            # automatically so the user only has to confirm the 3DS request
            else:
                # Check if all details are set
                redirect_details = self._checkout_details.redirect_details
                if redirect_details is None:
                    raise UnexpectedResponse(
                        "Failed to parse all required values."
                    )

                # Send webhook with confirmation button
                console.info("Sending Ntfy webhook...")
                with console.waiting(
                    status="Waiting for user to complete the challenge...",
                ) as status:
                    try:
                        send_webhook(self._config.settings.monitor.ntfy_topic)
                    except RuntimeError as e:
                        status.stop()
                        console.error(str(e), show_time=True)
                        return False

                # Check if challenge has been accepted
                with console.waiting(status="Completing payment..."):
                    cres = self._acs.submit_final_polling_request(
                        issuer=redirect_details.issuer,
                    )

                # Submit challenge result
                self._adyen.submit_3dnotif(
                    origin_key=redirect_details.origin_key,
                    psp_reference=redirect_details.psp_reference,
                    cres=cres,
                )

                # Submit PaReq
                pa_res = self._adyen.submit_payment_authentication_request(
                    trans_status="Y",
                    pa_req=redirect_details.pa_req,
                )

                # Submit PaRes
                self._adyen.submit_payment_authentication_response(
                    return_url=redirect_details.return_url,
                    md=redirect_details.md,
                    pa_res=pa_res,
                )

        # If authorization type is "threeDS2"
        elif (
            self._checkout_details.state
            is CheckoutState.ADDITIONAL_AUTHORIZATION_REQUIRED
            and isinstance(
                self._checkout_details.additional_authorization_details,
                AdditionalAuthorizationDetailsThreeDS2,
            )
        ):
            # Build 3DS2 details and compute fingerprint
            self._prepare_3ds2_details()

            # Submit 3DS2 fingerprint
            with console.waiting(status="Submitting fingerprint..."):
                self._submit_3ds2_fingerprint()

            # Additional flow if manual 3DS challenge is required
            if (
                self._checkout_details.needs_3ds2
                and self._checkout_details.three_ds2_details
            ):
                # Request challenge data
                console.info("3DS challenge required!")
                if self._checkout_details.three_ds2_details.token is None:
                    raise ValueError(
                        "Unable to request challenge data. "
                        "3DS2 token is missing."
                    )
                challenge_url, challenge_data = (
                    self._cryptography.get_3ds_challenge_data(
                        token=self._checkout_details.three_ds2_details.token,
                        action="initialize",
                    )
                )

                # Submit challenge request
                with console.waiting(status="Starting 3DS challenge..."):
                    challenge_response = self._acs.submit_challenge_data(
                        challenge_url=challenge_url,
                        challenge_data=challenge_data,
                    )

                    # Fetch challenge status
                    challenge_status = (
                        self._cryptography.get_3ds_challenge_status(
                            token=(
                                self._checkout_details.three_ds2_details.token
                            ),
                            challenge_response=challenge_response,
                        )
                    )

                # Loop until challenge completed (or unknown status)
                start_time = round(time())
                total_seconds = 240  # total time to finish payment process
                while challenge_status.status in (
                    "awaiting_confirmation",
                    "awaiting_selection",
                ):
                    if challenge_status.status == "awaiting_confirmation":
                        console.info("3DS challenge needs to be confirmed!")
                        token = self._checkout_details.three_ds2_details.token
                        challenge_url, challenge_data = (
                            self._cryptography.get_3ds_challenge_data(
                                token=token,
                                action="confirm",
                            )
                        )
                        console.info("Sending Ntfy webhook...")
                        with console.waiting(
                            status=(
                                "Waiting for user to confirm challenge "
                                "completion..."
                            ),
                        ) as status:
                            # Calculate time left for completing payment
                            seconds_passed = round(time()) - start_time
                            seconds_left = total_seconds - seconds_passed
                            if seconds_left < 3:
                                status.stop()
                                console.error(
                                    "Payment process took too long to "
                                    "complete.",
                                    show_time=True,
                                )
                                return False

                            # Send webhook with confirmation button
                            try:
                                send_webhook(
                                    topic=(
                                        self._config.settings \
                                        .monitor.ntfy_topic
                                    ),
                                    seconds_to_wait=seconds_left,
                                )
                            except RuntimeError as e:
                                status.stop()
                                console.error(str(e), show_time=True)
                                return False

                    else:
                        # Retrieve selection from user
                        console.info(
                            "Additional selections required to complete the "
                            "3DS challenge!"
                        )
                        console.info("Sending Ntfy webhook...")
                        with console.waiting(
                            status="Waiting for user to make a selection...",
                        ) as status:
                            # Calculate time left for completing payment
                            seconds_passed = round(time()) - start_time
                            seconds_left = total_seconds - seconds_passed
                            if seconds_left < 3:
                                status.stop()
                                console.error(
                                    "Payment process took too long to "
                                    "complete.",
                                    show_time=True,
                                )
                                return False

                            # Send webhook with selection options
                            try:
                                header = challenge_status.challenge_info_label
                                body = challenge_status.challenge_info_text
                                actions = (
                                    challenge_status.challenge_select_info
                                )
                                selection = send_webhook(
                                    topic=self._config.settings.monitor.ntfy_topic,
                                    header=header,
                                    body=body,
                                    actions=actions,
                                    seconds_to_wait=seconds_left,
                                )
                            except RuntimeError as e:
                                status.stop()
                                console.error(str(e), show_time=True)
                                return False

                        # Submit challenge data
                        token = self._checkout_details.three_ds2_details.token
                        challenge_url, challenge_data = (
                            self._cryptography.get_3ds_challenge_data(
                                token=token,
                                action="select",
                                selection=selection,
                            )
                        )

                    # Re-submit challenge request
                    status_message = (
                        "Confirming 3DS challenge..."
                        if challenge_status.status == "awaiting_confirmation"
                        else "Submitting user selection..."
                    )
                    with console.waiting(status=status_message):
                        challenge_response = self._acs.submit_challenge_data(
                            challenge_url=challenge_url,
                            challenge_data=challenge_data,
                        )

                        # Fetch challenge status
                        token = self._checkout_details.three_ds2_details.token
                        challenge_status = (
                            self._cryptography.get_3ds_challenge_status(
                                token=token,
                                challenge_response=challenge_response,
                            )
                        )

                else:
                    if challenge_status.status != "completed":
                        raise UnexpectedResponse(
                            "Unknown 3DS status: %s.", challenge_status.status
                        )

            # Send additional authorization
            with console.waiting(status="Completing payment..."):
                self._submit_additional_authorization()

        # Check payment status
        self._update_checkout_state()
        if self._checkout_details.state is CheckoutState.ABORTED:
            console.error("Order aborted!", show_time=True)
            console.error(
                "Payment process took too long to complete.",
                show_time=True,
            )
            send_notification(
                topic=self._config.settings.monitor.ntfy_topic,
                title="Order aborted!",
                message=(
                    f"Failed to complete order "
                    f"#{self._order_details.id.upper()}. "
                    f"Payment process took too long."
                ),
                headers={"tag": "x"},
            )
            return False

        # Await payment status change (to "AUTHORIZED" if successful)
        with console.waiting(status="Waiting for payment to be processed..."):
            while (
                self._checkout_details.state
                is CheckoutState.ADDITIONAL_AUTHORIZATION_INITIATED
            ):
                self._update_checkout_state()
                sleep(1)

        # Check if order was successful
        order_status = self._get_order_status()
        if order_status == "ACTIVE":
            console.success("Successfully completed order!")
            send_notification(
                topic=self._config.settings.monitor.ntfy_topic,
                title="Order completed!",
                message=(
                    f"Order #{self._order_details.id.upper()} was "
                    f"successfully checked out. You should now see it in "
                    f"your TooGoodToGo account."
                ),
                headers={"tag": "white_check_mark"},
            )

            # INFO: You can uncomment this block when debugging to
            #       automatically cancel all newly created orders.
            #
            # delay = randint(500, 1000) / 100
            # with console.waiting(
            #     status=(
            #         f"Sleeping for {delay} seconds before cancelling "
            #         f"order..."
            #     )):
            #     sleep(delay)
            # order_cancellation_details = self._tgtg.cancel_order(
            #     order_id=self._order_details.id,
            # )
            # console.success(f"Order cancelled: {order_cancellation_details}")

            return True

        else:
            console.error(f"Order failed! Status: {order_status}.")
            send_notification(
                topic=self._config.settings.monitor.ntfy_topic,
                title="Order failed!",
                message=(
                    f"Failed to complete order "
                    f"#{self._order_details.id.upper()}."
                ),
                headers={"tag": "x"},
            )
            return False

    def _create_order(self, item_id: str, count: int = 1) -> None:
        """
        Creates an order for the given item and count. Stores the result in
        self._order_details.

        Args:
            item_id (str): ID of the item to order.
            count (int, optional): Number of items to order. Defaults to 1.
        """
        order = self._tgtg.create_order(
            item_id=item_id,
            count=count,
        )
        order = cast(ReservedOrder, order["order"])
        self._order_details = OrderDetails(
            id=order["id"],
            quantity=order["order_line"]["quantity"],
            code=order["order_line"]["total_price"]["code"],
            minor_units=order["order_line"]["total_price"]["minor_units"],
            decimals=order["order_line"]["total_price"]["decimals"],
        )

    def _get_payment_details(self) -> None:
        """
        Creates the payment details needed to initiate the payment of an order.
        This includes encrypting the card details and checking the brand of the
        credit card. Stores the result in self._payment_details.
        """
        # Cast types for linter
        payment_details = self._config.settings.payment
        card_number = cast(PaymentCardNumber, payment_details.card_number)
        card_expiry_month = cast(int, payment_details.card_expiry_month)
        card_expiry_year = cast(int, payment_details.card_expiry_year)
        card_security_code = cast(str, payment_details.card_security_code)

        # Retrieve unique AES key and initialization vector
        aes_key_base64, iv_base64 = self._cryptography.get_encryptor()
        aes_key = base64.urlsafe_b64decode(aes_key_base64)
        iv = base64.urlsafe_b64decode(iv_base64)

        # Fetch public Adyen key
        public_key = self._adyen.get_public_key()
        exponent_hex, modulus_hex = public_key.split("|")

        # Encrypt card details
        encryption = Encryption(
            exponent_hex=exponent_hex,
            modulus_hex=modulus_hex,
            aes_key=aes_key,
            iv=iv,
        )
        encrypted_card_number = encryption.encrypt_card_number(
            card_number=card_number,
        )
        encrypted_expiry_month = encryption.encrypt_expiry_month(
            expiry_month=card_expiry_month,
        )
        encrypted_expiry_year = encryption.encrypt_expiry_year(
            expiry_year=card_expiry_year,
        )
        encrypted_security_code = encryption.encrypt_security_code(
            security_code=card_security_code,
        )

        # Get credit card brand
        if card_number.brand == PaymentCardBrand.amex:
            card_brand = "amex"
        elif card_number.brand == PaymentCardBrand.visa:
            card_brand = "visa"
        elif card_number.brand == PaymentCardBrand.mastercard:
            card_brand = "mc"
        else:
            encrypted_bin = encryption.encrypt_bin(
                bin_number=card_number[:11],
            )
            credit_card_details = self._adyen.get_credit_card_details(
                encrypted_bin=encrypted_bin,
            )
            card_brand = credit_card_details["brands"][0]["brand"]

        # Create payment details
        self._payment_details = PaymentDetails(
            encrypted_card_number=encrypted_card_number,
            encrypted_expiry_month=encrypted_expiry_month,
            encrypted_expiry_year=encrypted_expiry_year,
            encrypted_security_code=encrypted_security_code,
            credit_card_brand=card_brand,
        )

    def _initiate_payment(self) -> None:
        """
        Initiates the payment process for the order stored in
        self._order_details using the payment details stored in
        self._payment_details. Gets a checkout attempt ID from Adyen and
        initiates the payment process by sending all relevant payment details
        to TooGoodToGo's API. Stores the result in self._checkout_details.
        """
        # Start checkout attempt
        checkout_attempt_id = self._adyen.get_checkout_attempt_id(
            device_brand=self._config.device.brand,
            device_model=self._config.device.model,
            system_version=self._config.device.system_version,
            screen_width=self._config.device.screen_width,
            code=self._order_details.code,
            minor_units=self._order_details.minor_units,
        )

        # Initiate payment
        payment = self._tgtg.pay_order(
            checkout_attempt_id=checkout_attempt_id,
            encrypted_card_number=self._payment_details.encrypted_card_number,
            encrypted_expiry_month=(
                self._payment_details.encrypted_expiry_month
            ),
            encrypted_expiry_year=(
                self._payment_details.encrypted_expiry_year
            ),
            encrypted_security_code=(
                self._payment_details.encrypted_security_code
            ),
            brand=self._payment_details.credit_card_brand,
            code=self._order_details.code,
            decimals=self._order_details.decimals,
            minor_units=self._order_details.minor_units,
            order_id=self._order_details.id,
        )
        self._checkout_details = CheckoutDetails(
            checkout_attempt_id=checkout_attempt_id,
            payment_id=payment["payments"][0]["payment_id"],
            state=CheckoutState(payment["payments"][0]["state"]),
        )

    def _update_checkout_state(self) -> None:
        """
        Updates self._checkout_details by retrieving the latest payment
        status. If additional authorization is required, the payload is
        loaded and the additional_authorization_details are added to
        self._checkout_details.

        Raises:
            ValueError: If the payment_id is missing in self._checkout_details.
            UnexpectedResponse: If the payment failed for some reason.
            ValueError: If the payment's state was set to
                        "ADDITIONAL_AUTHORIZATION_REQUIRED" but no payload was
                        provided by TooGoodToGo's API.
        """
        if not self._checkout_details.payment_id:
            raise ValueError(
                "Unable to update checkout state. Payment ID is missing."
            )

        # Set latest payment status
        current_payment_status = self._tgtg.get_payment_status(
            payment_id=self._checkout_details.payment_id,
        )
        self._checkout_details.state = CheckoutState(
            current_payment_status["state"]
        )
        match self._checkout_details.state:
            case CheckoutState.ABORTED:
                return
            case CheckoutState.ADDITIONAL_AUTHORIZATION_INITIATED:
                return
            case CheckoutState.ADDITIONAL_AUTHORIZATION_REQUIRED:
                pass
            case CheckoutState.AUTHORIZATION_INITIATED:
                return
            case CheckoutState.AUTHORIZED:
                return
            case CheckoutState.FAILED:
                raise UnexpectedResponse(
                    "Payment failed. Please check your card details."
                )

        # If additional authorization required: load payload and add additional
        # details to checkout details
        payload_str = current_payment_status.get("payload")
        if not payload_str:
            raise ValueError(
                "Unable to proceed with checkout. Payload is missing even "
                "though additional authorization is required."
            )
        payload = json.loads(payload_str)

        # Additional check for supported authorization flows
        payload_type = payload.get("type")
        if payload_type == "threeDS2":
            self._checkout_details.additional_authorization_details = (
                AdditionalAuthorizationDetailsThreeDS2(
                    payment_data=payload["paymentData"],
                    token=payload["token"],
                )
            )
        elif payload_type == "redirect":
            self._checkout_details.additional_authorization_details = (
                AdditionalAuthorizationDetailsRedirect(url=payload["url"])
            )
        else:
            raise UnexpectedResponse(
                f"Unsupported authorization flow with payload type "
                f"'{payload_type}'. If you are able to reproduce this error, "
                f"please open an issue on GitHub."
            )

    def _initiate_redirect_challenge(self) -> None:
        """
        Initiates the in-browser 3DS challenge for the redirect authorization
        flow. Resolves Adyen's bridge form, submits it to retrieve the
        challenge data, builds the CReq payload and submits it to the ACS.
        The initial poll is triggered to register the challenge request on the
        ACS.

        Raises:
            ValueError: If the additional_authorization_details are missing
                        or not of type AdditionalAuthorizationDetailsRedirect.
            UnexpectedResponse: If any of the required parameters could not be
                                extracted from the redirect URL.
            UnsupportedIssuer: If the issuer is not supported (raised by
                               detect_issuer() of AccessControlServer class).
        """
        if not isinstance(
            self._checkout_details.additional_authorization_details,
            AdditionalAuthorizationDetailsRedirect,
        ):
            raise ValueError(
                "Unable to initiate redirect challenge. "
                "Redirect authorization details are missing."
            )

        # Extract params from redirect URL
        aad = self._checkout_details.additional_authorization_details
        url_query = parse_qs(urlparse(aad.url).query)
        md = url_query.get("MD", [""])
        pa_req = url_query.get("PaReq", [""])
        psp_references = url_query.get("pspReference", [""])
        if not all((md[0], pa_req[0], psp_references[0])):
            raise UnexpectedResponse(
                "Unable to extract required parameters from redirect URL."
            )

        # Resolve bridge form and submit it to obtain challenge data
        action_url, payload = self._adyen.get_redirect_form_data(
            redirect_url=aad.url,
        )
        challenge_data, origin_key, return_url = (
            self._adyen.submit_redirect_form(
                action_url=action_url,
                payload=payload,
            )
        )

        # Check if issuer is supported
        # This would raise an UnsupportedProvider exception if the flow is not
        # supported
        acs_url = challenge_data["acsURL"]
        issuing_bank = self._acs.detect_issuer(acs_url)

        # Build challenge request (CReq) payload
        creq = {
            "acsTransID": challenge_data["acsTransID"],
            "messageVersion": challenge_data["messageVersion"],
            "threeDSServerTransID": challenge_data["threeDSServerTransID"],
            "messageType": "CReq",
            "challengeWindowSize": "05",
        }
        json_bytes = json.dumps(creq, separators=(",", ":")).encode()
        creq = base64.urlsafe_b64encode(json_bytes).decode("ascii").rstrip("=")

        # Submit CReq to ACS
        issuer = self._acs.submit_challenge_request_browser(
            issuing_bank=issuing_bank,
            acs_url=acs_url,
            creq=creq,
        )

        # Add RedirectDetails to CheckoutDetails
        self._checkout_details.redirect_details = RedirectDetails(
            issuer=issuer,
            md=md[0],
            pa_req=pa_req[0],
            psp_reference=psp_references[0],
            origin_key=origin_key,
            return_url=return_url,
        )

        # Trigger initial poll so the ACS registers the request
        self._acs.submit_initial_polling_request(issuer=issuer)

    def _prepare_3ds2_details(self) -> None:
        """
        Builds ThreeDS2Details from the additional_authorization_details stored
        in self._checkout_details and assigns it. Computes the unique
        fingerprint via the Cryptography API.

        Raises:
            ValueError: If the required additional_authorization_details are
                         missing in self._checkout_details.
        """
        if not isinstance(
            self._checkout_details.additional_authorization_details,
            AdditionalAuthorizationDetailsThreeDS2,
        ):
            raise ValueError(
                "Unable to prepare 3DS2 details. "
                "Additional authorization details are missing."
            )
        aad = self._checkout_details.additional_authorization_details
        fingerprint_result = self._cryptography.get_fingerprint(
            token=aad.token,
        )
        self._checkout_details.three_ds2_details = ThreeDS2Details(
            fingerprint_result=fingerprint_result,
            payment_data=aad.payment_data,
        )

    def _submit_3ds2_fingerprint(self) -> None:
        """
        Submits the 3DS2 fingerprint to Adyen and checks if the payment
        requires a challenge to be completed manually. Updates
        self._checkout_details in place.

        Raises:
            ValueError: If the required three_ds2_details are missing in
                        self._checkout_details.
            UnexpectedResponse: If the fingerprint result type is 'completed'
                                but the transaction status is unknown (not 'Y',
                                which indicates a successful authentication).
            UnexpectedResponse: If the fingerprint result type is unknown.
        """
        if self._checkout_details.three_ds2_details is None:
            raise ValueError(
                "Unable to submit 3DS2 fingerprint. 3DS2 details are missing."
            )
        three_ds2_details = self._checkout_details.three_ds2_details
        fingerprint_result = self._adyen.submit_3ds2_fingerprint(
            fingerprint_result=three_ds2_details.fingerprint_result,
            payment_data=three_ds2_details.payment_data,
        )

        # Check if 3DS2 is required
        type = fingerprint_result.get("type")
        match type:
            case "action":
                fingerprint_result = cast(
                    ThreeDS2FingerprintResultAction, fingerprint_result
                )
                three_ds2_details.authorisation_token = fingerprint_result[
                    "action"
                ]["authorisationToken"]
                three_ds2_details.token = fingerprint_result["action"]["token"]
                self._checkout_details.needs_3ds2 = True
                return

            case "completed":
                fingerprint_result = cast(
                    ThreeDS2FingerprintResultCompleted, fingerprint_result
                )
                three_ds2_result_base64 = fingerprint_result["details"][
                    "threeDSResult"
                ]
                if three_ds2_result_base64:
                    three_ds2_result = json.loads(
                        base64.b64decode(three_ds2_result_base64).decode()
                    )
                    three_ds2_details.authorisation_token = three_ds2_result[
                        "authorisationToken"
                    ]
                    if three_ds2_result["transStatus"] != "Y":
                        raise UnexpectedResponse(
                            "Authentification of the payment method failed."
                        )
                return

            case _:
                raise UnexpectedResponse(
                    f"Unknown fingerprint result of type: {type}."
                )

    def _submit_additional_authorization(self) -> None:
        """
        Submits the additional authorization to TooGoodToGo's API. This
        notifies TooGoodToGo that the payment has been completed. Updates
        self._checkout_details.state by setting the latest payment status.

        Raises:
            ValueError: If the required three_ds2_details are missing in
                        self._checkout_details.
            ValueError: If the authorisation_token is missing in the
                        three_ds2_details.
            ValueError: If the payment_id is missing in
                        self._checkout_details.
        """
        if not self._checkout_details.three_ds2_details:
            raise ValueError(
                "Unable to submit additional authorization. "
                "3DS2 details are missing."
            )
        if not self._checkout_details.three_ds2_details.authorisation_token:
            raise ValueError(
                "Unable to submit additional authorization. "
                "Authorisation token is missing in 3DS2 details."
            )
        if not self._checkout_details.payment_id:
            raise ValueError(
                "Unable to submit additional authorization. "
                "Payment ID is missing."
            )
        additional_authorization_result = (
            self._tgtg.submit_additional_authorization(
                payment_id=self._checkout_details.payment_id,
                authorisation_token=(
                    self._checkout_details \
                    .three_ds2_details.authorisation_token
                ),
            )
        )
        self._checkout_details.state = CheckoutState(
            additional_authorization_result["state"]
        )

    def _get_order_status(self) -> str:
        """
        Checks the current state of self._order_details. Retries once if the
        API returns an error (which might happen if the order has not been
        fully processed yet).

        Raises:
            UnexpectedResponse: If the order status could not be retrieved.

        Returns:
            str: State of the order.
        """
        response = self._tgtg.get_order_status(order_id=self._order_details.id)
        if "errors" in response:
            sleep(1)
            response = cast(Error, response)
            response = self._tgtg.get_order_status(
                order_id=self._order_details.id,
            )
            if "errors" in response:
                response = cast(Error, response)
                raise UnexpectedResponse(
                    f"Unable to retrieve order status. "
                    f"Error: {response['errors'][0]['code']}."
                )
            else:
                response = cast(OrderStatusResult, response)
        return response["order"]["state"]
