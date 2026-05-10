"""
Parser: Responsables_modules_IDU.json
Maps each module code to its responsible teacher.
"""

import json
from pathlib import Path


def parse_responsables(path: Path) -> dict[str, dict]:
    """
    Parse the responsables file.

    The file uses PHPMyAdmin export format, table name LNM_enseignant.

    Returns:
        Dict mapping code_module → {"nom": "VERNIER", "prenom": "Flavien"}
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    result = {}
    for bloc in raw:
        if bloc.get("type") == "table" and "data" in bloc:
            for entry in bloc["data"]:
                code = entry["code_module"].strip()
                result[code] = {
                    "nom": entry.get("nom", "").strip(),
                    "prenom": entry.get("prenom", "").strip(),
                }

    return result
