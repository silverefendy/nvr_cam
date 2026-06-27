"""
Telegram notifier — kirim pesan dan foto snapshot ke Telegram Bot.
"""
import aiohttp
from pathlib import Path
from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__, service="notifier")

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


async def send_message(text: str, chat_id: str | None = None) -> bool:
    """Kirim pesan teks ke Telegram."""
    token = settings.telegram_bot_token
    cid = chat_id or settings.telegram_chat_id
    if not token or not cid:
        logger.warning("Telegram tidak dikonfigurasi")
        return False
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.post(url, json={"chat_id": cid, "text": text, "parse_mode": "HTML"})
            return resp.status == 200
    except Exception as e:
        logger.error(f"Gagal kirim Telegram: {e}")
        return False


async def send_photo(photo_path: str, caption: str, chat_id: str | None = None) -> bool:
    """Kirim foto snapshot ke Telegram."""
    token = settings.telegram_bot_token
    cid = chat_id or settings.telegram_chat_id
    if not token or not cid:
        return False
    url = TELEGRAM_API.format(token=token, method="sendPhoto")
    try:
        async with aiohttp.ClientSession() as session:
            with open(photo_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("chat_id", cid)
                form.add_field("caption", caption, content_type="text/plain")
                form.add_field("photo", f, filename=Path(photo_path).name, content_type="image/jpeg")
                resp = await session.post(url, data=form)
                return resp.status == 200
    except Exception as e:
        logger.error(f"Gagal kirim foto Telegram: {e}")
        return False


async def notify_motion(camera_name: str, zone_name: str, snapshot_path: str | None):
    """Format dan kirim notifikasi motion detection."""
    from datetime import datetime
    ts = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    text = (
        f"🔴 <b>MOTION DETECTED</b>\n"
        f"📷 {camera_name}\n"
        f"📍 Zona: {zone_name}\n"
        f"🕐 {ts}"
    )
    if snapshot_path and Path(snapshot_path).exists():
        await send_photo(snapshot_path, caption=text)
    else:
        await send_message(text)


async def notify_camera_offline(camera_name: str):
    await send_message(f"⚠️ <b>KAMERA OFFLINE</b>\n📷 {camera_name}\nSegera periksa koneksi.")


async def notify_disk_warning(drive: str, free_pct: float):
    await send_message(f"💾 <b>DISK HAMPIR PENUH</b>\nDrive: {drive}\nSisa: {free_pct:.1f}%")
