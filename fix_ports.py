path = "docker-compose.yml"
with open(path, "r") as f:
    content = f.read()

old = '    depends_on:\n      db:\n        condition: service_healthy\n    restart: unless-stopped'
new = '    ports:\n      - "8000:8000"\n    depends_on:\n      db:\n        condition: service_healthy\n    restart: unless-stopped'

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("Done: ports 8000:8000 added")
else:
    print("Pattern not found - cek manual")
