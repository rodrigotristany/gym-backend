import logging

logger = logging.getLogger("app.email")


def send_otp_email(to_email: str, code: str, purpose: str) -> None:
    logger.info("OTP email to=%s purpose=%s code=%s", to_email, purpose, code)
