"""Router: /api/v1/settings — Pengaturan global sistem."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from backend.api.middleware.auth import get_current_admin_user
from backend.db.models.user import User
from backend.utils.config_manager import config_manager

router = APIRouter(tags=["settings"])


class GeneralSettings(BaseModel):
    site_name: str = "CML NVR System"
    timezone: str = "Asia/Makassar"
    date_format: str = "DD/MM/YYYY"
    language: str = "id"


class RecordingSettings(BaseModel):
    default_retention_days: int = 30
    default_stream: str = "main"
    segment_duration_seconds: int = 300
    max_file_size_mb: int = 500
    recording_schedule: str = "24h"


class NotificationSettings(BaseModel):
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    email_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notify_camera_offline: bool = False
    notify_disk_full: bool = False
    notify_motion_detected: bool = False


class TestTelegramRequest(BaseModel):
    bot_token: str
    chat_id: str
    message: str = "Test message from CamControl Settings"


class TestEmailRequest(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    message: str = "Test email from CamControl Settings"


class StreamingSettings(BaseModel):
    hls_segment_duration: int = 2
    hls_playlist_size: int = 3
    default_stream_quality: str = "sub"
    transcode_concurrent_max: int = 3
    motion_detection_fps: int = 5


@router.get("")
async def get_settings(_: User = Depends(get_current_admin_user)):
    """Ambil semua pengaturan sistem dari system.yaml."""
    config = await config_manager.get_system_config()
    return config


@router.put("")
async def update_settings(body: dict, _: User = Depends(get_current_admin_user)):
    """Update pengaturan sistem."""
    await config_manager.update_system_config(body)
    return {"status": "updated"}


# --- New sub-settings endpoints ---

@router.get("/general", response_model=GeneralSettings)
async def get_general_settings(_user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    general = config.get("general", {})
    return GeneralSettings(**general)


@router.put("/general")
async def update_general_settings(body: GeneralSettings, _user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    config["general"] = body.model_dump()
    await config_manager.update_system_config(config)
    return {"status": "ok", "message": "General settings updated successfully"}


@router.get("/recording", response_model=RecordingSettings)
async def get_recording_settings(_user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    recording = config.get("recording", {})
    return RecordingSettings(**recording)


@router.put("/recording")
async def update_recording_settings(body: RecordingSettings, _user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    config["recording"] = body.model_dump()
    await config_manager.update_system_config(config)
    return {"status": "ok", "message": "Recording settings updated successfully"}


@router.get("/notification", response_model=NotificationSettings)
async def get_notification_settings(_user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    notif = config.get("notification", {})
    notif_copy = dict(notif)
    if notif_copy.get("smtp_password"):
        notif_copy["smtp_password"] = "******"
    return NotificationSettings(**notif_copy)


@router.put("/notification")
async def update_notification_settings(body: NotificationSettings, _user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    current_notif = config.get("notification", {})
    new_notif = body.model_dump()

    # If the submitted password is masked, preserve the existing password
    if new_notif.get("smtp_password") == "******":
        new_notif["smtp_password"] = current_notif.get("smtp_password", "")

    config["notification"] = new_notif
    await config_manager.update_system_config(config)
    return {"status": "ok", "message": "Notification settings updated successfully"}


@router.post("/notification/test-telegram")
async def test_telegram(body: TestTelegramRequest, _user: User = Depends(get_current_admin_user)):
    url = f"https://api.telegram.org/bot{body.bot_token}/sendMessage"
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"chat_id": body.chat_id, "text": body.message}) as resp:
                if resp.status == 200:
                    return {"success": True, "message": "Test message sent successfully"}
                else:
                    err_text = await resp.text()
                    return {"success": False, "message": f"Telegram API error (status {resp.status}): {err_text}"}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {e}"}


@router.post("/notification/test-email")
async def test_email(body: TestEmailRequest, _user: User = Depends(get_current_admin_user)):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg['From'] = body.smtp_user
    msg['To'] = body.smtp_user
    msg['Subject'] = "CamControl NVR Test Email"
    msg.attach(MIMEText(body.message, 'plain'))

    try:
        if body.smtp_port == 465:
            server = smtplib.SMTP_SSL(body.smtp_host, body.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(body.smtp_host, body.smtp_port, timeout=10)
            server.starttls()

        if body.smtp_user and body.smtp_password:
            server.login(body.smtp_user, body.smtp_password)

        server.sendmail(body.smtp_user, body.smtp_user, msg.as_string())
        server.quit()
        return {"success": True, "message": "Test email sent successfully"}
    except Exception as e:
        return {"success": False, "message": f"SMTP error: {e}"}


@router.get("/streaming", response_model=StreamingSettings)
async def get_streaming_settings(_user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    streaming = config.get("streaming", {})
    return StreamingSettings(**streaming)


@router.put("/streaming")
async def update_streaming_settings(body: StreamingSettings, _user: User = Depends(get_current_admin_user)):
    config = await config_manager.get_system_config()
    config["streaming"] = body.model_dump()
    await config_manager.update_system_config(config)
    return {"status": "ok", "message": "Streaming settings updated successfully"}
