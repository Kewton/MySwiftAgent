"""Unit tests for cryptographic services."""

from app.core.crypto import CryptoService


def test_encrypt_decrypt() -> None:
    """Test encryption and decryption roundtrip."""
    crypto = CryptoService()
    plaintext = "my-secret-password-123"

    # Encrypt
    ciphertext, iv, tag = crypto.encrypt(plaintext)

    # Verify we got hex strings
    assert len(ciphertext) > 0
    assert len(iv) == 24  # 12 bytes = 24 hex chars
    assert len(tag) == 32  # 16 bytes = 32 hex chars

    # Decrypt
    decrypted = crypto.decrypt(ciphertext, iv, tag)
    assert decrypted == plaintext


def test_encrypt_different_ivs() -> None:
    """Test that encryption generates different IVs each time."""
    crypto = CryptoService()
    plaintext = "same-secret"

    ciphertext1, iv1, tag1 = crypto.encrypt(plaintext)
    ciphertext2, iv2, tag2 = crypto.encrypt(plaintext)

    # IVs should be different
    assert iv1 != iv2
    # Ciphertexts should be different (because of different IVs)
    assert ciphertext1 != ciphertext2


def test_decrypt_invalid_tag_fails() -> None:
    """Test that decryption fails with invalid tag."""
    crypto = CryptoService()
    plaintext = "my-secret"

    ciphertext, iv, tag = crypto.encrypt(plaintext)

    # Modify tag
    invalid_tag = "0" * 32

    # Should fail
    try:
        crypto.decrypt(ciphertext, iv, invalid_tag)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_decrypt_invalid_ciphertext_fails() -> None:
    """Test that decryption fails with invalid ciphertext."""
    crypto = CryptoService()
    plaintext = "my-secret"

    ciphertext, iv, tag = crypto.encrypt(plaintext)

    # Modify ciphertext
    invalid_ciphertext = "0" * len(ciphertext)

    # Should fail
    try:
        crypto.decrypt(invalid_ciphertext, iv, tag)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
