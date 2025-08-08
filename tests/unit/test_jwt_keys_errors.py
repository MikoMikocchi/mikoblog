import pytest

from src.core import jwt_keys


@pytest.mark.unit
async def test_load_keypair_private_key_not_found(monkeypatch, tmp_path):
    # Create a temporary directory
    temp_dir = tmp_path / "keys"
    temp_dir.mkdir()

    # Set environment variables to point to non-existent files
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(temp_dir / "nonexistent_private.pem"))
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(temp_dir / "nonexistent_public.pem"))

    # Clear the cache to force reloading
    jwt_keys.load_keypair.cache_clear()

    with pytest.raises(FileNotFoundError) as exc_info:
        jwt_keys.load_keypair()

    assert "JWT private key not found" in str(exc_info.value)


@pytest.mark.unit
async def test_load_keypair_public_key_not_found(monkeypatch, tmp_path):
    # Create a temporary directory
    temp_dir = tmp_path / "keys"
    temp_dir.mkdir()

    # Create a private key file
    private_key_file = temp_dir / "private.pem"
    private_key_file.write_text(
        "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQD..."
    )  # truncated for brevity

    # Set environment variables
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(private_key_file))
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(temp_dir / "nonexistent_public.pem"))

    # Clear the cache to force reloading
    jwt_keys.load_keypair.cache_clear()

    with pytest.raises(FileNotFoundError) as exc_info:
        jwt_keys.load_keypair()

    assert "JWT public key not found" in str(exc_info.value)


@pytest.mark.unit
async def test_load_keypair_invalid_private_key(monkeypatch, tmp_path):
    # Create a temporary directory
    temp_dir = tmp_path / "keys"
    temp_dir.mkdir()

    # Create invalid key files
    private_key_file = temp_dir / "private.pem"
    private_key_file.write_text("invalid private key content")

    public_key_file = temp_dir / "public.pem"
    public_key_file.write_text("-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...")  # truncated for brevity

    # Set environment variables
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(private_key_file))
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(public_key_file))

    # Clear the cache to force reloading
    jwt_keys.load_keypair.cache_clear()

    with pytest.raises(ValueError) as exc_info:
        jwt_keys.load_keypair()

    assert "Invalid private key PEM content" in str(exc_info.value)


@pytest.mark.unit
async def test_load_keypair_invalid_public_key(monkeypatch, tmp_path):
    # Create a temporary directory
    temp_dir = tmp_path / "keys"
    temp_dir.mkdir()

    # Create key files
    private_key_file = temp_dir / "private.pem"
    private_key_file.write_text(
        "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQD..."
    )  # truncated for brevity

    public_key_file = temp_dir / "public.pem"
    public_key_file.write_text("invalid public key content")

    # Set environment variables
    monkeypatch.setenv("JWT_PRIVATE_KEY_PATH", str(private_key_file))
    monkeypatch.setenv("JWT_PUBLIC_KEY_PATH", str(public_key_file))

    # Clear the cache to force reloading
    jwt_keys.load_keypair.cache_clear()

    with pytest.raises(ValueError) as exc_info:
        jwt_keys.load_keypair()

    assert "Invalid public key PEM content" in str(exc_info.value)
