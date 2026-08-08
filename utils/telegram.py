# utils/telegram.py
import logging
import requests
from django.conf import settings

log = logging.getLogger(__name__)


def send_telegram_message(telegram_id: int, text: str, reply_markup=None) -> bool:
    """
    Oddiy Telegram Bot API orqali xabar yuborish.
    settings.TELEGRAM_BOT_TOKEN bo'lishi kerak.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token or not telegram_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": telegram_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(url, json=payload, timeout=10)
        ok = (r.status_code == 200)
        if not ok:
            log.warning("Telegram send failed: %s %s", r.status_code, r.text[:500])
        return ok
    except Exception as e:
        log.exception("Telegram send exception: %s", e)
        return False
