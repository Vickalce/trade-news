from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
import smtplib

import httpx

from api.core.config import settings


def _write_outbox(channel: str, payload: str) -> str:
    channel_name = channel.lower()
    out_dir = Path(settings.alert_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{channel_name}_{stamp}.log"
    out_path.write_text(payload, encoding="utf-8")
    return "delivered_local"


def _deliver_email(payload: str) -> str:
    if not settings.smtp_host or not settings.smtp_to_email:
        return _write_outbox("email", payload)

    msg = EmailMessage()
    msg["Subject"] = "Trade News Alert"
    msg["From"] = settings.smtp_from_email or settings.smtp_username or "trade-news@localhost"
    msg["To"] = settings.smtp_to_email
    msg.set_content(payload)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
    return "delivered"


def _deliver_discord(payload: str) -> str:
    if not settings.discord_webhook_url:
        return _write_outbox("discord", payload)
    with httpx.Client(timeout=10) as client:
        response = client.post(settings.discord_webhook_url, json={"content": payload})
        response.raise_for_status()
    return "delivered"


def _deliver_telegram(payload: str) -> str:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return _write_outbox("telegram", payload)

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    body = {"chat_id": settings.telegram_chat_id, "text": payload}
    with httpx.Client(timeout=10) as client:
        response = client.post(url, json=body)
        response.raise_for_status()
    return "delivered"


def deliver_alert(channel: str, payload: str) -> str:
    key = channel.strip().lower()
    try:
        if key == "email":
            return _deliver_email(payload)
        if key == "discord":
            return _deliver_discord(payload)
        if key == "telegram":
            return _deliver_telegram(payload)
        return _write_outbox(key or "unknown", payload)
    except Exception as exc:
        _write_outbox(f"{key or 'unknown'}_failed", payload)
        return f"failed:{type(exc).__name__}"


def deliver_alerts(payload: str, channels: list[str]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for channel in channels:
        statuses[channel] = deliver_alert(channel, payload)
    return statuses
