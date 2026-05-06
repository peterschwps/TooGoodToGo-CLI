from base64 import urlsafe_b64encode
from os import urandom

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from tgtg_cli.apis.cryptography import URL


def shorten_url(target_url: str) -> str:
    """
    Encrypts a target URL and sends it to the server to shorten it. Builds the 
    full URL to resolve the shortened URL back to the target URL by adding the
    key as a URI fragment.
    This keeps the target URL completely hidden from the server ensuring the
    highest-possible security.

    This function is a workaround for Ntfy's 4KB message limit which might be
    exceeded if Adyen's payment link is too long.
    See also: https://docs.ntfy.sh/config/#message-limits.

    Args:
        target_url (str): URL to encrypt and shorten.

    Returns:
        str: URL to be opened by the client.
    """
    # Encryption with AES-256-GCM
    key = urandom(32)
    iv = urandom(12)
    data = target_url.encode("utf-8")
    ciphertext_and_tag = AESGCM(key).encrypt(iv, data, None)

    # Send blob to API
    blob = urlsafe_b64encode(iv + ciphertext_and_tag).decode()
    response = requests.post(
        url=f"{URL}/shorten",
        json={"blob": blob},
        timeout=10,
    )
    data = response.json()
    return f"{data['url']}#{urlsafe_b64encode(key).decode()}"
