"""
This module instantiates the Config and TGTG class in the global namespace.
Both instances are required in multiple places across the application.
"""
import sys

from requests.exceptions import ConnectionError

from tgtg_cli.cli import console
from tgtg_cli.cli.config import Config
from tgtg_cli.utils.exceptions import SettingsError

# Initialize config
try:
    config = Config()
except SettingsError as e:
    console.clear()
    console.error(f"Settings error: {e}")
    console.blank()
    Config.open_settings_file()
    sys.exit(1)

# Initialize TGTG client
# IMPORTANT: This has to be done after initializing the config!
from tgtg_cli.apis.tgtg import TGTG

try:
    tgtg = TGTG()
except ConnectionError:
    console.clear()
    console.error(
        "Failed to establish a connection. "
        "Make sure you are connected to the internet."
    )
    sys.exit(1)
