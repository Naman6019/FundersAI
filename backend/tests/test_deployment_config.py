from pathlib import Path


def test_render_uses_fastapi_runtime_entrypoint():
    backend_root = Path(__file__).parents[1]
    render_config = (backend_root / "render.yaml").read_text(encoding="utf-8")

    assert "uvicorn app.main:app" in render_config
    assert "uvicorn api.index:app" not in render_config


def test_destructive_nav_drop_is_not_an_automatic_migration():
    backend_root = Path(__file__).parents[1]
    automatic_migrations = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (backend_root / "migrations").glob("*.sql")
    )

    assert "DROP TABLE public.mutual_fund_nav_history" not in automatic_migrations


def test_provider_response_cache_is_service_role_only():
    backend_root = Path(__file__).parents[1]
    migration = (
        backend_root / "migrations" / "20260721_harden_provider_response_cache_rls.sql"
    ).read_text(encoding="utf-8").lower()

    assert "alter table public.provider_response_cache enable row level security" in migration
    assert "revoke all on table public.provider_response_cache from anon" in migration
    assert "revoke all on table public.provider_response_cache from authenticated" in migration
    assert "grant select, insert, update, delete on table public.provider_response_cache to service_role" in migration


def test_backend_cors_uses_supported_production_domain():
    backend_root = Path(__file__).parents[1]
    source = (backend_root / "app" / "main.py").read_text(encoding="utf-8")

    assert '"https://fundersai.co.in"' in source
    assert '"https://www.fundersai.co.in"' in source
    assert '"https://fundersai.com"' not in source
    assert '"https://www.fundersai.com"' not in source
