"""SMTP email delivery for registration verification."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from personal_learning_coach.config import load_config


class EmailConfigurationError(RuntimeError):
    """Raised when SMTP settings are incomplete."""


class EmailDeliveryError(RuntimeError):
    """Raised when SMTP delivery fails."""


def send_registration_email_code(email: str, code: str) -> None:
    config = load_config()
    issues = config.validate_smtp()
    if issues:
        raise EmailConfigurationError("; ".join(issues))

    message = EmailMessage()
    message["Subject"] = "Personal Learning Coach 邮箱验证码"
    message["From"] = f"{config.smtp_from_name} <{config.smtp_from_email}>"
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                "你正在注册 Personal Learning Coach。",
                "",
                f"邮箱验证码：{code}",
                "",
                "验证码 10 分钟内有效。如果这不是你的操作，请忽略这封邮件。",
            ]
        )
    )

    try:
        if config.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                config.smtp_host, config.smtp_port, timeout=config.smtp_timeout_seconds
            ) as smtp:
                _send(smtp, config.smtp_username, config.smtp_password, message)
            return

        with smtplib.SMTP(
            config.smtp_host, config.smtp_port, timeout=config.smtp_timeout_seconds
        ) as smtp:
            if config.smtp_use_tls:
                smtp.starttls()
            _send(smtp, config.smtp_username, config.smtp_password, message)
    except smtplib.SMTPException as exc:
        raise EmailDeliveryError(str(exc)) from exc
    except OSError as exc:
        raise EmailDeliveryError(str(exc)) from exc


def _send(smtp: smtplib.SMTP, username: str, password: str, message: EmailMessage) -> None:
    smtp.login(username, password)
    smtp.send_message(message)
