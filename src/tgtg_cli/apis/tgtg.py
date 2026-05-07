import base64
import json
import re
from time import sleep, time
from uuid import uuid4

import requests
from bs4 import BeautifulSoup

from tgtg_cli.apis.base import BaseClient
from tgtg_cli.cli.config import Config
from tgtg_cli.cli.types import (
    AuthByEmailResult,
    AuthByRequestPinResult,
    CancelOrderResult,
    CreateOrderResult,
    DatadomeCaptchaResult,
    DatadomeCookieResult,
    DietCategory,
    Error,
    ItemCategory,
    ItemResult,
    ItemsResult,
    OrdersActiveResult,
    OrderStatusResult,
    PaymentAdditionalAuthorizationResult,
    PaymentResult,
    PayOrderResult,
    RefreshTokenResult,
    SortOption,
)
from tgtg_cli.utils.captcha import solve_datadome
from tgtg_cli.utils.exceptions import (
    AuthorizationError,
    InvalidSession,
    TooManyRequests,
    UnexpectedResponse,
)
from tgtg_cli.utils.models import SessionTokens

TGTG_URL = "https://api.toogoodtogo.com/api/"
DATADOME_SDK_URL = "https://api-sdk.datadome.co/sdk/"
DATADOME_TGTG_KEY = "1D42C2CA6131C526E09F294FE96F94"

THREE_DS2_SDK_VERSION = "2.2.26"


class Endpoints:
    AUTH_BY_EMAIL = TGTG_URL + "auth/v5/authByEmail"
    AUTH_BY_REQUEST_PIN = TGTG_URL + "auth/v5/authByRequestPin"
    AUTH_BY_REQUEST_POLLING_ID = TGTG_URL + "auth/v5/authByRequestPollingId"
    ITEM = TGTG_URL + "item/v8/{item_id}"
    ITEMS = TGTG_URL + "item/v8"
    ON_STARTUP = TGTG_URL + "app/v1/onStartup"
    ORDER_CREATE = TGTG_URL + "order/v8/create/{item_id}"
    ORDER_CANCEL = TGTG_URL + "order/v8/{order_id}/cancel"
    ORDER_PAY = TGTG_URL + "order/v8/{order_id}/pay"
    ORDER_STATUS = TGTG_URL + "order/v8/{order_id}"
    ORDERS_ACTIVE = TGTG_URL + "order/v8/active"
    PAYMENT = TGTG_URL + "payment/v4/{payment_id}"
    PAYMENT_ADDITIONAL_AUTHORIZATION = (
        TGTG_URL + "payment/v4/{payment_id}/additionalAuthorization"
    )
    REFRESH_TOKEN = TGTG_URL + "token/v1/refresh"


