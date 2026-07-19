---
description: >-
  The only CLI for Too Good To Go (TGTG) that automates the full checkout: it
  monitors magic bags, notifies you when they become available and pays
  automatically.
hide:
  - toc
---

# TooGoodToGo-CLI

**The only CLI for Too Good To Go (TGTG) that automates the full checkout
process.**

Magic bags sell out in seconds. TooGoodToGo-CLI is your personal helper tool:
it watches your favorite stores, sends a notification the instant an item
is available. It can automatically reserve and pay for it (including 3DS), so
you grab any item before it sells out. The app is free, open-source and runs on any platform.

[![PyPI](https://img.shields.io/pypi/v/TGTG-CLI.svg?label=PyPI)](https://pypi.org/project/TGTG-CLI/)
[![Python](https://img.shields.io/pypi/pyversions/TGTG-CLI.svg?label=Python)](https://pypi.org/project/TGTG-CLI/)
[![CI](https://github.com/peterschwps/TooGoodToGo-CLI/actions/workflows/ci.yml/badge.svg)](https://github.com/peterschwps/TooGoodToGo-CLI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/peterschwps/TooGoodToGo-CLI/blob/main/LICENSE)

![Demo of TooGoodToGo-CLI in action](assets/demo.gif)

## Features

- **Account Login**: passwordless login and persistent sessions.
- **Automatic Checkout**: handles the full checkout flow including any 3DS challenges.
- **Easy Setup**: all settings in a single file, editable with any text editor or directly from the command line - no extra tools needed.
- **Interactive Menu**: guided flow, easy to navigate.
- **Mobile & Desktop Notifications**: get notified via Ntfy when monitored items become available.
- **Monitor Items**: watch any item in your area and wait for it to become available.

## Get started

<div class="grid cards" markdown>

- **[Installation](installation.md)**

    Install with `uv` or `pipx`.

- **[Quick Start](quickstart.md)**

    From zero to monitoring in a few steps.

- **[Configuration](configuration.md)**

    Every setting explained in detail.

- **[FAQ](faq.md)**

    Common questions and troubleshooting.

</div>

!!! warning
    This project is an unofficial, independent third-party tool and is **not
    affiliated with Too Good To Go**. Use of this tool may violate the Too
    Good To Go Terms of Service. See the [Disclaimer](disclaimer.md) for
    details.
