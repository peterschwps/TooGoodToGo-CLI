---
description: >-
  Frequently asked questions about TooGoodToGo-CLI: configuration, functionality,
  rate limits and more.
---

# FAQ

## Is TooGoodToGo-CLI a bot?

Yes. TooGoodToGo-CLI is a free, open-source bot for Too Good To Go (TGTG): it
monitors the items you choose and, when one becomes available, can automatically
reserve and pay for it. You simply run it from the command line and stay in
full control.

## Does this work with Surprise Bags / Magic Bags?

Yes. "Surprise Bag" and "Magic Bag" are two names Too Good To Go uses for the
same thing, a bag of surplus food (which label you see depends on your region and
store). TooGoodToGo-CLI works with any item you can see in the app.

## How can I get Magic Bags before they sell out?

Popular magic bags are often gone within seconds. Add the items you want and
TooGoodToGo-CLI monitors them for you, sends a notification the moment one is
available, and (with checkout enabled) reserves and pays automatically, so you no
longer have to refresh the app by hand. For the best chance of reserving a magic bag, it is recommended to enable checkout.

## Can I configure TooGoodToGo-CLI to only be notified when a Magic Bag is available?

Yes. TooGoodToGo-CLI can send push notifications through the free
[Ntfy](https://ntfy.sh) app or website whenever a monitored item becomes
available, even if you leave automatic checkout turned off.

## Is it free to use?

Yes. TooGoodToGo-CLI is completely free and open-source (MIT licensed). You only
pay Too Good To Go for the bags you actually buy.

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

Soft bans seem to last one hour. After the cooldown, the CLI works as normal with
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
