#!/usr/bin/env python3
"""
Setup database - create first admin user if none exists.
Safe to run multiple times (idempotent).
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import settings
from backend.core.security import get_password_hash
from backend.db.base import AsyncSessionLocal
from backend.db.models.user import User
from backend.db.repositories.user_repo import UserRepository
from sqlalchemy import select


async def create_admin_user():
    """Create admin user if it doesn't exist."""
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        
        # Check if any admin exists
        result = await db.execute(
            select(User).where(User.role == "admin")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"✓ Admin user already exists: {existing_admin.username}")
            return
        
        # Create default admin user
        admin = User(
            username="admin",
            password_hash=get_password_hash("nvr1234"),
            role="admin",
            full_name="System Administrator",
            email=None,
            is_active=True
        )
        
        await repo.create(admin)
        await db.commit()
        
        print("✓ Created admin user:")
        print("  Username: admin")
        print("  Password: nvr1234")
        print("  Role: admin")
        print("\n⚠️  IMPORTANT: Change the default password after first login!")


async def main():
    try:
        print("Connecting to database...")
        print(f"  Host: {settings.db_host}")
        print(f"  Database: {settings.db_name}")
        print(f"  User: {settings.db_user}")
        
        await create_admin_user()
        print("\n✓ Database setup completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
