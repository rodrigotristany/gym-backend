from app.utils.otp import generate_otp_code, hash_otp_code, verify_otp_code


def test_generate_otp_code_is_six_digits():
    code = generate_otp_code()
    assert len(code) == 6
    assert code.isdigit()


def test_hash_and_verify_otp_code_roundtrip():
    code = generate_otp_code()
    code_hash = hash_otp_code(code)
    assert verify_otp_code(code, code_hash) is True
    assert verify_otp_code("000000", code_hash) is False
