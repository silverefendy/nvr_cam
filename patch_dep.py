content = open('/app/backend/api/dependencies.py').read()
old = '    if current_user.role != "admin":\n        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak - admin only")'
new = '    if current_user.role not in ("admin", "super_admin"):\n        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak - minimal role admin")'
if old in content:
    open('/app/backend/api/dependencies.py', 'w').write(content.replace(old, new))
    print('PATCHED OK')
else:
    print('NOT FOUND')
    print(repr(content))
