path = "backend/api/routers/config.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

old = '''        return {
            "success": True,
            "message": "Koneksi RTSP berhasil",
            "codec": codec,
            "resolution": f"{width}x{height}" if width and height else None,
            "fps": fps,
        }'''

new = '''        # Konversi fps dari format fraction "30000/1001" atau "5/1" ke float
        fps_float = None
        if fps:
            try:
                if "/" in str(fps):
                    num, den = fps.split("/")
                    fps_float = round(float(num) / float(den), 2) if float(den) != 0 else None
                else:
                    fps_float = float(fps)
            except Exception:
                fps_float = None

        return {
            "success": True,
            "message": "Koneksi RTSP berhasil",
            "codec": codec,
            "resolution": f"{width}x{height}" if width and height else None,
            "fps": fps_float,
        }'''

if old in content:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("PATCHED OK")
else:
    print("NOT FOUND - cek manual")
