"""License-plate text normalisation, country presets and validation.

The plate *format* is configurable because plates differ by country.  A preset
name (or a fully custom regex) is stored in the settings table and applied to
every OCR reading before it is accepted.
"""
from __future__ import annotations

import re

# preset name -> (human description, regex applied to the NORMALISED plate,
#                i.e. uppercase A-Z0-9 only, no spaces/symbols)
PRESETS: dict[str, tuple[str, str]] = {
    "generic": ("Any plate (letters+digits, 4-10 chars)", r"^(?=.*\d)(?=.*[A-Z])[A-Z0-9]{4,10}$"),
    "kenya": ("Kenya (e.g. KDA 445J)", r"^K[A-Z]{2}\d{3}[A-Z]?$"),
    "tanzania": ("Tanzania (e.g. T 372 BAA)", r"^T\d{3}[A-Z]{3}$"),
    "uganda": ("Uganda (e.g. UAG 445B)", r"^U[A-Z]{1,2}\d{3}[A-Z]?$"),
    "uk": ("United Kingdom (e.g. AB12 CDE)", r"^[A-Z]{2}\d{2}[A-Z]{3}$"),
    "eu": ("Europe (e.g. B-AB 1234, 12AB34567)", r"^(?=.*\d)(?=.*[A-Z])[A-Z0-9]{4,10}$"),
    "custom": ("Custom regex (Settings)", r""),  # filled from settings
}

# Characters that frequently get confused by OCR on plates, used only for
# logging/diagnostics — normalisation never "fixes" text automatically.
_COMMON_CONFUSIONS = {"0O": ("0", "O"), "1I": ("1", "I"), "8B": ("8", "B"), "5S": ("5", "S")}


def normalize(raw: str) -> str:
    """Uppercase, keep A-Z and 0-9 only (drops spaces, dashes, dots...)."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def looks_like_plate(text: str, min_len: int = 4, max_len: int = 10) -> bool:
    """Cheap sanity check before any country-specific validation."""
    n = normalize(text)
    return min_len <= len(n) <= max_len and any(c.isdigit() for c in n) and any(c.isalpha() for c in n)


def validate(plate: str, preset: str = "generic", custom_regex: str = "") -> bool:
    """True when ``plate`` (already normalised) matches the configured format."""
    if preset == "custom":
        pattern = custom_regex or PRESETS["generic"][1]
    else:
        pattern = PRESETS.get(preset, PRESETS["generic"])[1]
    try:
        return re.fullmatch(pattern, plate) is not None
    except re.error:
        return False


def preset_names() -> list[str]:
    return list(PRESETS.keys())


def preset_description(name: str) -> str:
    return PRESETS.get(name, ("unknown", ""))[0]
