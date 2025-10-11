"""Cryptographic services for secret encryption/decryption."""

import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class CryptoService:
    """Service for encrypting and decrypting secrets using AES-256-GCM."""

    def __init__(self) -> None:
        """Initialize crypto service with master key."""
        self.master_key = settings.get_master_key_bytes()
        self.aesgcm = AESGCM(self.master_key)

    def encrypt(self, plaintext: str) -> tuple[str, str, str]:
        """
        Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: The secret value to encrypt

        Returns:
            Tuple of (ciphertext_hex, iv_hex, tag_hex)
        """
        # Generate random 12-byte IV (nonce)
        iv = secrets.token_bytes(12)

        # Encrypt and get ciphertext with authentication tag
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext_with_tag = self.aesgcm.encrypt(iv, plaintext_bytes, None)

        # Split ciphertext and tag (last 16 bytes are the tag)
        ciphertext = ciphertext_with_tag[:-16]
        tag = ciphertext_with_tag[-16:]

        return (
            ciphertext.hex(),
            iv.hex(),
            tag.hex(),
        )

    def decrypt(self, ciphertext_hex: str, iv_hex: str, tag_hex: str) -> str:
        """
        Decrypt ciphertext using AES-256-GCM.

        Args:
            ciphertext_hex: Hex-encoded ciphertext
            iv_hex: Hex-encoded initialization vector
            tag_hex: Hex-encoded authentication tag

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails or authentication fails
        """
        try:
            # Convert from hex
            ciphertext = bytes.fromhex(ciphertext_hex)
            iv = bytes.fromhex(iv_hex)
            tag = bytes.fromhex(tag_hex)

            # Reconstruct ciphertext with tag
            ciphertext_with_tag = ciphertext + tag

            # Decrypt and verify
            plaintext_bytes = self.aesgcm.decrypt(iv, ciphertext_with_tag, None)
            return plaintext_bytes.decode("utf-8")

        except Exception as e:
            raise ValueError(f"Decryption failed: {e}") from e


# Global crypto service instance
crypto_service = CryptoService()
