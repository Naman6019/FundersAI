from __future__ import annotations

from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"


def test_main_contains_no_business_route_endpoints():
    source = (APP_DIR / "main.py").read_text(encoding="utf-8")
    forbidden = ("@app.get", "@app.post", "@app.put", "@app.delete", "@app.patch")
    assert not any(token in source for token in forbidden)


def test_routes_do_not_access_supabase_directly():
    for path in (APP_DIR / "routes").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "from app.database" not in source, path
        assert "supabase.table" not in source, path


def test_route_facing_services_do_not_import_database_client():
    service_names = [
        "admin_service.py",
        "asset_resolver.py",
        "chat_service.py",
        "compare_data_service.py",
        "data_health_service.py",
        "fund_category_service.py",
        "provider_usage_service.py",
    ]
    for name in service_names:
        source = (APP_DIR / "services" / name).read_text(encoding="utf-8")
        assert "from app.database" not in source, name
        assert "supabase.table" not in source, name


def test_route_facing_services_do_not_raise_http_exceptions():
    service_names = [
        "admin_service.py",
        "asset_resolver.py",
        "chat_service.py",
        "compare_data_service.py",
        "data_health_service.py",
        "fund_category_service.py",
        "provider_usage_service.py",
    ]
    for name in service_names:
        source = (APP_DIR / "services" / name).read_text(encoding="utf-8")
        assert "HTTPException" not in source, name
