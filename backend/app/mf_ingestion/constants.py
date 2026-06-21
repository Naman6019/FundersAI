from __future__ import annotations

from dataclasses import dataclass

PARSER_VERSION = "mf_ingestion_v1"

AMC_PPFAS = "ppfas"
AMC_MIRAE = "mirae"
AMC_HDFC = "hdfc"
AMC_ICICI = "icici"
AMC_SBI = "sbi"
AMC_AXIS = "axis"
AMC_MOTILAL = "motilal"
AMC_NIPPON = "nippon"


SUPPORTED_AMCS = [
    AMC_PPFAS,
    AMC_MIRAE,
    AMC_HDFC,
    AMC_ICICI,
    AMC_SBI,
    AMC_AXIS,
    AMC_MOTILAL,
    AMC_NIPPON,
]

EXCEL_EXTENSIONS = {".xls", ".xlsx", ".xlsm"}
PDF_EXTENSIONS = {".pdf"}
HTML_EXTENSIONS = {".html", ".htm"}
SUPPORTED_DOC_EXTENSIONS = EXCEL_EXTENSIONS | PDF_EXTENSIONS | HTML_EXTENSIONS

VALIDATION_STATUS_VALID = "valid"
VALIDATION_STATUS_REVIEW = "needs_review"
VALIDATION_STATUS_INVALID = "invalid"

DEFAULT_SCHEME_MATCH_THRESHOLD = 90
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 80

PPFAS_FLEXI_CAP_SCHEME_CANONICAL = "Parag Parikh Flexi Cap Fund"

@dataclass(frozen=True)
class ReportMonthWindow:
    lower_bound_pct: float = 90.0
    upper_bound_pct: float = 110.0
