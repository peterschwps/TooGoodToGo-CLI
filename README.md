[![PyPI](https://img.shields.io/pypi/v/TGTG-CLI.svg?label=PyPI)](https://pypi.org/project/TGTG-CLI/)
[![Python](https://img.shields.io/pypi/pyversions/TGTG-CLI.svg?label=Python)](https://pypi.org/project/TGTG-CLI/)
[![CI](https://github.com/peterschwps/TooGoodToGo-CLI/actions/workflows/ci.yml/badge.svg)](https://github.com/peterschwps/TooGoodToGo-CLI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

# TooGoodToGo-CLI

**The only CLI for Too Good To Go (TGTG) that automates the full checkout process.**

TooGoodToGo-CLI is a free, open-source bot that monitors magic bags and reserves them automatically before they sell out. It runs directly from the command line, is easy to set up and doesn't require any extra tools.

![Demo](https://raw.githubusercontent.com/peterschwps/TooGoodToGo-CLI/main/docs/assets/demo.gif)

📖 **[Read the full documentation.](https://peterschwps.com/docs/tgtg/)**

## Features

- **Account Login**: passwordless login and persistent sessions.
- **Automatic Checkout**: handles the full checkout flow including any 3DS challenges.
- **Easy Setup**: all settings in a single file, editable with any text editor or directly from the command line.
- **Interactive Menu**: guided flow, easy to navigate.
- **Mobile & Desktop Notifications**: get notified via Ntfy when monitored items become available.
- **Monitor Items**: watch any item in your area and wait for it to become available.

## Installation

Install the app globally with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install tgtg-cli
```

or with [pipx](https://pipx.pypa.io/stable/how-to/install-pipx/):

```bash
pipx install tgtg-cli
```

Other options (pip, virtual environments) are covered in the [Installation guide](https://peterschwps.com/docs/tgtg/installation/).

## Quick Start

1. Start the CLI:

   ```bash
   tgtg
   ```

   > [!NOTE]
   > You can also start the CLI with `tgtg-cli`, `toogoodtogo` and `toogoodtogo-cli`.

2. Select **Settings** from the menu to open the settings file in your default editor.
3. Fill in the settings as described in the [Configuration guide](https://peterschwps.com/docs/tgtg/configuration/), then restart the CLI.
4. Select **Login** and enter the 6-digit code sent to your email.
5. Once logged in, choose **Monitor** and select the item you want to watch.

> [!TIP]
> For automatic checkout, a free virtual card from [Bunq](https://bunq.com) is recommended as it has been used in development. In general, any card that works in the app should work with the CLI. See [Credit Cards](https://peterschwps.com/docs/tgtg/credit-cards/) for more details.

## Disclaimer

This project is an unofficial, independent third-party tool and is **not affiliated with, endorsed by, sponsored by, or in any way officially connected to** Too Good To Go ApS or any of its subsidiaries or affiliates.

"Too Good To Go" and "TGTG" are trademarks of Too Good To Go ApS, used here only nominatively to identify the service this software interacts with.

This software is provided "as is" without warranty of any kind. Use of this tool may violate the Too Good To Go Terms of Service and could result in account termination. The authors accept no liability for any consequences arising from its use.
