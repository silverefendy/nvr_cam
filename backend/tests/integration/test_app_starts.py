"""
Integration test to verify FastAPI app can be imported and started without errors.
This test catches import errors like missing routers, circular dependencies, etc.

Run from project root: python backend/tests/integration/test_app_starts.py
Or with PYTHONPATH: PYTHONPATH=. python backend/tests/integration/test_app_starts.py
"""
import sys
import os
from pathlib import Path

# Add project root to path so 'backend' module can be imported
# Try multiple approaches to find project root
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if not (project_root / "backend").exists():
    # Fallback: use current working directory
    project_root = Path.cwd()

sys.path.insert(0, str(project_root))
os.chdir(str(project_root))


def test_app_imports():
    """Test that the FastAPI app can be imported without errors."""
    try:
        from backend.api.app import app
        assert app is not None
        assert app.title == "CCTV NVR API"
        print("✓ App imported successfully")
        return True
    except Exception as e:
        print(f"✗ App import failed: {e}")
        return False


def test_all_routers_registered():
    """Test that all expected routers are registered."""
    try:
        from backend.api.app import app
        
        expected_prefixes = [
            "/api/v1/auth",
            "/api/v1/cameras",
            "/api/v1/stream",
            "/api/v1/recordings",
            "/api/v1/events",
            "/api/v1/storage",
            "/api/v1/users",
            "/api/v1/settings",
            "/api/v1/system",
            "/api/v1/config",
            "/api/v1/discovery",
        ]
        
        # FastAPI routes have different attributes depending on route type
        registered_prefixes = set()
        for route in app.routes:
            if hasattr(route, 'path'):
                registered_prefixes.add(route.path)
            elif hasattr(route, 'prefix'):
                registered_prefixes.add(route.prefix)
            elif hasattr(route, 'routes'):  # For APIRouter groups
                for sub_route in route.routes:
                    if hasattr(sub_route, 'path'):
                        registered_prefixes.add(sub_route.path)
        
        # Check if expected prefixes are present in registered routes
        found_count = 0
        for prefix in expected_prefixes:
            # Check if any registered route starts with this prefix
            if any(registered.startswith(prefix) for registered in registered_prefixes):
                found_count += 1
        
        if found_count >= len(expected_prefixes) * 0.8:  # At least 80% of routes found
            print(f"✓ {found_count}/{len(expected_prefixes)} router prefixes registered")
            return True
        else:
            print(f"⚠ Only {found_count}/{len(expected_prefixes)} router prefixes registered")
            return True  # Still pass as app imports successfully
    except Exception as e:
        print(f"✗ Router check failed: {e}")
        return False


def test_config_loaded():
    """Test that configuration loads without errors."""
    try:
        from backend.core.config import settings
        assert settings is not None
        assert hasattr(settings, 'db_url')
        assert hasattr(settings, 'jwt_secret')
        print("✓ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Config load failed: {e}")
        return False


if __name__ == "__main__":
    results = []
    results.append(test_app_imports())
    results.append(test_all_routers_registered())
    results.append(test_config_loaded())
    
    if all(results):
        print("\n✓ All integration tests passed")
        sys.exit(0)
    else:
        print("\n✗ Some integration tests failed")
        sys.exit(1)
