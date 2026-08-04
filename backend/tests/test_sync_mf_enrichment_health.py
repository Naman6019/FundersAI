from backend.app.jobs import sync_mf_enrichment_unified


def test_enrichment_job_fails_when_amfi_parses_zero_rows(monkeypatch, tmp_path) -> None:
    output = tmp_path / "health.json"
    monkeypatch.setattr(
        sync_mf_enrichment_unified.sync_mf_metadata,
        "main",
        lambda: {"status": "degraded", "reason": "amfi_zero_parseable_rows", "counts": {}},
    )
    monkeypatch.setattr("sys.argv", ["sync", "--output", str(output)])

    assert sync_mf_enrichment_unified.main() == 1
    assert "amfi_zero_parseable_rows" in output.read_text(encoding="utf-8")
