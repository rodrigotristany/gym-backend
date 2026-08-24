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


def test_validate_password_strength_rejects_over_72_bytes():
    # Otherwise valid, but bcrypt would raise ValueError on it.
    password = "A1!" + "a" * 70
    assert len(password.encode()) > 72
    with pytest.raises(ValueError, match="72 bytes"):
        validate_password_strength(password)


def test_validate_password_strength_counts_bytes_not_characters():
    # 40 multi-byte characters = 120 bytes, but only 43 characters.
    password = "A1!" + "é" * 40
    assert len(password) <= 72
    with pytest.raises(ValueError, match="72 bytes"):
        validate_password_strength(password)


def test_verify_password_returns_false_for_over_length_input():
    hashed = hash_password("Str0ng!Pass")
    assert verify_password("x" * 100, hashed) is False
