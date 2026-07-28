import re

path = "frontend/src/components/camera/CameraImportExport.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "import { useMutation, useQueryClient } from '@tanstack/react-query'",
    "import { useQueryClient } from '@tanstack/react-query'"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done: useMutation removed from import")
