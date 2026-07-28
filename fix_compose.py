path = "docker-compose.yml"
with open(path, "r") as f:
    content = f.read()

old = """  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile.frontend.prod
    container_name: cctv_web
    ports:
      - "3000:80"
    volumes:
      - hls_data:/var/lib/nvr_cam/hls:ro
      - snapshot_data:/var/lib/nvr_cam/snapshots:ro
    depends_on:
      - api
    restart: unless-stopped"""

new = """  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile.frontend.prod
    container_name: cctv_web
    ports:
      - "3000:80"
    volumes:
      - hls_data:/var/lib/nvr_cam/hls:ro
      - snapshot_data:/var/lib/nvr_cam/snapshots:ro
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - api
    restart: unless-stopped"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("Done: extra_hosts added to frontend service")
else:
    print("ERROR: pattern not found, edit docker-compose.yml manually")
