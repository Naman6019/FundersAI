from __future__ import annotations

SUPPORTED_MF_AMC_MARKERS: dict[str, tuple[str, ...]] = {
    "HDFC": ("hdfc",),
    "SBI": ("sbi",),
    "ICICI": ("icici",),
    "AXIS": ("axis",),
    "PPFAS": ("ppfas", "parag parikh", "parag", "parikh"),
    "NIPPON": ("nippon", "nippon india"),
}

USER_FACING_SUPPORTED_AMCS = tuple(SUPPORTED_MF_AMC_MARKERS)

SUPPORTED_AMC_DISPLAY_NAMES: dict[str, str] = {
    "PPFAS": "PPFAS (Parag Parikh)",
    "ICICI": "ICICI Prudential",
    "HDFC": "HDFC",
    "SBI": "SBI",
    "AXIS": "Axis",
    "NIPPON": "Nippon India",
}

SUPPORTED_AMC_PIPELINE_COPY = ", ".join(
    SUPPORTED_AMC_DISPLAY_NAMES[label] for label in ("PPFAS", "ICICI", "HDFC", "SBI", "AXIS", "NIPPON")
)

UNSUPPORTED_MF_AMC_KEYWORDS = (
    "quant",
    "kotak",
    "mirae",
    "uti",
    "dsp",
    "tata",
    "motilal",
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
)


def supported_amc_label_from_text(value: object) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    for label, markers in SUPPORTED_MF_AMC_MARKERS.items():
        if any(marker in text for marker in markers):
            return label
    return None
