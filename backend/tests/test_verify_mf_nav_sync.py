from datetime import datetime, timezone

from backend.scripts.verify_mf_nav_sync import build_supported_nav_sync_report


def _amfi_row(code: str, name: str, nav: float, nav_date: str) -> dict:
    return {
        "scheme_code": code,
        "scheme_name": name,
        "nav": nav,
        "nav_date": nav_date,
    }


def test_supported_nav_reconciliation_requires_every_supported_amc(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.scripts.verify_mf_nav_sync.SUPPORTED_MF_AMC_MARKERS",
        {"HDFC": ("hdfc",), "PPFAS": ("parag parikh",)},
    )
    report = build_supported_nav_sync_report(
        [_amfi_row("118955", "HDFC Flexi Cap Fund - Direct Plan - Growth", 2297.867, "2026-09-03")],
        {"118955": {"scheme_code": "118955", "nav": 2297.867, "nav_date": "2026-09-03"}},
        now=datetime(2026, 9, 4, 6, tzinfo=timezone.utc),
    )

    assert report["status"] == "out_of_sync"
    assert report["per_amc"]["HDFC"]["status"] == "fresh"
    assert report["per_amc"]["PPFAS"]["status"] == "missing_from_amfi"
    assert "amfi_missing_supported_amc:PPFAS" in report["failures"]


def test_supported_nav_reconciliation_detects_missing_and_stale_snapshot_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.scripts.verify_mf_nav_sync.SUPPORTED_MF_AMC_MARKERS",
        {"HDFC": ("hdfc",), "PPFAS": ("parag parikh",)},
    )
    report = build_supported_nav_sync_report(
        [
            _amfi_row("118955", "HDFC Flexi Cap Fund - Direct Plan - Growth", 2297.867, "2026-09-03"),
            _amfi_row("122639", "Parag Parikh Flexi Cap Fund - Direct Plan - Growth", 90.9964, "2026-09-03"),
        ],
        {"118955": {"scheme_code": "118955", "nav": 2297.867, "nav_date": "2026-08-25"}},
        now=datetime(2026, 9, 4, 6, tzinfo=timezone.utc),
    )

    assert report["missing_snapshot_count"] == 1
    assert report["nav_date_mismatch_count"] == 1
    assert report["synced_scheme_count"] == 0
    assert report["per_amc"]["HDFC"]["status"] == "out_of_sync"
    assert report["per_amc"]["PPFAS"]["status"] == "out_of_sync"
    assert report["needs_retry"] is True


def test_supported_nav_reconciliation_accepts_matching_nav_values(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.scripts.verify_mf_nav_sync.SUPPORTED_MF_AMC_MARKERS",
        {"HDFC": ("hdfc",)},
    )
    report = build_supported_nav_sync_report(
        [_amfi_row("118955", "HDFC Flexi Cap Fund - Direct Plan - Growth", 2297.867, "2026-09-03")],
        {"118955": {"scheme_code": "118955", "nav": "2297.8670", "nav_date": "2026-09-03"}},
        now=datetime(2026, 9, 4, 6, tzinfo=timezone.utc),
    )

    assert report["status"] == "fresh"
    assert report["synced_scheme_count"] == 1
    assert report["freshness"]["status"] == "fresh"
