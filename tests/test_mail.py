"""SMTP transport contracts without sending external email."""

import smtplib
import pytest
from fastapi import HTTPException
from gaia.config import settings
from gaia.services import mail


@pytest.mark.parametrize("mode", ["ssl", "starttls"])
def test_transport_headers_and_sender(monkeypatch, mode):
    # The application test fixture intercepts send_code; reload its real implementation.
    import importlib

    importlib.reload(mail)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "GAIA <sender@example.com>")
    monkeypatch.setattr(settings, "smtp_security", mode)
    monkeypatch.setattr(settings, "smtp_username", "sender@example.com")
    monkeypatch.setattr(settings, "smtp_password", "test-only-password")
    calls = []

    class SMTP:
        def __init__(self, *args, **kwargs):
            calls.append(("connect", bool(kwargs.get("context"))))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, **kwargs):
            calls.append(("starttls", bool(kwargs.get("context"))))

        def login(self, username, password):
            calls.append(("login", username))

        def send_message(self, message, **kwargs):
            assert kwargs["from_addr"] == "sender@example.com"
            assert message["To"] == "recipient@example.com"
            assert message["Date"] and message["Message-ID"]
            assert "123456" in message.get_content()
            calls.append(("sent", True))

    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", SMTP)
    monkeypatch.setattr(mail.smtplib, "SMTP", SMTP)
    mail.send_code("recipient@example.com", "123456")
    assert calls[0] == ("connect", mode == "ssl")
    assert (("starttls", True) in calls) == (mode == "starttls")
    assert calls[-1] == ("sent", True)


def test_invalid_sender_fails_before_connecting(monkeypatch):
    import importlib

    importlib.reload(mail)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "not-an-email")

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid sender must be rejected before connecting")

    monkeypatch.setattr(smtplib, "SMTP_SSL", unexpected)
    monkeypatch.setattr(smtplib, "SMTP", unexpected)
    with pytest.raises(HTTPException) as error:
        mail.send_code("recipient@example.com", "123456")
    assert error.value.status_code == 503 and "SMTP_FROM" in error.value.detail
