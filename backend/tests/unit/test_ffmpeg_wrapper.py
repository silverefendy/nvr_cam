"""Unit test untuk FFmpeg wrapper."""
import pytest
from services.recorder.ffmpeg_wrapper import build_record_command, build_hls_command


def test_build_record_command():
    cmd = build_record_command("rtsp://cam/stream", "/tmp/%H.mp4", 3600)
    assert "ffmpeg" in cmd
    assert "-c" in cmd
    assert "copy" in cmd
    assert "3600" in cmd


def test_build_hls_command():
    cmd = build_hls_command("rtsp://cam/stream", "/tmp/hls")
    assert "hls" in cmd
    assert "/tmp/hls/index.m3u8" in cmd
