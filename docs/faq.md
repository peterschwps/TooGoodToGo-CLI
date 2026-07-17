---
description: >-
  Frequently asked questions about the TooGoodToGo CLI — payment, rate limits,
  where credentials are stored, resetting and account safety.
---

# FAQ

## Do I need a credit card to use the CLI?

No. Monitoring and notifications work without payment details. Set
`ENABLE_CHECKOUT = False` in `settings.ini` and leave the `[PAYMENT]` fields
empty. You'll receive a notification whenever a monitored item becomes
available and can then check out manually in the Too Good To Go app.

## My card is rejected during checkout. What's wrong?

A few possible causes:

- Your bank requires an SMS code or another authorization flow not supported
  by the CLI.
- Your card has insufficient funds or a spending limit below the item price.

Try to use [Bunq](https://bunq.com) as described in
[Credit Cards](credit-cards.md) if possible. If you keep getting errors, open
an issue.

## How long am I blocked after being rate limited?

Soft bans seem to last one hour. After the cooldown, the CLI works as normal —
no extra action needed. To reduce the chance of being rate-limited again, keep
the polling delay at `4500ms` or higher.

If you don't want to wait for an hour you can change your IP, e.g. by using a
proxy.

## Where are my credentials and tokens stored?

Session tokens, the random device profile, and logs live in the OS-native
cache directory:

| OS | Path |
| --- | --- |
| **macOS** | `~/Library/Caches/TGTG-CLI/` |
| **Linux** | `~/.cache/TGTG-CLI/` (or `$XDG_CACHE_HOME/TGTG-CLI/`) |
| **Windows** | `%LOCALAPPDATA%\TGTG-CLI\Cache\` |

Card details are read from `settings.ini` (see
[File Location](configuration.md#file-location)).

## Why do I keep getting logged out?

The session tokens are stored in your local cache directory (see
[Where are my credentials and tokens stored?](#where-are-my-credentials-and-tokens-stored)).
Cleanup tools might clear that directory, which means that you will have to log
in again. Add the `TGTG-CLI/` folder to the tool's exclude list to prevent
this.

## How do I reset the CLI?

Select **Logout** in the menu to clear the session, or delete the config and
cache directories above for a full reset. On the next start, both files will be
recreated.

## Will using this tool get my account banned?

This tool may violate the Too Good To Go Terms of Service. Use at your own
risk. See the [Disclaimer](disclaimer.md) for details. To reduce exposure,
keep the polling delay at the default (`4500ms`) or even higher.
