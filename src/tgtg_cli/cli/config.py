import configparser
import contextlib
import json
import sys
import webbrowser
from datetime import datetime
from functools import cached_property
from pathlib import Path
from time import sleep
from typing import Self
from urllib.parse import quote

from platformdirs import user_cache_dir, user_config_dir
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_extra_types.payment import PaymentCardBrand, PaymentCardNumber

from tgtg_cli.cli import console
from tgtg_cli.utils.devices import get_random_device
from tgtg_cli.utils.exceptions import SettingsError
from tgtg_cli.utils.models import Device, SessionTokens

PROJECT_NAME = "TGTG-CLI"

SETTINGS_DIR = Path(user_config_dir(PROJECT_NAME, ensure_exists=True))
SETTINGS_FILE_PATH = SETTINGS_DIR / "settings.ini"

CACHE_DIR = Path(user_cache_dir(PROJECT_NAME, ensure_exists=True))
SESSION_FILE_PATH = CACHE_DIR / "session.json"
DEVICE_FILE_PATH = CACHE_DIR / "device.json"

LOG_DIR = Path(CACHE_DIR, "logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = LOG_DIR / "tgtg-cli.log"


DEFAULT_SETTINGS: dict[str, dict[str, str]] = {
    "ACCOUNT": {
        "EMAIL": "",
        "LATITUDE": "55.713",
        "LONGITUDE": "12.569982",
        "RADIUS": "5",
        "PROXY": "",
    },
    "APPLICATION": {
        "ENABLE_LOGGING": "True",
        "ENABLE_CHECKOUT": "False",
    },
    "PAYMENT": {
        "CARD_NUMBER": "",
        "CARD_EXPIRY_MONTH": "",
        "CARD_EXPIRY_YEAR": "",
        "CARD_SECURITY_CODE": "",
    },
    "MONITOR": {
        "DELAY_IN_MILLISECONDS": "4500",
        "NTFY_TOPIC": "",
    },
    "SOLVER": {
        "CAPSOLVER_API_KEY": "",
    },
}


def _convert_empty_string_to_none(value: object) -> object:
    """
    Converts an empty string to None. If the value passed is not an empty 
    string or of a different type, the value is returned unchanged.

    Args:
        value (object): Value to check.

    Returns:
        object: None if an empty string was passed, else the unchanged value.
    """
    if isinstance(value, str) and value.strip() == "":
        return None
    return value   

class AccountSettings(BaseModel):
    email: EmailStr = Field(alias="EMAIL", min_length=5)
    # Hint: Using float instead of Decimal because it can be serialized in 
    #       the JSON payloads. The precision differences are negligible.
    latitude: float = Field(alias="LATITUDE")
    longitude: float = Field(alias="LONGITUDE")
    radius: int = Field(alias="RADIUS", ge=1)
    proxy: str | None = Field(default=None, alias="PROXY")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("latitude")
    @classmethod
    def _validate_latitude_range(cls, value: float) -> float:
        """
        Validates that the latitude is within the valid geographic range.

        Args:
            value (float): Latitude value to validate.

        Raises:
            SettingsError: If the latitude is outside the range -90 to 90.

        Returns:
            float: Validated latitude value.
        """
        if not float(-90) <= value <= float(90):
            raise SettingsError(
                "Invalid latitude. "
                "Latitude must be any decimal number between -90 and 90."
            )
        return value

    @field_validator("longitude")
    @classmethod
    def _validate_longitude_range(cls, value: float) -> float:
        """
        Validates that the longitude is within the valid geographic range.

        Args:
            value (float): Longitude value to validate.

        Raises:
            SettingsError: If the longitude is outside the range -180 to 180.

        Returns:
            float: Validated longitude value.
        """
        if not float(-180) <= value <= float(180):
            raise SettingsError(
                "Invalid longitude. "
                "Longitude must be any decimal number between -180 and 180."
            )
        return value

    @field_validator("proxy", mode="before")
    @classmethod
    def _convert_proxy_to_none_if_empty(cls, value: object) -> object:
        """
        Converts empty proxy strings to None or keeps the value unchanged.

        Args:
            value (object): Proxy string from the settings file.

        Returns:
            object: Converted proxy value or None if the value was empty.
        """
        return _convert_empty_string_to_none(value)

    @field_validator("proxy")
    @classmethod
    def _validate_proxy_format(cls, value: str | None) -> str | None:
        """
        Validates the expected proxy format: username:password@hostname:port.

        Args:
            value (str | None): Proxy to validate. None if no proxy was set.

        Raises:
            SettingsError: If the proxy format is invalid.
            SettingsError: If any parts of the proxy are empty.
            SettingsError: If the port is not numeric.
            SettingsError: If the port is not between 1 and 65535.

        Returns:
            str | None: Validated proxy. None if no proxy was set.
        """
        if value is None:
            return None
        try:
            username_password, hostname_port = value.split("@")
            username, password = username_password.split(":")
            hostname, port = hostname_port.rsplit(":")
        except ValueError as error:
            raise SettingsError(
                "Invalid proxy format. "
                "Format must be: username:password@hostname:port."
            ) from error
            
        for name, part in (
            ("username", username),
            ("password", password),
            ("hostname", hostname),
            ("port", port),
        ):
            if not part:
                raise SettingsError(
                    f"Invalid proxy format. "
                    f"Proxy {name} must not be empty. "
                )
        if not port.isdigit():
            raise SettingsError(
                "Invalid proxy format. "
                "Proxy port must be numeric. "
            )
        else:
            port = int(port)
            if port < 1 or port > 65535:
                raise SettingsError(
                    "Invalid proxy format. "
                    "Proxy port must be between 1 and 65535. "
                )
        return value


class ApplicationSettings(BaseModel):
    enable_logging: bool = Field(default=True, alias="ENABLE_LOGGING")
    enable_checkout: bool = Field(default=False, alias="ENABLE_CHECKOUT")

    model_config = ConfigDict(populate_by_name=True)


class PaymentSettings(BaseModel):
    card_number: PaymentCardNumber | None = Field(
        default=None,
        alias="CARD_NUMBER",
    )
    card_expiry_month: int | None = Field(
        default=None,
        alias="CARD_EXPIRY_MONTH",
    )
    card_expiry_year: int | None = Field(
        default=None,
        alias="CARD_EXPIRY_YEAR",
    )
    card_security_code: str | None = Field(
        default=None,
        alias="CARD_SECURITY_CODE",
    )

    model_config = ConfigDict(populate_by_name=True)

    @cached_property
    def brand(self) -> PaymentCardBrand | None:
        """
        Returns the detected card brand for the configured card number.

        Returns:
            PaymentCardBrand | None: Detected card brand or None if no card
                                     number is set.
        """
        if self.card_number is None:
            return None
        return self.card_number.brand

    @field_validator(
        "card_number",
        "card_expiry_month",
        "card_expiry_year",
        "card_security_code",
        mode="before",
    )
    @classmethod
    def _convert_card_details_to_none_if_empty(cls, value: object) -> object:
        """
        Converts empty strings for payment card values to None or keeps the
        value unchanged.

        Args:
            value (object): Payment card value from the settings file.

        Returns:
            object: Converted payment value or None if the value was empty.
        """
        return _convert_empty_string_to_none(value)

    @field_validator("card_expiry_month")
    @classmethod
    def _validate_expiry_month(cls, value: int | None) -> int | None:
        """
        Validates the credit card's expiry month.

        Args:
            value (int | None): Expiry month to validate.

        Raises:
            SettingsError: If the month is outside 1-12.
            SettingsError: If the month contains non-numeric characters.

        Returns:
            int | None: Validated expiry month or None if no month was set.
        """
        if value is None:
            return None
        elif not 1 <= value <= 12:
            raise SettingsError(
                "Invalid card expiry month. Month must be between 1 and 12."
            )
        elif not str(value).isdigit():
            raise SettingsError(
                "Invalid card expiry month. "
                "Month must contain only digits."
            )
        else:
            return value

    @field_validator("card_expiry_year")
    @classmethod
    def _validate_expiry_year(cls, value: int | None) -> int | None:
        """
        Validates the credit card's expiry year.

        Args:
            value (int | None): Expiry year to validate.

        Raises:
            SettingsError: If the year format is invalid.
            SettingsError: If the year contains non-numeric characters.
            SettingsError: If the year is outside the allowed range.

        Returns:
            int | None: Validated expiry year or None if no year was set.
        """
        if value is None:
            return None
        elif len(str(value)) != 4:
            raise SettingsError(
                "Invalid card expiry year. Expected format: YYYY."
            )
        elif not str(value).isdigit():
            raise SettingsError(
                "Invalid card expiry year. "
                "Year must contain only digits."
            )
        else:
            current_year = datetime.now().year
            if not current_year <= value <= current_year + 5:
                raise SettingsError(
                    f"Invalid expiry year. Year must be between {current_year}"
                    f" and {current_year + 5}."
                )
            else:
                return value

    @field_validator("card_security_code")
    @classmethod
    def _validate_security_code(cls, value: str | None) -> str | None:
        """
        Validates the credit card's security code.

        Args:
            value (str | None): Security code to validate.

        Raises:
            SettingsError: If the security code has non-numeric characters.
            SettingsError: If the security code is not 3 or 4 digits long.

        Returns:
            str | None: Validated security code or None if no code was set.
        """
        if value is None:
            return None
        elif not value.isdigit():
            raise SettingsError(
                "Invalid card security code. "
                "Security code must contain only digits."
            )
        elif len(value) not in (3, 4):
            raise SettingsError(
                "Invalid card security code. "
                "Security code must be either 3 or 4 digits."
            )
        else:
            return value


class MonitorSettings(BaseModel):
    delay_in_milliseconds: int = Field(alias="DELAY_IN_MILLISECONDS", gt=0)
    ntfy_topic: str = Field(alias="NTFY_TOPIC", min_length=1)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("delay_in_milliseconds")
    @classmethod
    def _validate_delay_in_milliseconds(cls, value: str | None) -> str | None:
        """
        Checks if a low delay is correctly set. Warns the user about potential
        rate limiting if the delay is low.

        Args:
            value (str | None): Delay in milliseconds.

        Raises:
            SettingsError: If delay is not a positive number.

        Returns:
            str | None: Delay in milliseconds.
        """
        if value is not None and str(value).isdigit():
            delay = int(value)
            if delay < 4500:
                console.warning(f"Current delay: {delay}ms.")
                console.warning(
                    "Please note that a lower delay might lead to rate "
                    "limiting if you are running for a longer time!"
                )
                sleep(4)
                console.clear()
        return value


class SolverSettings(BaseModel):
    capsolver_api_key: str | None = Field(
        default=None,
        alias="CAPSOLVER_API_KEY",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("capsolver_api_key", mode="before")
    @classmethod
    def _convert_capsolver_api_key_to_empty_if_none(
        cls,
        value: object,
    ) -> object:
        """
        Converts empty CapSolver API key strings to None or keeps the value
        unchanged.

        Args:
            value (object): CapSolver API key string from the settings file.

        Returns:
            object: Converted CapSolver API key string or None if the value was
                    empty.
        """
        return _convert_empty_string_to_none(value)


class SettingsModel(BaseModel):
    account: AccountSettings = Field(alias="ACCOUNT")
    application: ApplicationSettings = Field(alias="APPLICATION")
    payment: PaymentSettings = Field(alias="PAYMENT")
    monitor: MonitorSettings = Field(alias="MONITOR")
    solver: SolverSettings = Field(alias="SOLVER")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate_checkout_dependency(self) -> Self:
        """
        Validates the checkout dependencies. If checkout is enabled, all card
        details must be provided. 

        Raises:
            SettingsError: If checkout is enabled but card details are missing.

        Returns:
            Self: SettingsModel object.
        """
        if not self.application.enable_checkout:
            return self
        else:
            payment = self.payment
            missing = []
            for name, value in (
                ("CARD_NUMBER", payment.card_number),
                ("CARD_EXPIRY_MONTH", payment.card_expiry_month),
                ("CARD_EXPIRY_YEAR", payment.card_expiry_year),
                ("CARD_SECURITY_CODE", payment.card_security_code),
            ):
                if value is None:
                    missing.append(name)
            if missing:
                raise SettingsError(
                    f"Invalid application configuration. "
                    f"Checkout is enabled, but the following payment details "
                    f"are missing: {', '.join(missing)}."
                )
            else:
                return self

    @model_validator(mode="after")
    def _validate_proxy_set_if_capsolver_api_key_provided(
        self,
    ) -> Self:
        """
        Validates that a proxy is configured when CapSolver is enabled.

        Raises:
            SettingsError: If a CapSolver API key is set without a proxy.

        Returns:
            Self: SettingsModel object.
        """
        if self.solver.capsolver_api_key and not self.account.proxy:
            raise SettingsError(
                "Invalid CapSolver configuration. "
                "Proxy must be set when a CapSolver API key is "
                "provided."
            )
        return self


class SessionModel(BaseModel):
    access_token: str = Field(
        default="",
        alias="ACCESS_TOKEN",
    )
    refresh_token: str = Field(
        default="",
        alias="REFRESH_TOKEN",
    )
    access_token_timestamp: int = Field(
        default=0,
        alias="ACCESS_TOKEN_TIMESTAMP",
        ge=0,
    )
    access_token_ttl_seconds: int = Field(
        default=0,
        alias="ACCESS_TOKEN_TTL_SECONDS",
        ge=0,
    )

    model_config = ConfigDict(populate_by_name=True)

    @property
    def _session_tokens_exist(self) -> bool:
        """
        Checks if the session tokens differ from their initial value.

        Returns:
            bool: True if all session tokens exist, else False.
        """
        return (
            bool(self.access_token)
            and bool(self.refresh_token)
            and self.access_token_timestamp > 0
            and self.access_token_ttl_seconds > 0
        )


class DeviceModel(BaseModel):
    brand: str = Field(alias="BRAND", min_length=1)
    model: str = Field(alias="MODEL", min_length=1)
    android_version: str = Field(alias="ANDROID_VERSION", min_length=1)
    system_version: str = Field(alias="SYSTEM_VERSION", min_length=1)
    build_number: str = Field(alias="BUILD_NUMBER", min_length=1)
    screen_width: int = Field(alias="SCREEN_WIDTH", gt=0)

    model_config = ConfigDict(populate_by_name=True)


class Config:
    def __init__(self):
        self._session: SessionModel = self._load_or_create_session()
        self.settings: SettingsModel = self._load_or_create_settings()
        self.device: Device = self._load_or_create_device()

    def _load_or_create_settings(self) -> SettingsModel:
        """
        Checks if the settings file exists and creates a new one if it doesn't.
        Loads the settings file and creates the SettingsModel object with it.
        Exits the program if any error occurs (e.g. due to a corrupt file).
        Logs a short summary of all errors to the console.

        Returns:
            SettingsModel: SettingsModel object.
        """
        # Check if settings file exists
        if not SETTINGS_FILE_PATH.exists():
            self.generate_new_settings_file()

        # Load settings file 
        parser = configparser.ConfigParser()
        parser.read(SETTINGS_FILE_PATH)

        # Convert settings to a dictionary by iterating over all sections and
        # their keys
        settings_dict = {}
        for section, keys in DEFAULT_SETTINGS.items():
            settings_dict[section] = {}
            # Add missing sections with None values
            if not parser.has_section(section):
                for key in keys:
                    settings_dict[section][key] = None
                continue
            # Add keys with their values
            for key in keys:
                settings_dict[section][key] = parser.get(
                    section=section,
                    option=key,
                    fallback=None,
                )
        # Validate settings against the SettingsModel
        try:
            return SettingsModel.model_validate(settings_dict)

        except ValidationError as exc:
            console.error("Corrupt settings file:")
            for error in exc.errors():
                error_type = error.get("type")
                path = ".".join(str(part) for part in error.get("loc"))

                # Show specific error message for different error types
                if (
                    error_type == "value_error" and 
                    error.get("loc") == ("ACCOUNT", "EMAIL")
                ):
                    console.error(
                        f"- {path}: {error['msg'].split()[0].title()} "
                        f"{' '.join(error['msg'].split()[1:])}"
                    )
                elif error_type == "bool_parsing":
                    console.error(
                        f"- {path}: Value must be a valid boolean value. "
                        f"Valid values are 'True' or 'False'."
                    )
                elif error_type == "float_parsing":
                    console.error(
                        f"- {path}: Value must be a valid decimal number."
                    )
                elif error_type == "int_parsing":
                    console.error(
                        f"- {path}: Value must be a valid whole number."
                    )
                elif error_type in (
                    "greater_than",
                    "greater_than_equal",
                    "less_than",
                    "less_than_equal",
                ):
                    console.error(
                        f"- {path}: {error['msg'].replace('Input', 'Value')}."
                    )
                elif error_type == "payment_card_number_luhn":
                    console.error(
                        f"- {path}: Card number has an invalid checksum. "
                    )
                else:
                    console.error(f"- {path}: {error['msg']}.")

            # Add general note
            console.warning(
                "\nPlease fix the settings file and restart the program. "
            )
            console.warning(
                "Rename or delete the file and restart the program to load "
                "the default settings template."
            )
            console.blank()

            # Open settings file and exit program
            self.open_settings_file()
            sys.exit(1)

    def _load_or_create_session(self) -> SessionModel:
        """
        Checks if the session file exists and creates a new one if it doesn't.
        Loads the session file and creates the SessionModel object with it. If
        any error occurs (e.g. due to a corrupt file), a new session file gets
        created and a default SessionModel object gets returned.

        Returns:
            SessionModel: SessionModel object.
        """
        if not SESSION_FILE_PATH.exists():
            self.generate_new_session_file()

        # Load session file and validate it against the SessionModel
        try:
            with open(SESSION_FILE_PATH) as session_file:
                data = json.load(session_file)
            return SessionModel.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            console.warning(
                "Invalid session file. Generating a new session file..."
            )
            self.generate_new_session_file()
            return SessionModel()

    def _load_or_create_device(self) -> Device:
        """
        Checks if the device file exists and creates a new one with random
        device data if it doesn't. Loads the device file and creates the Device
        object with it. If any error occurs (e.g. due to a corrupt file), a new
        device file gets created and the resulting Device object gets returned.

        Returns:
            Device: Device object.
        """
        if not DEVICE_FILE_PATH.exists():
            self.generate_new_device_file()

        # Load device file and validate it against the DeviceModel
        try:
            with open(DEVICE_FILE_PATH) as device_file:
                data = json.load(device_file)
            model = DeviceModel.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            console.warning(
                "Invalid device file. Generating a new device file..."
            )
            self.generate_new_device_file()
            with open(DEVICE_FILE_PATH) as device_file:
                data = json.load(device_file)
            model = DeviceModel.model_validate(data)

        return Device(
            brand=model.brand,
            model=model.model,
            android_version=model.android_version,
            system_version=model.system_version,
            build_number=model.build_number,
            screen_width=model.screen_width,
        )

    def get_session_tokens(self) -> SessionTokens | None:
        """
        Loads the latest session tokens from the session file.

        Returns:
            SessionTokens | None: SessionTokens object if session tokens exist,
                                  else None.
        """
        self._session = self._load_or_create_session()
        # Check if session tokens exist
        # (meaning the file didn't just get created)
        if not self._session._session_tokens_exist:
            return None
        return SessionTokens(
            access_token=self._session.access_token,
            refresh_token=self._session.refresh_token,
            access_token_timestamp=self._session.access_token_timestamp,
            access_token_ttl_seconds=self._session.access_token_ttl_seconds,
        )

    @staticmethod
    def open_settings_file() -> None:
        """
        Opens the settings file in the default editor.
        """
        console.info(
            "Opening settings file in the default editor...",
            show_time=False,
        )
        with contextlib.suppress(Exception):
            webbrowser.open(f"file://{SETTINGS_FILE_PATH.absolute()}")
        url = f"file://{quote(str(SETTINGS_FILE_PATH), safe='/')}"
        console.info(
            f"You can find the settings file at "
            f"[link={url}]{SETTINGS_FILE_PATH}[/link].",
            show_time=False,
        )
        console.blank()

    @staticmethod
    def generate_new_settings_file() -> None:
        """
        Generates a new settings file with the default values. Opens the new
        file in the default editor and exits the program.
        """
        # Write default settings to file
        settings = configparser.ConfigParser()
        with open(SETTINGS_FILE_PATH, "w") as settings_file:
            for section, values in DEFAULT_SETTINGS.items():
                settings.add_section(section)
                for key, default_value in values.items():
                    settings.set(section, key, default_value)
            settings.write(settings_file)
        
        # Open settings file and exit program
        console.info(
            "New settings file generated. "
            "Please fill it and restart the program.",
            show_time=False,
        )
        console.blank()
        Config.open_settings_file()
        sys.exit(1)

    @staticmethod
    def generate_new_session_file() -> None:
        """
        Generates a new session file with empty session tokens.
        """
        with open(SESSION_FILE_PATH, "w") as session_file:
            json.dump(
                SessionModel().model_dump(by_alias=True),
                session_file,
                indent=4
            )

    @staticmethod
    def generate_new_device_file() -> None:
        """
        Generates a new device file with random device data.
        """
        device = get_random_device()
        model = DeviceModel(
            BRAND=device.brand,
            MODEL=device.model,
            ANDROID_VERSION=device.android_version,
            SYSTEM_VERSION=device.system_version,
            BUILD_NUMBER=device.build_number,
            SCREEN_WIDTH=device.screen_width,
        )
        with open(DEVICE_FILE_PATH, "w") as device_file:
            json.dump(
                model.model_dump(by_alias=True),
                device_file,
                indent=4,
            )

    @staticmethod
    def save_session(tokens: SessionTokens) -> None:
        """
        Saves the session tokens to the session file.

        Args:
            tokens (SessionTokens): Session tokens to save.
        """
        session = SessionModel(
            ACCESS_TOKEN=tokens.access_token,
            REFRESH_TOKEN=tokens.refresh_token,
            ACCESS_TOKEN_TIMESTAMP=tokens.access_token_timestamp,
            ACCESS_TOKEN_TTL_SECONDS=tokens.access_token_ttl_seconds,
        )
        with open(SESSION_FILE_PATH, "w") as session_file:
            json.dump(
                session.model_dump(by_alias=True),
                session_file,
                indent=4,
            )