class TGTG(BaseClient):
    def __init__(self, config: Config):
        self._config = config

        # Configure session
        self.user_agent = (
            f"TGTG/{self._get_latest_app_version()} Dalvik/2.1.0 "
            f"(Linux; U; Android {self._config.device.android_version}; "
            f"{self._config.device.model} "
            f"Build/{self._config.device.build_number})"
        )
        super().__init__(
            config=self._config,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Correlation-ID": str(uuid4()),
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Language": "en-GB",
                "Accept-Encoding": "gzip, deflate, br",
            },
            proxy=self._config.settings.account.proxy,
        )

        # Add Authorization header if cached session tokens are available
        self.tokens = self._config.get_session_tokens()

    @property
    def tokens(self) -> SessionTokens | None:
        return self._tokens

    @tokens.setter
    def tokens(self, tokens: SessionTokens | None) -> None:
        """
        Updates the session tokens and the Authorization header of the current
        session.

        Args:
            tokens (SessionTokens | None): Session tokens to set. If None, the
                                           Authorization header will be removed
                                           which essentially logs out the user.
        """
        self._tokens = tokens
        if tokens:
            self._set_bearer_token(access_token=tokens.access_token)
        else:
            self.session.headers.pop("Authorization", None)

    def _get_latest_app_version(self) -> str:
        """
        Fetches the latest app version from the Google Play Store. If an error
        occurs APK Mirror is used as a backup source.

        Raises:
            UnexpectedResponse: If the latest app version could not be found.

        Returns:
            str: Latest app version.
        """
        # Search pattern for: XX.X/XX.X/XX, e.g. 26.4.1, 26.2.10 or 25.12.3
        search_pattern = r"\b\d{2}\.\d{1,2}\.\d{1,2}\b"

        # Google Play Store
        response = requests.get(
            url="https://play.google.com/store/apps/details",
            params={
                "id": "com.app.tgtg",
                "hl": "de",
            },
            timeout=10,
        )
        soup = BeautifulSoup(response.text, "html.parser")
        script_section = soup.find(attrs={"class": "ds:5"})
        match = re.search(
            search_pattern,
            script_section.get_text() if script_section else "",
        )
        if match:
            return match.group(0)

        # Backup: APK Mirror
        response = requests.get(
            url=(
                "https://www.apkmirror.com/apk/too-good-to-go-aps/"
                "too-good-to-go-fight-food-waste-save-great-food/"
            ),
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        soup = BeautifulSoup(response.text, "html.parser")
        last_version_section = soup.find("a", class_="fontBlack")
        match = re.search(
            search_pattern,
            last_version_section.get_text() if last_version_section else "",
        )
        if match:
            return match.group(0)
        else:
            raise UnexpectedResponse("Failed to get the latest APK version.")

    def _handle_internal_errors(
        self,
        request: requests.PreparedRequest,
        response: requests.Response,
    ) -> tuple[bool, requests.Response | None]:
        """
        Implementation of the _handle_internal_errors method of the BaseClient
        for TGTG-specific errors.

        This includes handling of invalid JWT tokens and Datadome captchas. If
        the usage of CapSolver is enabled in the settings and a captcha is
        triggered on login, the captcha is solved and the request is retried.
        However, CapSolver won't be used for any other requests to prevent
        unnecessary solves, e.g. when monitoring with a low delay that triggers
        a captcha.

        Args:
            request (requests.PreparedRequest): Request that triggered an
                                                error.
            response (requests.Response): Response of the request that
                                          triggered an error.

        Raises:
            InvalidSession: If the session tokens are invalid and cannot be
                            refreshed.
            AuthorizationError: If captcha solving with CapSolvers succeeds
                                but access remains blocked.
            TooManyRequests: If all retry attempts result 429 status codes.
                             This means that the IP has been blocked
                             temporarily for sending too many requests.

        Returns:
            tuple[bool, requests.Response | None]: Tuple indicating whether an
                                                   UnexpectedResponse should be
                                                   raised to exit the program
                                                   and the last response of all
                                                   retry attempts.
        """
        # TODO: diese Klasse eher in Service Klasse verschieben und dann
        #       übergeben? (z.B. client.py in cli/??)

        # API errors
        if response.status_code == 401:
            # Additional check to prevent infinite loops
            # For invalid JWT tokens, the refresh method is called, which could
            # result in more 401 errors, thus creating an infinite loop
            if self.quit_on_failed_retry:
                if (
                    response.url == Endpoints.REFRESH_TOKEN
                    and "UNAUTHORIZED" in response.text
                ):
                    raise InvalidSession("Unable to refresh session.")
                return True, None
            else:
                try:
                    error = response.json()

                    # Expired / Invalid JWT Token
                    # Example response: {"errors":[{"code":"UNAUTHORIZED",
                    # "message":"Could not authenticate JwtToken(
                    # principal=null, type=ACCESS,
                    # requestAudit=Optional[RequestAudit[clientIp=<redacted>,
                    # clientUserAgent=<redacted>]]) because: Invalid token
                    # for: AuthTokenRequest(tokenType=ACCESS,
                    # clientIp=<redacted>, clientUserAgent=<redacted>"}]}
                    if (
                        error["errors"][0]["code"] == "UNAUTHORIZED" and
                        error["errors"][0]["message"].startswith(
                            "Could not authenticate JwtToken"
                        )
                    ):
                        self.quit_on_failed_retry = True

                        # Refresh and update tokens of current session
                        if self.tokens:
                            tokens = self.refresh_tokens(
                                refresh_token=self.tokens.refresh_token
                            )
                            self.tokens = SessionTokens.from_api(tokens)

                            # Save new tokens to cache
                            self._config.save_session(tokens=self.tokens)

                        # Resend failed request
                        self._update_prepared_request(request)
                        response = self.session.send(request)
                        if response.status_code in (
                            requests.codes.OK,
                            requests.codes.CREATED,
                            requests.codes.ACCEPTED,
                            requests.codes.NO_CONTENT,
                        ):
                            return False, response
                        else:
                            return True, response

                    # Other unexpected errors
                    else:
                        return True, None

                # All errors that occur during retry attempts of methods called
                # from within this function, that raise another exception need
                # to be handled here.
                #
                # Example: If response.status_code == 401 and not
                #          self.quit_on_failed_retry, then refresh_token() is
                #          called. Before calling this method we are setting
                #          self.quit_on_failed_retry to True to prevent
                #          infinite loops. However, if another 401 occurs and
                #          we are still receiving an "AUTHORIZED" error, the
                #          error handler raises an InvalidSession exception to
                #          indicate that the session is no longer valid and the
                #          cache needs to be reset.
                #          If the InvalidSession wouldn't be caught here, it
                #          would only be caught as a general Exception. This
                #          would make it impossible to handle InvalidSession at
                #          a higher level (e.g. run_safely() in executor.py).
                except (AuthorizationError, InvalidSession):
                    raise
                except Exception:
                    return True, None

        # Captcha triggered, e.g. by too many requests wth low delays
        elif (
            response.status_code == 403
            and "geo.captcha-delivery.com" in response.text
        ):
            # 1. Try: Hardcoded delay
            sleep(1)
            response = self.session.send(request)

            # 2. Try: Requesting Datadome cookie from Datadome SDK API
            if response.status_code == 403 and request.url:
                datadome_cookie_result = self._get_datadome_cookie(
                    tgtg_url=request.url
                )
                datadome_cookie = datadome_cookie_result.get("cookie")
                if datadome_cookie:
                    cookie_attributes = [
                        value.split("=")[-1]
                        for value in datadome_cookie.split("; ")
                    ]
                    self.session.cookies.set(
                        name="datadome",
                        value=str(cookie_attributes[0]),
                        domain=".toogoodtogo.com",
                        path="/",
                        secure=True,
                    )
                    self._update_prepared_request(request)
                    response = self.session.send(request)

            # 3. Try: Solve the Datadome captcha using CapSolver
            # IMPORTANT: This should only be done at login to prevent high
            # amounts of solves (e.g. when monitoring with low delays).
            # IMPORTANT: This check raises an AuthorizationError if the
            # received Datadome cookie does not work.
            capsolver_api_key = self._config.settings.solver.capsolver_api_key
            proxy = self._config.settings.account.proxy
            if (
                response.status_code == 403
                and response.url == Endpoints.AUTH_BY_EMAIL
                and capsolver_api_key
                and proxy
            ):
                captcha_url = response.json()["url"]
                captcha_solution = solve_datadome(
                    capsolver_api_key=capsolver_api_key,
                    website_url=Endpoints.AUTH_BY_EMAIL,
                    captcha_url=captcha_url,
                    proxy=proxy,
                )
                self.session.cookies.set(
                    name="datadome",
                    value="".join(captcha_solution["cookie"].split("=")[1:]),
                    domain=".toogoodtogo.com",
                    path="/",
                    secure=True,
                )
                self._update_prepared_request(request)
                response = self.session.send(request)
                if response.status_code == 403:
                    raise AuthorizationError(
                        "Failed to solve the Datadome captcha using CapSolver."
                        " Please try again later."
                    )

            # Check if retry was successful
            if response.status_code in (
                requests.codes.OK,
                requests.codes.CREATED,
                requests.codes.ACCEPTED,
                requests.codes.NO_CONTENT,
            ):
                return False, response

            # Handle block after too many failed login attempts
            elif (
                response.status_code == 403
                and request.url == Endpoints.REFRESH_TOKEN
                and "geo.captcha-delivery.com" in response.text
            ):
                raise AuthorizationError(
                    "Too many failed login attempts. Please try again later."
                )

            # Handle 'Too Many Requests' errors
            # This can happen if the monitoring delay is too low and requesting
            # a new Datadome cookie doesn't lift this ban
            elif (
                response.status_code == 403
                and "geo.captcha-delivery.com" in response.text
            ):
                raise TooManyRequests()

            else:
                return True, response

        return False, None

    def _get_datadome_cookie(self, tgtg_url: str) -> DatadomeCookieResult:
        """
        Requests the Datadome cookie from the Datadome SDK API.

        Args:
            tgtg_url (str): URL of the TGTG API request that triggered the
                            captcha.

        Returns:
            DatadomeCookieResult: Result of the request. Contains the status
                                  code and the Datadome cookie if successful.
        """
        response = self._post(
            url=DATADOME_SDK_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "api-sdk.datadome.co",
                "Connection": "Keep-Alive",
                "User-Agent": "okhttp/5.1.0",
                "Accept-Encoding": "gzip",
            },
            data={
                "ddk": DATADOME_TGTG_KEY,
                "request": tgtg_url,
            },
            use_session_headers=False,
        )
        return response.json()

    def _set_bearer_token(self, access_token: str) -> None:
        """
        Sets the Authorization header for the current session.

        Args:
            access_token (str): Access token to use for authentication.
        """
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
            }
        )

    def refresh_tokens(self, refresh_token: str) -> RefreshTokenResult:
        """
        Refreshes the session tokens.
        A refresh is required if the access tokens ttl has expired. If no
        tokens are set the method returns without doing anything.

        Args:
            refresh_token (str): Refresh token to use.

        Returns:
            RefreshTokenResult: New session tokens.
        """
        data = {"refresh_token": refresh_token}
        response = self._post(url=Endpoints.REFRESH_TOKEN, json=data)
        return response.json()

    def on_startup(self) -> int:
        """
        Sends a request to the onStartup endpoint.
        This method can be used to validate if the authorization token is still
        valid. It should only be called for logged in users.

        Returns:
            int: Status code of the response
        """
        response = self._post(url=Endpoints.ON_STARTUP)
        return response.status_code

    def initiate_login(
        self,
        device_type: str,
        email: str,
    ) -> AuthByEmailResult | DatadomeCaptchaResult:
        """
        Initiates the login process by requesting an email verification code.

        Returns:
            AuthByEmailResult | DatadomeCaptchaResult: Result of the request
                                                       containing either the
                                                       polling_id or the url
                                                       of the Datadome captcha.
        """
        data = {
            "device_type": device_type,
            "email": email,
        }
        response = self._post(url=Endpoints.AUTH_BY_EMAIL, json=data)
        return response.json()

    def complete_login(
        self,
        device_type: str,
        email: str,
        code: str,
        polling_id: str,
    ) -> AuthByRequestPinResult:
        """
        Completes a pending login process by submitting the email verification
        code. Updates all token attributes and the session headers.

        Args:
            device_type (str): Device type to use for the login.
            email (str): Email address of the user to login with.
            code (str): Email verification code.
            polling_id (str): Polling ID of the email verification request.

        Returns:
            AuthByRequestPinResult: Session tokens for the logged in user.
        """
        data = {
            "device_type": device_type,
            "email": email,
            "request_pin": code,
            "request_polling_id": polling_id,
        }
        response = self._post(url=Endpoints.AUTH_BY_REQUEST_PIN, json=data)
        return response.json()

    def get_item(
        self,
        latitude: float,
        longitude: float,
        item_id: str,
    ) -> ItemResult:
        """
        Retrieves detailed information for a specific item.

        Args:
            latitude (float): Latitude used as search origin.
            longitude (float): Longitude used as search origin.
            item_id (str): ID of the item to look up.

        Returns:
            ItemResult: Response with item details.
        """
        data = {
            "origin": {
                "latitude": latitude,
                "longitude": longitude,
            }
        }
        response = self._post(
            url=Endpoints.ITEM.format(item_id=item_id),
            json=data,
        )
        return response.json()

    def get_items(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        page_size: int = 20,
        page: int = 1,
        discover: bool = False,
        favorites_only: bool = False,
        item_categories: list[ItemCategory] | None = None,
        diet_categories: list[DietCategory] | None = None,
        pickup_intervals: list | None = None,
        search_phrase: str | None = None,
        with_stock_only: bool = False,
        hidden_only: bool = False,
        sort_option: SortOption = "RELEVANCE",
        expand_radius_if_not_enough_items: bool = False,
    ) -> ItemsResult:
        """
        Retrieves items for within a given radius from a given location. Allows
        configuration of various filters and sorting options.

        Args:
            latitude (float): Latitude used as search origin.
            longitude (float): Longitude used as search origin.
            radius (int): Search radius in kilometers.
            page_size (int, optional): Number of items per page. Do NOT change
                                       this value. As of now it doesn't seems
                                       to work and will only lead to duplicates
                                       or missing items in the search results.
                                       Defaults to 20.
            page (int, optional): Page number to request. Defaults to 1.
            discover (bool, optional): If discover mode should be enabled.
                                       Defaults to False.
            favorites_only (bool, optional): If only favorites should be
                                             returned.
                                             Defaults to False.
            item_categories (list[ItemCategory] | None, optional): Specific
                                                                   item
                                                                   categories
                                                                   to filter
                                                                   for.
                                                                   Defaults to
                                                                   None.
            diet_categories (list[DietCategory] | None, optional): Specific
                                                                   diet
                                                                   categories
                                                                   to filter
                                                                   for.
                                                                   Defaults to
                                                                   None.
            pickup_intervals (list | None, optional): Specific pickup intervals
                                                      to filter for.
                                                      Defaults to None.
            search_phrase (str | None, optional): Search query to use.
                                                  Defaults to None.
            with_stock_only (bool, optional): If only in-stock items should be
                                              returned.
                                              Defaults to False.
            hidden_only (bool, optional): If only hidden items should be
                                          returned.
                                          Defaults to False.
            sort_option (SortOption, optional): Sort mode for the results.
                                                Defaults to "RELEVANCE".
            expand_radius_if_not_enough_items (bool, optional): If the radius
                                                                may be expanded
                                                                by the AP if no
                                                                items were
                                                                found.
                                                                Defaults to
                                                                False.

        Returns:
            ItemsResult: Paginated item search result.
        """
        item_categories = [] if item_categories is None else item_categories
        diet_categories = [] if diet_categories is None else diet_categories
        data = {
            "origin": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "radius": radius,
            "page_size": page_size,
            "page": page,
            "discover": discover,
            "favorites_only": favorites_only,
            "item_categories": item_categories,
            "diet_categories": diet_categories,
            "with_stock_only": with_stock_only,
            "hidden_only": hidden_only,
            "sort_option": sort_option,
            "expand_radius_if_not_enough_items": (
                expand_radius_if_not_enough_items
            ),
        }

        # Add optional arguments if provided
        if pickup_intervals:
            data["pickup_intervals"] = pickup_intervals
        if search_phrase:
            data["search_phrase"] = search_phrase

        response = self._post(url=Endpoints.ITEMS, json=data)
        return response.json()

    def create_order(self, item_id: str, count: int = 1) -> CreateOrderResult:
        """
        Creates a new order reservation for an item.

        Args:
            item_id (str): Item ID to reserve.
            count (int, optional): Number of item units to reserve.
                                   Defaults to 1.

        Returns:
            CreateOrderResult: Details of the created order.
        """
        data = {"item_count": count}
        response = self._post(
            url=Endpoints.ORDER_CREATE.format(item_id=item_id),
            json=data,
        )
        return response.json()

    def pay_order(
        self,
        checkout_attempt_id: str,
        encrypted_card_number: str,
        encrypted_expiry_month: str,
        encrypted_expiry_year: str,
        encrypted_security_code: str,
        brand: str,
        code: str,
        decimals: int,
        minor_units: int,
        order_id: str,
    ) -> PayOrderResult:
        """
        Initiates the payment process for an order.

        Args:
            checkout_attempt_id (str): ID of the checkout attempt.
            encrypted_card_number (str): Encrypted card number.
            encrypted_expiry_month (str): Encrypted expiry month.
            encrypted_expiry_year (str): Encrypted expiry year.
            encrypted_security_code (str): Encrypted security code.
            brand (str): Brand of the card.
            code (str): 3-letter ISO 4217 currency code.
            decimals (int): Number of decimal places in the minor unit.
            minor_units (int): Payment amount in minor units.
            order_id (str): ID of the order.

        Returns:
            PayOrderResult: Details of the initiated payment.
        """
        sdk_data_dict = {
            "schemaVersion": 1,
            "analytics": {"checkoutAttemptId": checkout_attempt_id},
            "authentication": {"threeDS2SdkVersion": THREE_DS2_SDK_VERSION},
            "createdAt": int(time() * 1000),
            "supportNativeRedirect": True,
        }
        sdk_data = base64.b64encode(
            json.dumps(sdk_data_dict, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")
        inner_payload = {
            "type": "scheme",
            "checkoutAttemptId": checkout_attempt_id,
            "sdkData": sdk_data,
            "encryptedCardNumber": encrypted_card_number,
            "encryptedExpiryMonth": encrypted_expiry_month,
            "encryptedExpiryYear": encrypted_expiry_year,
            "encryptedSecurityCode": encrypted_security_code,
            "brand": brand,
            "threeDS2SdkVersion": THREE_DS2_SDK_VERSION,
        }
        data = {
            "authorizations": [
                {
                    "authorization_payload": {
                        "save_payment_method": False,
                        "payment_type": "CREDITCARD",
                        "type": "adyenAuthorizationPayload",
                        "payload": json.dumps(inner_payload),
                    },
                    "payment_provider": "ADYEN",
                    "return_url": "adyencheckout://com.app.tgtg.itemview",
                    "amount": {
                        "code": code,
                        "decimals": decimals,
                        "minor_units": minor_units,
                    },
                }
            ]
        }
        response = self._post(
            url=Endpoints.ORDER_PAY.format(order_id=order_id),
            json=data,
        )
        return response.json()

    def cancel_order(self, order_id: str) -> CancelOrderResult:
        """
        Cancels an active order.

        Args:
            order_id (str): ID of the order to cancel.

        Returns:
            CancelOrderResult: Details of the cancelled order.
        """
        data = {"cancel_reason_id": "1"}
        response = self._post(
            url=Endpoints.ORDER_CANCEL.format(order_id=order_id),
            json=data,
        )
        return response.json()

    def get_order_status(self, order_id: str) -> OrderStatusResult | Error:
        """
        Retrieves the current status of an order.

        Args:
            order_id (str): ID of the order to inspect.

        Returns:
            OrderStatusResult | Error: Current order status or a generic error
                                       response.
        """
        response = self._post(
            url=Endpoints.ORDER_STATUS.format(order_id=order_id),
        )
        return response.json()

    def get_active_orders(self) -> OrdersActiveResult:
        """
        Retrieves all active orders for the current user.

        Returns:
            OrdersActiveResult: Active orders in the user's account.
        """
        response = self._post(
            url=Endpoints.ORDERS_ACTIVE,
        )
        return response.json()

    def get_payment_status(self, payment_id: str) -> PaymentResult:
        """
        Retrieves the current status of a payment.

        Args:
            payment_id (str): ID of the payment to inspect.

        Returns:
            PaymentResult: Details of the payment.
        """
        response = self._post(
            url=Endpoints.PAYMENT.format(payment_id=payment_id),
        )
        return response.json()

    def submit_additional_authorization(
        self,
        payment_id: str,
        authorisation_token: str,
    ) -> PaymentAdditionalAuthorizationResult:
        """
        Submits additional 3DS authorization data for a payment. This notifies
        the server that the payment has been completed.

        Args:
            payment_id (str): ID of the payment.
            authorisation_token (str): Authorisation token of the completed
                                       payment.

        Returns:
            PaymentAdditionalAuthorizationResult: Response of the additional
                                                  authorization submission.
        """
        three_ds_result = {
            "transStatus": "Y",
            "authorisationToken": authorisation_token,
        }
        data = {
            "payment_provider": "ADYEN",
            "payload": {
                "save_payment_method": True,
                "type": "adyenAdditionalAuthorizationPayload",
                "details_payload": json.dumps(
                    {
                        "threeDSResult": base64.b64encode(
                            json.dumps(
                                three_ds_result,
                                separators=(",", ":"),
                                ensure_ascii=False,
                            ).encode()
                        ).decode()
                    }
                ),
            },
        }
        response = self._post(
            url=Endpoints.PAYMENT_ADDITIONAL_AUTHORIZATION.format(
                payment_id=payment_id
            ),
            json=data,
        )
        return response.json()


# TODO: API Schicht so umstellen, dass die volle Response zurückgesendet wird!
#       Alles andere dann im Service machen!
