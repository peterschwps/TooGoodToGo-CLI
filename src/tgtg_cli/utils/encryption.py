import json
from base64 import urlsafe_b64encode
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class Encryption:
    """
    Encrypts all card details as a JSON Web Encryption (JWE) token.
    """

    def __init__(
        self,
        exponent_hex: str,
        modulus_hex: str,
        aes_key: bytes,
        iv: bytes,
    ):
        """
        Initializes the Encryption class.

        Args:
            exponent_hex (str): Exponent of Adyen's public key.
            modulus_hex (str): Modulus of Adyen's public key.
            aes_key (bytes): Unique AES key provided by the Cryptography API.
            iv (bytes): Unique initialization vector provided by the 
                        Cryptography API.
        """
        self.exponent_hex = exponent_hex
        self.modulus_hex = modulus_hex
        self.aes_key = aes_key
        self.iv = iv
        self.encoded_iv = urlsafe_b64encode(self.iv).decode()

        # Additional variables
        self.encoded_header = None
        self.cipher = None

        # Retrieve Adyen's public key
        self.public_key = rsa.RSAPublicNumbers(
            int(self.exponent_hex, 16),
            int(self.modulus_hex, 16),
        ).public_key()

        # Encrypt AES key with Adyen's public key (RSA-OAEP-256) and encode it
        encrypted_key = self.public_key.encrypt(
            self.aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        self.encoded_key = urlsafe_b64encode(encrypted_key).decode()

    def _encrypt(self, payload: dict[str, Any]) -> str:
        """
        Encrypts a payload as a JSON Web Encryption (JWE) token. This token 
        contains the following base64 url-safe encoded components:

        1.) Header: The header gets created the first time this method is
                    called. It is then stored as an attribute to speed up the
                    process.

        2.) Encrypted key: The AES key is encrypted with Adyen's public key 
                           using the RSA-OAEP-256 algorithm. An unique key
                           can be retrieved from the external Cryptography API.

        3.) Initialization vector: An unique initialization vector can be 
                                   retrieved from the external Cryptography 
                                   API.

        4.) Ciphertext: The ciphertext is encrypted using the AES-256-GCM
                        algorithm.

        5.) Tag: The tag is derived from the ciphertext after the encryption
                 is finalized.

        Args:
            payload (dict[str, Any]): Payload to encrypt.

        Returns:
            str: Encrypted payload as a JWE token.
        """
        # Encode header if not previously done
        if self.encoded_header is None:
            header_bytes = json.dumps({
                "alg": "RSA-OAEP-256",
                "enc": "A256GCM",
                "version": "1",
            }).encode()
            self.encoded_header = urlsafe_b64encode(header_bytes).decode()
        
        # Create cipher if not previously done
        if self.cipher is None:
            self.cipher = Cipher(
                algorithm=algorithms.AES(key=self.aes_key),
                mode=modes.GCM(initialization_vector=self.iv)
            )
        
        # Create encryptor
        encryptor = self.cipher.encryptor()
        encryptor.authenticate_additional_data(
            data=self.encoded_header.encode()
        )

        # Add timestamp to payload
        timestamp = datetime.now(UTC).isoformat(timespec='milliseconds')
        payload["generationtime"] = timestamp

        # Create encrypted ciphertext and get tag
        ciphertext = encryptor.update(json.dumps(payload).encode())
        ciphertext += encryptor.finalize()
        tag = encryptor.tag

        # Build JWE
        return ".".join([
            self.encoded_header,
            self.encoded_key,
            self.encoded_iv,
            urlsafe_b64encode(ciphertext).decode(),
            urlsafe_b64encode(tag).decode(),
        ])

    def encrypt_bin(self, bin_number: str) -> str:
        """
        Encrypts a BIN number as a JWE token.

        Args:
            bin_number (str): BIN number (first 11 digits of the card number).

        Returns:
            str: Encrypted BIN number as a JWE token.
        """
        return self._encrypt({"binValue": bin_number})

    def encrypt_card_number(self, card_number: str) -> str:
        """
        Encrypts a card number as a JWE token.

        Args:
            card_number (str): Card number.

        Returns:
            str: Encrypted card number as a JWE token.
        """
        return self._encrypt({"number": card_number})

    def encrypt_expiry_month(self, expiry_month: int) -> str:
        """
        Encrypts the expiry month as a JWE token.

        Args:
            expiry_month (int): Expiry month (1-12).

        Returns:
            str: Encrypted expiry month as a JWE token.
        """
        return self._encrypt({"expiryMonth": expiry_month})
    
    def encrypt_expiry_year(self, expiry_year: int) -> str:
        """
        Encrypts the expiry year as a JWE token.

        Args:
            expiry_year (int): Expiry year (YYYY).

        Returns:
            str: Encrypted expiry year as a JWE token.
        """
        return self._encrypt({"expiryYear": expiry_year})
    
    def encrypt_security_code(self, security_code: str) -> str:
        """
        Encrypts the security code as a JWE token.

        Args:
            security_code (str): Security code.

        Returns:
            str: Encrypted security code as a JWE token.
        """
        return self._encrypt({"cvc": security_code})
