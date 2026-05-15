from __future__ import annotations

import pandas as pd

from app.mf_ingestion.parsers.excel_parser import ExcelParser


def test_excel_parser_falls_back_to_xlrd_for_xls(monkeypatch):
    calls: list[object] = []

    def _fake_read_excel(_source, sheet_name=None, engine=None):
        calls.append(engine)
        if engine == "openpyxl":
            raise RuntimeError("not_zip")
        return {"Sheet1": pd.DataFrame({"a": [1]})}

    monkeypatch.setattr(pd, "read_excel", _fake_read_excel)
    parser = ExcelParser()
    frames = parser.parse_all_sheets("sample.xls")

    assert len(frames) == 1
    assert calls[:2] == ["openpyxl", "xlrd"]
