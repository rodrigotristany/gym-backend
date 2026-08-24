import secrets

from app.utils.hashing import sha256_hex


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp_code(code: str) -> str:
    return sha256_hex(code)


def verify_otp_code(code: str, code_hash: str) -> bool:
    return sha256_hex(code) == code_hash
