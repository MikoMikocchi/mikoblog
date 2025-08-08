import pytest

from src.core import security


@pytest.mark.unit
async def test_verify_password_invalid_password():
    hashed_password = security.get_password_hash("correct_password")

    # Verify that an incorrect password returns False
    assert not security.verify_password("wrong_password", hashed_password)

    # Verify that the correct password returns True
    assert security.verify_password("correct_password", hashed_password)
