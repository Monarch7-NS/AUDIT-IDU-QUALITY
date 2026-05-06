"""
Parser: dependance_sequence_IDU.json
Reads pedagogical sequencing constraints (DAG of session dependencies).
"""

import json
from pathlib import Path


def parse_dependances(path: Path) -> list[dict]:
    """
    Parse the dependency graph file.

    The file uses PHPMyAdmin export format,
    table name MAQUETTE_dependance_sequence.

    Returns:
        List of dicts, each with keys:
            module_precedent, type_precedent, numero_precedent (int),
            module_suivant, type_suivant, numero_suivant (int)
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    deps = []
    for bloc in raw:
        if bloc.get("type") == "table" and "data" in bloc:
            for entry in bloc["data"]:
                deps.append({
                    "module_precedent": entry["module_precedent"].strip(),
                    "type_precedent": entry["type_precedent"].strip(),
                    "numero_precedent": int(entry["numero_precedent"]),
                    "module_suivant": entry["module_suivant"].strip(),
                    "type_suivant": entry["type_suivant"].strip(),
                    "numero_suivant": int(entry["numero_suivant"]),
                })

    return deps
