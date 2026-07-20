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
