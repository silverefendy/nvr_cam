import re

path = "backend/api/dependencies.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

old = '''async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency untuk user dengan role admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak - admin only")
    return current_user'''

new = '''async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency untuk user dengan role admin atau super_admin."""
    from backend.api.middleware.auth import ROLE_HIERARCHY
    user_level = ROLE_HIERARCHY.get(current_user.role, 0)
    admin_level = ROLE_HIERARCHY.get("admin", 4)
    if user_level < admin_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak - minimal role admin"
        )
    return current_user'''

if old in content:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace(old, new))
    print("PATCHED OK")
else:
    print("Tidak perlu patch - file sudah versi baru")
