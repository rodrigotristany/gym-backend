import re

import bcrypt

PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]).{8,}$'
)

# bcrypt rejects inputs longer than 72 bytes with a ValueError.
MAX_PASSWORD_BYTES = 72


def validate_password_strength(password: str) -> None:
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_BYTES} bytes.")
    if not PASSWORD_PATTERN.match(password):
        raise ValueError(
            "Password must be at least 8 characters and include uppercase, "
            "lowercase, a number, and a symbol."
        )


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    encoded = plain.encode()
    if len(encoded) > MAX_PASSWORD_BYTES:
        # bcrypt would raise ValueError; an over-length candidate can never
        # match a stored hash, so treat it as a failed verification.
        return False
    return bcrypt.checkpw(encoded, hashed.encode())
