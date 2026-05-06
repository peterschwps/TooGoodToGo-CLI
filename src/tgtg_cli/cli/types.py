from typing import Any, Literal, NotRequired, Required, TypedDict

# ===== Internal Types =====


# ===== Adyen API Types =====
# /checkoutshopper/v1/submitThreeDS2Fingerprint?token={client_key}
class AdyenAction(TypedDict):
    authorisationToken: str
    subtype: str
    token: str
    type: str


class AdyenDetails(TypedDict):
    threeDSResult: str


class ThreeDS2FingerprintResultAction(TypedDict):
    action: AdyenAction  # if 3DS is required
    type: str


class ThreeDS2FingerprintResultCompleted(TypedDict):
    details: AdyenDetails  # if 3DS is not required
    type: str


# /checkoutshopper/v2/bin/binLookup?clientKey={client_key}
class Brand(TypedDict):
    brand: str
    cvcPolicy: str
    enableLuhnCheck: bool
    expiryDatePolicy: str
    localeBrand: str
    paymentMethodVariant: str
    showExpiryDate: bool
    showSocialSecurityNumber: bool
    supported: bool


class BinLookupResult(TypedDict):
    brands: list[Brand]
    issuingCountryCode: str
    requestId: str


# ===== Datadome API Types =====
class DatadomeCookieResult(TypedDict):
    status: int
    cookie: NotRequired[str]


# ===== TGTG API Types =====
# Shared Types
class Error(TypedDict):
    errors: list[dict[str, str]]

class Country(TypedDict):
    iso_code: str
    name: str


class Address(TypedDict):
    country: Country
    address_line: str
    city: str
    postal_code: str


class Location(TypedDict):
    longitude: float
    latitude: float


class PickupLocation(TypedDict):
    address: Address
    location: Location


class PickupInterval(TypedDict):
    start: str
    end: str


class Price(TypedDict):
    code: str
    minor_units: int
    decimals: int


class Picture(TypedDict):
    picture_id: str
    current_url: str
    is_automatically_created: bool


class SessionTokens(TypedDict):
    access_token: str
    access_token_ttl_seconds: int
    refresh_token: str


# Filter Options
DietCategory = Literal[
    "VEGAN",
    "VEGETARIAN",
]

ItemCategory = Literal[
    "OTHER",
    "GROCERIES",
    "PET_FOOD",
    "BAKED_GOODS",
    "MEAL",
    "FLOWERS_PLANTS",
]

SortOption = Literal[
    "RELEVANCE",
    "DISTANCE",
    "PRICE",
    "RATING",
]

# /auth/v5/authByEmail
type ResponseStatusCode = int


class AuthByEmailResult(TypedDict):
    state: str
    polling_id: str


class DatadomeCaptchaResult(TypedDict):
    url: str


# /auth/v5/authByRequestPin
type AuthByRequestPinResult = SessionTokens


# /item/v8
class AverageOverallRating(TypedDict):
    average_overall_rating: float
    rating_count: int
    month_count: int
    average_collection_experience_rating: float
    average_food_quality_rating: float
    average_contents_variety_rating: float
    average_food_quantity_rating: float


class ItemDetails(TypedDict):
    item_id: str
    item_price: Price
    item_value: Price
    cover_picture: Picture
    logo_picture: Picture
    name: str
    description: str
    subtitle: str
    food_handling_instructions: str
    can_user_supply_packaging: bool
    packaging_option: str
    collection_info: str
    diet_categories: list[DietCategory]
    item_category: ItemCategory
    buffet: bool
    positive_rating_reasons: list[str]
    average_overall_rating: NotRequired[AverageOverallRating]
    favorite_count: int


class StoreLocation(TypedDict):
    address: Address
    location: Location


class StoreDetails(TypedDict):
    store_id: str
    store_name: str
    branch: str
    description: str
    tax_identifier: str
    website: str
    store_location: StoreLocation
    logo_picture: Picture
    store_time_zone: str
    hidden: bool
    favorite_count: int
    distance: float
    cover_picture: Picture
    is_manufacturer: bool


class ItemTag(TypedDict):
    id: str
    short_text: str
    long_text: str
    variant: str


class Item(TypedDict):
    item: ItemDetails
    store: StoreDetails
    display_name: str
    pickup_interval: PickupInterval
    pickup_location: PickupLocation
    purchase_end: str
    items_available: int
    distance: float
    favorite: bool
    subscribed_to_notification: bool
    in_sales_window: bool
    new_item: bool
    item_type: str
    matches_filters: bool
    item_tags: list[ItemTag]


class ItemsResult(TypedDict):
    items: list[Item]
    items_expanded_radius: list[Item]


# /item/v8/{item_id}
class IngredientLabel(TypedDict):
    label_name: str
    probability_percentage: float
    image_url: str


