path = "docker-compose.yml"
with open(path, "r") as f:
    content = f.read()

# Hapus network_mode: host
content = content.replace("    network_mode: host\n", "")

# Kembalikan nginx proxy ke nama service "api"
with open(path, "w") as f:
    f.write(content)
print("Done: network_mode: host removed")
