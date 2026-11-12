"""SMTP delivery. Never log codes or make them available through HTTP."""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr, formatdate, make_msgid
from email_validator import validate_email, EmailNotValidError
from fastapi import HTTPException
from ..config import settings


def send_code(address: str, code: str):
    if not settings.smtp_host or not settings.smtp_from:
        raise HTTPException(503, "Почта ещё не подключена. Администратору нужно заполнить SMTP_* в .env.")
    try:
        sender = validate_email(parseaddr(settings.smtp_from)[1], check_deliverability=False).normalized
    except (EmailNotValidError, ValueError) as exc:
        raise HTTPException(
            503, "Некорректный SMTP_FROM в .env. Укажите email отправителя; для Gmail — адрес SMTP_USERNAME."
        ) from exc
    message = EmailMessage()
    message["Subject"] = "GAIA — подтверждение входа"
    message["From"] = settings.smtp_from
    message["To"] = address
    message["Date"] = formatdate(usegmt=True)
    message["Message-ID"] = make_msgid(domain=sender.rsplit("@", 1)[1])
    message.set_content(
        f"Ваш код GAIA: {code}\n\nДействует 10 минут, используется один раз. "
        "Не сообщайте его другим. Если вы не входили в GAIA, проигнорируйте письмо."
    )
    try:
        if settings.smtp_security == "ssl":
            smtp = smtplib.SMTP_SSL(
                settings.smtp_host, settings.smtp_port, timeout=15, context=ssl.create_default_context()
            )
        elif settings.smtp_security == "starttls":
            smtp = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            smtp.starttls(context=ssl.create_default_context())
        else:
            raise HTTPException(503, "SMTP_SECURITY должен быть starttls или ssl")
        with smtp:
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message, from_addr=sender)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(
            503, "Не удалось отправить письмо. Проверьте настройки SMTP и повторите попытку."
        ) from exc