class ItemIngredients(TypedDict):
    ingredient_labels: list[IngredientLabel]
    bag_count: int


class ItemResult(TypedDict):
    item: ItemDetails
    store: StoreDetails
    display_name: str
    pickup_interval: PickupInterval
    pickup_location: PickupLocation
    purchase_end: str
    items_available: int
    distance: float
    favorite: bool
    subscribed_to_notification: bool
    in_sales_window: bool
    new_item: bool
    item_type: str
    matches_filters: bool
    item_tags: list[ItemTag]
    item_ingredients: NotRequired[ItemIngredients]


# /order/v8/create/{item_id}
class OrderLine(TypedDict):
    quantity: int
    item_price_including_taxes: Price
    item_price_excluding_taxes: Price
    total_price_including_taxes: Price
    total_price_excluding_taxes: Price
    total_price: Price


class ReservedOrder(TypedDict):
    id: str
    item_id: str
    user_id: str
    state: str
    order_line: OrderLine
    reserved_at: str
    order_type: str
    might_be_eligible_for_reward: bool
    is_multi_item: bool


class CreateOrderResult(TypedDict):
    state: str
    order: ReservedOrder
    item_level_errors: list[Any]


# /order/v8/{order_id}/cancel
class RatingInfo(TypedDict):
    is_rateable: bool


class StoreInfo(TypedDict):
    store_id: str
    store_display_name: str
    country_iso_code: str
    logo_url: str
    store_time_zone: str


class ItemInfo(TypedDict):
    item_id: str
    item_name: str


class PickupWindow(TypedDict):
    start: str
    end: str


class CancelledOrder(TypedDict):
    user_id: str
    order_id: str
    order_state: str
    order_type: str
    rating_info: RatingInfo
    store_info: StoreInfo
    item_info: ItemInfo
    pickup_window: PickupWindow
    is_support_available: bool
    last_updated_at_utc: str
    time_of_purchase_utc: str
    is_multi_item: bool


class CancelOrderResult(TypedDict):
    state: str
    order: CancelledOrder


# /order/v8/{order_id}/pay
class Payment(TypedDict):
    payment_id: str
    order_id: str
    payment_provider: str
    state: str
    user_id: str


class PayOrderResult(TypedDict):
    payments: list[Payment]
    has_multiple_payments: bool


# /order/v8/{order_id}
class RedeemInterval(TypedDict):
    start: str
    end: str


class SalesTax(TypedDict):
    tax_description: str
    tax_percentage: float
    tax_amount: Price


class OrderItem(TypedDict):
    item_id: str
    quantity: int
    item_price: Price
    item_name: str
    item_subtitle: str
    item_cover_image: Picture


class OrderDetails(TypedDict):
    type: str
    order_id: str
    user_id: str
    state: str
    cancel_until: str
    redeem_interval: RedeemInterval
    pickup_interval: PickupInterval
    store_time_zone: str
    quantity: int
    price_including_taxes: Price
    price_excluding_taxes: Price
    total_applied_taxes: Price
    sales_taxes: list[SalesTax]
    total_price: Price
    pickup_location: PickupLocation
    can_be_rated: bool
    is_rated: bool
    should_be_excluded_from_expense_rating: bool
    time_of_purchase: str
    store_id: str
    store_name: str
    store_branch: str
    store_logo: Picture
    order_items: list[OrderItem]
    item_id: str
    item_name: str
    item_category: ItemCategory
    item_cover_image: Picture
    food_handling_instructions: str
    is_buffet: bool
    item_collection_info: str
    can_user_supply_packaging: bool
    packaging_option: str
    pickup_window_changed: bool
    can_show_best_before_explainer: bool
    show_sales_taxes: bool
    order_type: str
    is_support_available: bool
    has_dynamic_price: bool
    is_eligible_for_reward: bool
    last_updated_at_utc: str
    has_multiple_payments: bool
    total_price_paid_with_external_provider: Price
    is_multi_item: bool
    payment_method_display_name: str
    payment_state: NotRequired[str]
    cancelling_entity: NotRequired[str]
    expected_bank_processing_days: NotRequired[int]
    cancelled_or_refunded_at_utc: NotRequired[str]
    is_donation: bool


class OrderStatusResult(TypedDict):
    order: OrderDetails


# /order/v8/active
class OrdersActiveResult(TypedDict):
    current_time: str
    has_more: bool
    orders: list[OrderDetails]


# /payment/v4/{payment_id}
class PaymentResult(TypedDict):
    payment_id: str
    order_id: str
    payment_provider: str
    state: str
    user_id: str
    payload: NotRequired[str]


# /payment/v4/{payment_id}/additionalAuthorization
class PaymentAdditionalAuthorizationResult(PaymentResult):
    payload: Required[str]


# /token/v1/refresh
type RefreshTokenResult = SessionTokens
