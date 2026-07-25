import re

path = "frontend/src/pages/Storage/index.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "                  {recordings.map((rec: Recording, i: number) => ("
new = "                  {recordings.map((rec: Recording) => ("

if old not in content:
    print("ERROR: string tidak ditemukan!")
else:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: patch berhasil diterapkan")
