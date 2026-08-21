import pytest

from app.utils.password import hash_password, validate_password_strength, verify_password


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("Str0ng!Pass")
    assert hashed != "Str0ng!Pass"
    assert verify_password("Str0ng!Pass", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.parametrize(
    "password",
    ["Str0ng!", "nouppercase1!", "NOLOWERCASE1!", "NoDigitsHere!", "NoSymbols1here"],
)
def test_validate_password_strength_rejects_weak_passwords(password):
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_validate_password_strength_accepts_strong_password():
    validate_password_strength("Str0ng!Pass")
