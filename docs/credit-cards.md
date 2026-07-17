---
description: >-
  Which credit cards work with the TooGoodToGo CLI, the supported 3DS
  authorization flows and recommended virtual-card providers.
---

# Credit Cards

In general, **any credit card** that works in the Too Good To Go app should
also work here. Some exceptions might be credit cards that require an SMS code
or have a special authorization flow.

!!! warning
    Your card details are stored on your local disk. **It is highly
    recommended to use a dedicated virtual card with a custom spending
    limit.**

[**Bunq**](https://bunq.com) is one of the recommended providers as it
provides the necessary features and has been tested already. Opening an
account is free, virtual cards can be created at no extra cost and you can set
spending limits for each card. You can delete and re-create a new card at any
time.

You can find more information about the different authorization flows and a
list of fully supported providers down below.

---

There are three different authorization flows:

| Flow | Explanation | Implementation |
| --- | --- | --- |
| **3DS2** | As far as my testing goes, this seems to be the most common flow. It should be the same one you encounter when manually buying an item in the Too Good To Go app. | The CLI handles the authorization flow. The user receives a notification asking them to confirm the 3DS challenge. |
| **Redirect (supported provider)** | This appears to be the legacy 3DS1 flow. However, it seems to occur randomly even for cards that usually use the 3DS2 flow. | Same as 3DS2, but only for supported providers. Each provider requires a different implementation. See the list down below for a list of providers that are confirmed to work. |
| **Redirect (unsupported provider)** | Same flow as above. | The CLI sends a notification with the challenge URL. The user needs to open the URL, complete all required steps and confirm the challenge. |

---

Supported providers for **redirect** challenges:

| Providers |
| --------- |
| Bunq      |
| DKB       |

!!! note
    Please open an issue if you think that your provider is well-known and
    should be added to this list.
