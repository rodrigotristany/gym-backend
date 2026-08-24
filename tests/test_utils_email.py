import logging

from app.utils.email import send_otp_email


def test_send_otp_email_logs_the_code(caplog):
    with caplog.at_level(logging.INFO, logger="app.email"):
        send_otp_email("user@example.com", "123456", "login_otp")
    assert "123456" in caplog.text
    assert "user@example.com" in caplog.text
