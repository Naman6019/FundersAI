from __future__ import annotations

from dataclasses import dataclass
from app.mf_ingestion.sources.registry import capability_keys

PARSER_VERSION = "mf_ingestion_v1"

AMC_PPFAS = "ppfas"
AMC_MIRAE = "mirae"
AMC_HDFC = "hdfc"
AMC_ICICI = "icici"
AMC_SBI = "sbi"
AMC_AXIS = "axis"
AMC_MOTILAL = "motilal"
AMC_NIPPON = "nippon"
AMC_UTI = "uti"
AMC_DSP = "dsp"
AMC_KOTAK = "kotak"
AMC_ADITYA_BIRLA = "aditya_birla"
AMC_TATA = "tata"
AMC_BANDHAN = "bandhan"
AMC_EDELWEISS = "edelweiss"
AMC_INVESCO = "invesco"
AMC_HSBC = "hsbc"
AMC_QUANT = "quant"
AMC_CANARA_ROBECO = "canara_robeco"
AMC_GROWW = "groww"
AMC_ZERODHA = "zerodha"
AMC_BARODA_BNP = "baroda_bnp"
AMC_LIC = "lic"
AMC_SUNDARAM = "sundaram"
AMC_PGIM = "pgim"
AMC_QUANTUM = "quantum"
AMC_BAJAJ_FINSERV = "bajaj_finserv"
AMC_CAPITALMIND = "capitalmind"
AMC_ABAKKUS = "abakkus"
AMC_UNIFI = "unifi"
AMC_SHRIRAM = "shriram"
AMC_HELIOS = "helios"
AMC_NJ = "nj"
AMC_OLD_BRIDGE = "old_bridge"
AMC_360_ONE = "360_one"
AMC_NAVI = "navi"
AMC_TAURUS = "taurus"
AMC_ANGEL_ONE = "angel_one"
AMC_BOI = "boi"
AMC_CHOICE = "choice"
AMC_WEALTH_COMPANY = "wealth_company"
AMC_JIO_BLACKROCK = "jio_blackrock"


SUPPORTED_AMCS = list(capability_keys("portfolio_parser_enabled"))

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
