"""Integration tests for FastAPI app import and route registration."""
import os
import sys
from pathlib import Path

script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if not (project_root / "backend").exists():
    project_root = Path.cwd()

sys.path.insert(0, str(project_root))
os.chdir(str(project_root))


def _collect_route_paths(routes) -> set[str]:
    paths = set()
    for route in routes:
        include_context = getattr(route, "include_context", None)
        prefix = getattr(include_context, "prefix", None)
        if prefix:
            paths.add(prefix)
        path = getattr(route, "path", None)
        if path:
            paths.add(path)
        child_routes = getattr(route, "routes", None)
        if child_routes:
            paths.update(_collect_route_paths(child_routes))
    return paths


def test_app_imports():
    """The FastAPI app should import without dependency or router errors."""
    from backend.api.app import app

    assert app is not None
    assert app.title == "CCTV NVR API"


def test_all_routers_registered():
    """All expected API prefixes should have at least one route."""
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
    registered_paths = _collect_route_paths(app.routes)
    missing = [
        prefix
        for prefix in expected_prefixes
        if not any(path.startswith(prefix) for path in registered_paths)
    ]

    assert missing == []


def test_config_loaded():
    """Configuration should expose core runtime settings."""
    from backend.core.config import settings

    assert settings is not None
    assert hasattr(settings, "db_url")
    assert hasattr(settings, "jwt_secret")


if __name__ == "__main__":
    test_app_imports()
    test_all_routers_registered()
    test_config_loaded()
    print("All integration checks passed")
