"""
Tests for parsers: maquette, dependances, responsables.
Uses synthetic data to avoid dependency on real data files.
"""

import json
import pytest
from pathlib import Path
from src.parsers.maquette import parse_maquette
from src.parsers.dependances import parse_dependances
from src.parsers.responsables import parse_responsables


# ── Fixtures ──────────────────────────────────────────────────────────────── #

MAQUETTE_SAMPLE = [
    {"type": "header"},
    {"type": "database"},
    {
        "type": "table",
        "name": "MAQUETTE_module",
        "data": [
            {
                "code_module": "INFO631_IDU",
                "nom": "Algorithmique avancée",
                "ects": "3",
                "cm": "15",
                "td": "10",
                "tp": "0",
            },
            {
                "code_module": "DATA501_IDU",
                "nom": "Bases de données",
                "ects": "4",
                "cm": "20",
                "td": "15",
                "tp": "5",
            },
        ],
    },
]

DEPENDANCES_SAMPLE = [
    {
        "module_precedent": "INFO631_IDU",
        "type_precedent": "CM",
        "numero_precedent": 1,
        "module_suivant": "INFO631_IDU",
        "type_suivant": "TD",
        "numero_suivant": 1,
    }
]

RESPONSABLES_SAMPLE = [
    {"code_module": "INFO631_IDU", "nom": "Dupont", "prenom": "Alice"},
    {"code_module": "DATA501_IDU", "nom": "Martin", "prenom": "Bob"},
]


@pytest.fixture()
def tmp_maquette(tmp_path):
    p = tmp_path / "MAQUETTE_IDU.json"
    p.write_text(json.dumps(MAQUETTE_SAMPLE), encoding="utf-8")
    return p


@pytest.fixture()
def tmp_dependances(tmp_path):
    p = tmp_path / "dependances.json"
    p.write_text(json.dumps(DEPENDANCES_SAMPLE), encoding="utf-8")
    return p


@pytest.fixture()
def tmp_responsables(tmp_path):
    p = tmp_path / "responsables.json"
    p.write_text(json.dumps(RESPONSABLES_SAMPLE), encoding="utf-8")
    return p


# ── Tests: parse_maquette ──────────────────────────────────────────────────── #

class TestParseMaquette:
    def test_returns_list(self, tmp_maquette):
        result = parse_maquette(tmp_maquette)
        assert isinstance(result, list)

    def test_correct_count(self, tmp_maquette):
        result = parse_maquette(tmp_maquette)
        assert len(result) == 2

    def test_fields_present(self, tmp_maquette):
        result = parse_maquette(tmp_maquette)
        module = result[0]
        for field in ("code_module", "nom", "ects", "cm", "td", "tp"):
            assert field in module, f"Missing field: {field}"

    def test_numeric_conversion(self, tmp_maquette):
        result = parse_maquette(tmp_maquette)
        mod = result[0]
        assert isinstance(mod["cm"], float)
        assert isinstance(mod["td"], float)
        assert isinstance(mod["tp"], float)
        assert mod["cm"] == 15.0
        assert mod["td"] == 10.0
        assert mod["tp"] == 0.0

    def test_code_stripped(self, tmp_maquette):
        result = parse_maquette(tmp_maquette)
        assert result[0]["code_module"] == "INFO631_IDU"

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps([]), encoding="utf-8")
        result = parse_maquette(p)
        assert result == []


# ── Tests: parse_dependances ───────────────────────────────────────────────── #

class TestParseDependances:
    def test_returns_list(self, tmp_dependances):
        result = parse_dependances(tmp_dependances)
        assert isinstance(result, list)

    def test_correct_count(self, tmp_dependances):
        result = parse_dependances(tmp_dependances)
        assert len(result) == 1

    def test_fields_present(self, tmp_dependances):
        result = parse_dependances(tmp_dependances)
        dep = result[0]
        for field in (
            "module_precedent", "type_precedent", "numero_precedent",
            "module_suivant", "type_suivant", "numero_suivant",
        ):
            assert field in dep, f"Missing field: {field}"

    def test_values(self, tmp_dependances):
        result = parse_dependances(tmp_dependances)
        dep = result[0]
        assert dep["module_precedent"] == "INFO631_IDU"
        assert dep["type_precedent"] == "CM"
        assert dep["numero_precedent"] == 1

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps([]), encoding="utf-8")
        result = parse_dependances(p)
        assert result == []


# ── Tests: parse_responsables ──────────────────────────────────────────────── #

class TestParseResponsables:
    def test_returns_dict(self, tmp_responsables):
        result = parse_responsables(tmp_responsables)
        assert isinstance(result, dict)

    def test_correct_keys(self, tmp_responsables):
        result = parse_responsables(tmp_responsables)
        assert "INFO631_IDU" in result
        assert "DATA501_IDU" in result

    def test_correct_values(self, tmp_responsables):
        result = parse_responsables(tmp_responsables)
        assert "Dupont" in result["INFO631_IDU"] or "Alice" in result["INFO631_IDU"]

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps([]), encoding="utf-8")
        result = parse_responsables(p)
        assert isinstance(result, dict)
        assert len(result) == 0
