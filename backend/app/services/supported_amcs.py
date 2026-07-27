from __future__ import annotations

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
}

SUPPORTED_AMC_PIPELINE_COPY = ", ".join(
    SUPPORTED_AMC_DISPLAY_NAMES[label] for label in USER_FACING_SUPPORTED_AMCS
)

UNSUPPORTED_MF_AMC_KEYWORDS = (
    "quant",
    "tata",
    "canara",
    "groww",
    "zerodha",
    "bandhan",
    "idfc",
    "franklin",
    "edelweiss",
    "sundaram",
    "lic",
    "pgim",
    "invesco",
    "hsbc",
    "union",
    "baroda",
    "bnp",
    "mahindra",
    "shriram",
    "whiteoak",
    "samco",
    "helios",
    "navi",
    "quantum",
    "taurus",
    "360 one",
    "iifl",
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
    for label, markers in SUPPORTED_MF_AMC_MARKERS.items():
        if any(marker in text for marker in markers):
            return label
    return None
