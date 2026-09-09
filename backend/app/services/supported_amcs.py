from __future__ import annotations

import re

from app.mf_ingestion.sources.registry import SOURCES


ALL_MF_AMC_MARKERS: dict[str, tuple[str, ...]] = {
    "HDFC": ("hdfc",),
    "SBI": ("sbi",),
    "ICICI": ("icici",),
    "AXIS": ("axis",),
    "PPFAS": ("ppfas", "parag parikh", "parag", "parikh"),
    "NIPPON": ("nippon", "nippon india"),
    "MOTILAL": ("motilal", "motilal oswal"),
    "MIRAE": ("mirae", "mirae asset"),
    "UTI": ("uti",),
    "DSP": ("dsp",),
    "KOTAK": ("kotak",),
    "ABSL": ("aditya birla", "birla sun life", "absl"),
    "TATA": ("tata",),
    "BANDHAN": ("bandhan",),
    "EDELWEISS": ("edelweiss",),
    "INVESCO": ("invesco",),
    "HSBC": ("hsbc",),
    "QUANT": ("quant",),
    "CANARA_ROBECO": ("canara robeco", "canara"),
    "GROWW": ("groww",),
    "ZERODHA": ("zerodha",),
    "BARODA_BNP": ("baroda bnp paribas", "baroda bnp", "baroda pioneer", "baroda"),
    "LIC": ("lic mutual fund", "lic mf", "lic"),
    "SUNDARAM": ("sundaram",),
    "PGIM": ("pgim india", "pgim"),
    "QUANTUM": ("quantum",),
    "BAJAJ_FINSERV": ("bajaj finserv", "bajaj"),
    "CAPITALMIND": ("capitalmind",),
    "ABAKKUS": ("abakkus",),
    "UNIFI": ("unifi",),
    "SHRIRAM": ("shriram",),
    "HELIOS": ("helios",),
    "NJ": ("nj mutual fund", "nj mf", "nj"),
    "OLD_BRIDGE": ("old bridge", "oldbridge"),
    "THREE_SIXTY_ONE": ("360 one", "iifl"),
    "NAVI": ("navi",),
    "TAURUS": ("taurus",),
    "ANGEL_ONE": ("angel one", "angel"),
    "BOI": ("bank of india", "boi"),
    "CHOICE": ("choice",),
    "WEALTH_COMPANY": ("the wealth company", "wealth company"),
    "JIO_BLACKROCK": ("jio blackrock", "jio"),
}

SUPPORTED_MF_AMC_MARKERS: dict[str, tuple[str, ...]] = {
    source.amc_code: ALL_MF_AMC_MARKERS[source.amc_code]
    for source in SOURCES.values()
    if source.runtime_enabled
}

USER_FACING_SUPPORTED_AMCS = tuple(SUPPORTED_MF_AMC_MARKERS)

SUPPORTED_AMC_DISPLAY_NAMES: dict[str, str] = {
    "PPFAS": "PPFAS (Parag Parikh)",
    "ICICI": "ICICI Prudential",
    "HDFC": "HDFC",
    "SBI": "SBI",
    "AXIS": "Axis",
    "NIPPON": "Nippon India",
    "MOTILAL": "Motilal Oswal",
    "MIRAE": "Mirae Asset",
    "UTI": "UTI",
    "DSP": "DSP",
    "KOTAK": "Kotak",
    "ABSL": "Aditya Birla Sun Life",
    "TATA": "Tata",
    "BANDHAN": "Bandhan",
    "EDELWEISS": "Edelweiss",
    "INVESCO": "Invesco",
    "HSBC": "HSBC",
    "QUANT": "Quant",
    "CANARA_ROBECO": "Canara Robeco",
    "GROWW": "Groww",
    "ZERODHA": "Zerodha",
    "BARODA_BNP": "Baroda BNP Paribas",
    "LIC": "LIC",
    "SUNDARAM": "Sundaram",
    "PGIM": "PGIM India",
    "QUANTUM": "Quantum",
    "BAJAJ_FINSERV": "Bajaj Finserv",
    "CAPITALMIND": "Capitalmind",
    "ABAKKUS": "Abakkus",
    "UNIFI": "Unifi",
    "SHRIRAM": "Shriram",
    "HELIOS": "Helios",
    "NJ": "NJ",
    "OLD_BRIDGE": "Old Bridge",
    "THREE_SIXTY_ONE": "360 ONE",
    "NAVI": "Navi",
    "TAURUS": "Taurus",
    "ANGEL_ONE": "Angel One",
    "BOI": "Bank of India",
    "CHOICE": "Choice",
    "WEALTH_COMPANY": "The Wealth Company",
    "JIO_BLACKROCK": "Jio BlackRock",
}

SUPPORTED_AMC_PIPELINE_COPY = ", ".join(
    SUPPORTED_AMC_DISPLAY_NAMES[label] for label in USER_FACING_SUPPORTED_AMCS
)

UNSUPPORTED_MF_AMC_KEYWORDS = (
    "idfc",
    "franklin",
    "union",
    "mahindra",
    "whiteoak",
    "samco",
    "jm financial",
    *(
        marker
        for source in SOURCES.values()
        if not source.runtime_enabled
        for marker in ALL_MF_AMC_MARKERS.get(source.amc_code, ())
    ),
)


def supported_amc_label_from_text(value: object) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    matches: list[tuple[int, str]] = []
    for label, markers in SUPPORTED_MF_AMC_MARKERS.items():
        for marker in markers:
            # Check for word boundary to avoid substring collisions like "quant" in "quantum"
            if re.search(rf"\b{re.escape(marker)}\b", text):
                matches.append((len(marker), label))
    if matches:
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]
    return None
