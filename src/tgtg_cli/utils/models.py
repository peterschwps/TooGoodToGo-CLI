from dataclasses import dataclass
from enum import StrEnum
from time import time
from typing import Literal

from tgtg_cli.cli.types import AuthByRequestPinResult, RefreshTokenResult


@dataclass
class Device:
    brand: str
    model: str
    android_version: str
    system_version: str
    build_number: str
    screen_width: int


@dataclass
class SessionTokens:
    access_token: str
    refresh_token: str
    access_token_timestamp: int
    access_token_ttl_seconds: int

    @classmethod
    def from_api(
        cls,
        response: AuthByRequestPinResult | RefreshTokenResult,
    ) -> "SessionTokens":
        """
        Builds a SessionTokens instance from a TGTG API response.

        Args:
            response: An API response dict containing all token fields. This
                      can be from the login process (AuthByRequestPinResult)
                      or from refreshing the token (RefreshTokenResult).

        Returns:
            SessionTokens: New SessionTokens instance with the current
                           timestamp.
        """
        return cls(
            access_token=response["access_token"],
            refresh_token=response["refresh_token"],
            access_token_timestamp=int(time()),
            access_token_ttl_seconds=response["access_token_ttl_seconds"],
        )


@dataclass
class ItemOverview:
    id: str
    name: str
    price: float
    currency_code: str
    items_available: int


@dataclass
class OrderDetails:
    id: str
    quantity: int
    code: str
    minor_units: int
    decimals: int


@dataclass
class PaymentDetails:
    encrypted_card_number: str
    encrypted_expiry_month: str
    encrypted_expiry_year: str
    encrypted_security_code: str
    credit_card_brand: str


@dataclass
class ThreeDS2Details:
    fingerprint_result: str
    payment_data: str
    authorisation_token: str | None = None
    token: str | None = None


@dataclass
class Bunq:
    polling_url: str


@dataclass
class DKB:
    polling_url: str
    session_id: str
    request_id: str


type Issuer = Bunq | DKB


@dataclass
class RedirectDetails:
    issuer: Issuer
    md: str
    pa_req: str
    psp_reference: str
    origin_key: str
    return_url: str


@dataclass
class AdditionalAuthorizationDetailsRedirect:
    url: str


@dataclass
class AdditionalAuthorizationDetailsThreeDS2:
    payment_data: str
    token: str


type AdditionalAuthorizationDetails = (
    AdditionalAuthorizationDetailsRedirect |
    AdditionalAuthorizationDetailsThreeDS2
)


class CheckoutState(StrEnum):
    ABORTED = "ABORTED"
    ADDITIONAL_AUTHORIZATION_INITIATED = "ADDITIONAL_AUTHORIZATION_INITIATED"
    ADDITIONAL_AUTHORIZATION_REQUIRED = "ADDITIONAL_AUTHORIZATION_REQUIRED"
    AUTHORIZATION_INITIATED = "AUTHORIZATION_INITIATED"
    AUTHORIZED = "AUTHORIZED"
    FAILED = "FAILED"


@dataclass
class CheckoutDetails:
    checkout_attempt_id: str
    payment_id: str | None = None
    state: CheckoutState | None = None
    additional_authorization_details: \
        AdditionalAuthorizationDetails | None = None
    redirect_details: RedirectDetails | None = None
    three_ds2_details: ThreeDS2Details | None = None
    needs_3ds2: bool = False


@dataclass
class ThreeDS2Status:
    status: Literal["completed", "awaiting_confirmation", "awaiting_selection"]
    challenge_info_label: str | None = None
    challenge_info_text: str | None = None
    challenge_select_info: list[dict[str, str]] | None = None
