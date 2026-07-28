path = "docker-compose.yml"
with open(path, "r") as f:
    content = f.read()

# Tambah ports mapping ke api service
old = "    # ports: tidak dipakai saat network_mode: host\n    # Port API (8000) langsung tersedia di host"
new = "    ports:\n      - \"8000:8000\""

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("Done: ports 8000:8000 added to api service")
else:
    print("Pattern not found - edit manually")
