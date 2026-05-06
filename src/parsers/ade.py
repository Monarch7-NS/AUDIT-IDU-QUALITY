"""
Parser: ADECal_IDU3/4/5.json
Reads ADE calendar exports, normalises titles into canonical module codes,
extracts session type (CM/TD/TP), teachers, and computes duration.
"""

import json
import re
from pathlib import Path

from dateutil import parser as dateparser


# Patterns that identify non-IDU events to filter out
_FILTER_PATTERNS = [
    "LANG", "EASI", "DDRS", "SHES", "BDE", "BDS", "Rentrée",
    "REUNION", "Bus_sport", "POLYMPIADES", "ACTIVITE",
    "Cérémonie", "Prévention", "Présentation Stages",
    "RI]", "COM]", "RE]", "Math500", "MATH501", "MATH641",
    "EEAT", "SOUTIEN",
]

# Regex to extract the canonical module code from a Title
_CODE_RE = re.compile(
    r"((?:INFO|DATA|ISOC|MATH|PROJ)\d{3})_?"
)

# Regex to detect session type from Title
_TYPE_PATTERNS = [
    (re.compile(r"_CM|_cm", re.IGNORECASE), "CM"),
    (re.compile(r"_TP|TPG\d|_tp", re.IGNORECASE), "TP"),
    (re.compile(r"_TD|TDG|_td", re.IGNORECASE), "TD"),
    (re.compile(r"_ET_|EXAMEN|_ET$", re.IGNORECASE), "Exam"),
    (re.compile(r"PROJ|_P\d", re.IGNORECASE), "PROJ"),
]


def parse_ade(
    path: Path,
    promo: str,
    known_codes: set[str],
) -> list[dict]:
    """
    Parse an ADE calendar export file.

    Args:
        path:         Path to ADECal_IDUx.json
        promo:        Promo identifier (e.g. "IDU3")
        known_codes:  Set of valid module codes from the maquette

    Returns:
        List of event dicts with keys:
            title, code, session_type, start, end, duration_h,
            location, teachers, groups, promo, description
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    events = []
    for entry in raw:
        title = entry.get("Title", "")

        # Skip non-IDU events
        if _should_filter(title, entry.get("Description", "")):
            continue

        code = _extract_code(title, known_codes)
        session_type = _extract_session_type(title, entry.get("Description", ""))

        start = dateparser.parse(entry["Starts"])
        end = dateparser.parse(entry["Ends"])
        duration_h = (end - start).total_seconds() / 3600

        teachers = _extract_teachers(entry.get("Description", ""))
        location = entry.get("Location", "").strip()

        events.append({
            "title": title,
            "code": code,
            "session_type": session_type,
            "start": start,
            "end": end,
            "duration_h": round(duration_h, 2),
            "location": location,
            "teachers": teachers,
            "groups": _extract_groups(entry.get("Description", "")),
            "promo": promo,
            "description": entry.get("Description", ""),
        })

    return events


def _should_filter(title: str, desc: str) -> bool:
    """Return True if this event is not an IDU teaching session."""
    combined = title + " " + desc
    for pattern in _FILTER_PATTERNS:
        if pattern in combined:
            return True
    return False


def _extract_code(title: str, known_codes: set[str]) -> str | None:
    """
    Extract the canonical module code from the ADE title.
    Handles non-standard titles like INFO631_INGE_TDG → INFO631_IDU
    """
    match = _CODE_RE.search(title)
    if not match:
        return None

    base_code = match.group(1)

    # Try exact match with known suffixes
    for suffix in ("_IDU", "_PACY"):
        candidate = base_code + suffix
        if candidate in known_codes:
            return candidate

    # If no suffix match, return base code + _IDU as default
    return base_code + "_IDU"


def _extract_session_type(title: str, desc: str) -> str:
    """
    Determine session type from ADE title and description.
    Priority: description parenthetical > title patterns.
    """
    # Try description first: look for (CM), (TD), (TP), (EXAMEN), (PROJET)
    desc_match = re.search(r"\((\w+)\)", desc)
    if desc_match:
        dtype = desc_match.group(1).upper()
        if dtype in ("CM", "TD", "TP"):
            return dtype
        if dtype in ("EXAMEN",):
            return "Exam"
        if dtype in ("PROJET",):
            return "PROJ"

    # Fall back to title-based detection
    for pattern, stype in _TYPE_PATTERNS:
        if pattern.search(title):
            return stype

    return "UNKNOWN"


def _extract_teachers(desc: str) -> list[str]:
    """
    Extract teacher names from the ADE description block.
    Teachers are listed after the group lines and before the empty lines.
    Pattern: LASTNAME FIRSTNAME (all caps first word)
    """
    teachers = []
    lines = desc.split("\n")
    # Known group prefixes to skip
    group_prefixes = (
        "IDU-", "MECA-", "SNI-", "EPU-", "BAT_", "EIT", "MC",
        "sem-", "examen_", "Kit ", "Scolarité",
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("(Exporté"):
            break
        if any(line.startswith(prefix) for prefix in group_prefixes):
            continue
        # A teacher name: at least two words, first word is all uppercase
        words = line.split()
        if len(words) >= 2 and words[0].isupper() and words[0].isalpha():
            teachers.append(line)

    return teachers


def _extract_groups(desc: str) -> list[str]:
    """Extract group identifiers from ADE description."""
    groups = []
    group_prefixes = ("IDU-", "MECA-", "SNI-", "EPU-")
    for line in desc.split("\n"):
        line = line.strip()
        if any(line.startswith(prefix) for prefix in group_prefixes):
            groups.append(line)
    return groups
