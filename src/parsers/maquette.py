"""
Parser: MAQUETTE_IDU.json
Reads the official curriculum definition exported from PHPMyAdmin.
Returns a list of module dicts with normalised numeric fields.
"""

import json
from pathlib import Path


def parse_maquette(path: Path) -> list[dict]:
    """
    Parse the MAQUETTE_IDU.json file.

    The file uses the PHPMyAdmin JSON export format:
        [ {header}, {database}, {type:"table", name:"MAQUETTE_module", data:[...]} ]

    Returns:
        List of dicts, each with keys:
            code_module, nom, ects, cm, td, tp  (all hours as float)
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    # Find the table block containing module data
    modules = []
    for bloc in raw:
        if bloc.get("type") == "table" and "data" in bloc:
            for entry in bloc["data"]:
                modules.append({
                    "code_module": entry["code_module"].strip(),
                    "nom": entry.get("nom", "").strip(),
                    "ects": float(entry.get("ects", 0)),
                    "cm": float(entry.get("cm", 0)),
                    "td": float(entry.get("td", 0)),
                    "tp": float(entry.get("tp", 0)),
                })

    return modules
