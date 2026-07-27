from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.mf_ingestion.parsers.factsheet_parser import (
    FactsheetParser,
    _find_scheme_sections,
    _extract_vector_riskometer_levels,
    _preprocess_factsheet_text,
    filter_factsheet_records_for_amc,
)
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Inspect bounded factsheet text around a scheme or field label.")
    parser.add_argument("--file", required=True)
    parser.add_argument("--scheme")
    parser.add_argument("--pattern", default="AUM|TER|Expense|Riskometer|risk of the scheme")
    parser.add_argument("--max-chars", type=int, default=8000)
    parser.add_argument("--summary-amc", help="Return field coverage for this AMC instead of text excerpts.")
    parser.add_argument("--vector-risk-debug", action="store_true")
    args = parser.parse_args()

    path = Path(args.file).resolve()
    if args.vector_risk_debug:
        diagnostics: list[dict[str, object]] = []
        levels = _extract_vector_riskometer_levels(str(path), diagnostics=diagnostics)
        print(
            json.dumps(
                {"file": str(path), "risk_levels": levels, "pages": diagnostics},
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.summary_amc:
        records = filter_factsheet_records_for_amc(
            FactsheetParser().parse(
                str(path),
                ParseContext(source_document_id="local-inspection", source_url=str(path), report_month=None),
            ),
            args.summary_amc,
        )
        fields = ("aum", "expense_ratio", "benchmark", "fund_manager", "risk_level")
        counts = {
            field: sum(1 for record in records if getattr(record, field, None) not in (None, ""))
            for field in fields
        }
        total = len(records)
        print(
            json.dumps(
                {
                    "file": str(path),
                    "record_count": total,
                    "field_counts": counts,
                    "field_coverage_percent": {
                        field: round(count / total * 100.0, 2) if total else 0.0
                        for field, count in counts.items()
                    },
                    "missing_sample_schemes": {
                        field: [
                            str(record.scheme_name)
                            for record in records
                            if getattr(record, field, None) in (None, "")
                        ][:10]
                        for field in fields
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    text = _preprocess_factsheet_text(PDFTextParser().extract_text(str(path)))
    output: dict[str, object] = {"file": str(path)}

    if args.scheme:
        requested = " ".join(args.scheme.lower().split())
        matches = [
            (name, start, end)
            for name, start, end in _find_scheme_sections(text)
            if requested in " ".join(name.lower().split())
        ]
        output["sections"] = [
            {
                "scheme_name": name,
                "text": text[start : min(end, start + max(500, args.max_chars))],
            }
            for name, start, end in matches[:5]
        ]
    else:
        pattern = re.compile(args.pattern, flags=re.IGNORECASE)
        hits: list[dict[str, object]] = []
        for match in pattern.finditer(text):
            start = max(0, match.start() - 500)
            end = min(len(text), match.end() + 1000)
            hits.append({"offset": match.start(), "text": text[start:end]})
            if len(hits) >= 20:
                break
        output["pattern"] = args.pattern
        output["matches"] = hits

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
