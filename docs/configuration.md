---
description: >-
  Full reference for the TooGoodToGo CLI settings.ini — account, application,
  payment, monitor and solver options, with an annotated example.
---

# Configuration

The configuration of the CLI can be changed in the `settings.ini`. This file
is generated automatically on the first start and opened in your default
editor. If you are making any changes to it, you always need to restart the
CLI.

!!! note
    If you ever need a fresh `settings.ini` you can simply delete or rename the
    file and restart the CLI.

## File Location

The path follows the platform-specific config directory:

| OS | Path |
| --- | --- |
| **macOS** | `~/Library/Application Support/TGTG-CLI/settings.ini` |
| **Linux** | `~/.config/TGTG-CLI/settings.ini` (or `$XDG_CONFIG_HOME/TGTG-CLI/settings.ini`) |
| **Windows** | `%APPDATA%\TGTG-CLI\settings.ini` |

You can re-open the file at any time via **Settings** in the menu. This will
also show you the path of the file.

## Settings Reference

The settings file is split into five sections. All keys are required to be
present, but optional values can be left empty when the parameter is not used.

### `[ACCOUNT]`

All settings regarding your Too Good To Go account and the geographic area to
scan.

| Key | Type | Description |
| --- | --- | --- |
| `EMAIL` | string | Email of your Too Good To Go account. Example: `your-email@example.com`. |
| `LATITUDE` | decimal | Latitude of the area to monitor. Example: `55.713`. |
| `LONGITUDE` | decimal | Longitude of the area to monitor. Example: `12.569982`.<br><br>**Note:** You can get the coordinates (`latitude,longitude`) by right-clicking any location on [Google Maps](https://www.google.com/maps). Make sure the decimal numbers are using a `.` and not a `,`. |
| `RADIUS` | integer | Search radius in full kilometers. Example: `5`. |
| `PROXY` | string | Optional proxy in the format `username:password@hostname:port`. Required when `CAPSOLVER_API_KEY` is set.<br><br>**Note:** Using a proxy is only recommended if you have problems bypassing Cloudflare. |

### `[APPLICATION]`

Feature switches to configure the behaviour of the CLI.

| Key | Type | Description |
| --- | --- | --- |
| `ENABLE_LOGGING` | bool | Write logs to disk. Set to `True` or `False`. Default: `False`. This creates a log file in the cache directory.<br><br>**Note:** This is mainly for debugging purposes. It is recommended to turn off logging unless you are having issues. |
| `ENABLE_CHECKOUT` | bool | If `True`, the CLI will attempt to complete the purchase automatically. Requires all `[PAYMENT]` fields to be filled. Default: `False`. If set to `False`, the CLI will only notify the user when an item becomes available and not try to buy it. |

### `[PAYMENT]`

Card details used for automatic checkout. Only required when
`ENABLE_CHECKOUT = True`.

| Key | Type | Description |
| --- | --- | --- |
| `CARD_NUMBER` | string | Card number, digits only. Validated via Luhn checksum. Example: `4242424242424242`. |
| `CARD_EXPIRY_MONTH` | integer | Month of expiry (`1`–`12`). Example `6`. |
| `CARD_EXPIRY_YEAR` | integer | Year of expiry, four digits. Example `2028`. |
| `CARD_SECURITY_CODE` | string | CVC / CVV (3 or 4 digits). Example `034`. |

### `[MONITOR]`

Behavior of the CLI when monitoring an item.

| Key | Type | Description |
| --- | --- | --- |
| `DELAY_IN_MILLISECONDS` | integer | Delay between polls in milliseconds. Default: `4500`. Please note that lower delays may trigger rate limiting. |
| `NTFY_TOPIC` | string | Topic name for [Ntfy.sh](https://ntfy.sh) push notifications. Subscribe to the same topic in the ntfy app to receive alerts.<br>You can find the Ntfy setup guide [here](https://docs.ntfy.sh).<br><br>**Note:** Make sure you pick a unique string to prevent other users receiving your notifications. This could be a random [UUID](https://www.uuidgenerator.net/) or a random [password](https://1password.com/password-generator). |

### `[SOLVER]`

Configuration of the captcha solver via
[CapSolver](https://dashboard.capsolver.com/passport/register?inviteCode=Gac0yUtJJQhN).
This is only needed for edge cases if you are having trouble logging into your
account. CapSolver will only be used to solve the captcha upon login and
retrieving the session tokens.

| Key | Type | Description |
| --- | --- | --- |
| `CAPSOLVER_API_KEY` | string | Your CapSolver API key. Leave empty to disable. **A proxy in `[ACCOUNT]` is mandatory** when this key is set. |

## Example

```ini
[ACCOUNT]
EMAIL = your-email@example.com
LATITUDE = 55.713
LONGITUDE = 12.569982
RADIUS = 3
PROXY =

[APPLICATION]
ENABLE_LOGGING = False
ENABLE_CHECKOUT = True

[PAYMENT]
CARD_NUMBER = 4242424242424242
CARD_EXPIRY_MONTH = 6
CARD_EXPIRY_YEAR = 2028
CARD_SECURITY_CODE = 034

[MONITOR]
DELAY_IN_MILLISECONDS = 4500
NTFY_TOPIC = your-unique-topic-string

[SOLVER]
CAPSOLVER_API_KEY =
```

!!! danger "Do not remove any keys or sections!"
    Leave any optional parameters empty if you don't need them.
