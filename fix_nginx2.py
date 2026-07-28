path = "scripts/nginx/cctv.conf"
with open(path, "r") as f:
    content = f.read()

content = content.replace(
    "proxy_pass http://host.docker.internal:8000;",
    "proxy_pass http://api:8000;"
)

with open(path, "w") as f:
    f.write(content)
print("Done: nginx upstream -> api:8000")
