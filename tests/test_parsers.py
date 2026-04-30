"""
tests/test_parsers.py
=====================
Tests unitaires pour src/parsers/parse_all.py
Couvre : parse_ade_title, _parse_location, get_famille_hors_maquette,
         deduplicate_parallel_groups, build_parse_report
"""

import re
import pandas as pd
import pytest

from src.parsers.parse_all import (
    parse_ade_title,
    _parse_location,
    _parse_description,
    get_famille_manquante,
    is_lv2_optionnel,
    deduplicate_parallel_groups,
    build_parse_report,
    TYPE_MAP,
    ADE_TO_MAQUETTE,
    LV2_CODES,
)


# ─────────────────────────────────────────────────────────────
# parse_ade_title
# ─────────────────────────────────────────────────────────────

class TestParseAdeTitle:

    def test_format_code_type_simple(self):
        code, typ, is_exam, is_par = parse_ade_title("DATA931_CM")
        assert code == "DATA931"
        assert typ  == "CM"
        assert not is_exam
        assert not is_par

    def test_format_code_tdg(self):
        code, typ, is_exam, is_par = parse_ade_title("INFO631_INGE_TDG")
        assert code == "INFO631"
        assert typ  == "TD"

    def test_format_type_code_avec_espace(self):
        code, typ, is_exam, is_par = parse_ade_title("CM INFO931")
        assert code == "INFO931"
        assert typ  == "CM"
        assert not is_exam

    def test_format_proj_idu(self):
        code, typ, is_exam, is_par = parse_ade_title("PROJ631_IDU_01_4H1")
        assert code == "PROJ631"
        assert typ  == "PROJ"

    def test_format_atelier_groupe_parallele(self):
        code, typ, is_exam, is_par = parse_ade_title("INFO633_A01_G1")
        assert code == "INFO633"
        assert typ  == "TD"
        assert is_par is True

    def test_format_projet_groupe_parallele(self):
        code, typ, is_exam, is_par = parse_ade_title("INFO633_P01_G2")
        assert code == "INFO633"
        assert typ  == "TP"
        assert is_par is True

    def test_format_controle_continu(self):
        code, typ, is_exam, is_par = parse_ade_title("INFO634_CC1")
        assert code == "INFO634"
        assert typ  == "EXAM"
        assert is_exam is True

    def test_bruit_bde_ignore(self):
        code, typ, is_exam, is_par = parse_ade_title("BDE Soirée étudiants")
        assert code is None
        assert typ  is None

    def test_bruit_rentree_ignore(self):
        code, typ, _, _ = parse_ade_title("Rentrée IDU 2024")
        assert code is None

    def test_exam_keyword_rattrap(self):
        code, typ, is_exam, _ = parse_ade_title("INFO632_RATTRAP")
        assert code == "INFO632"
        assert is_exam is True

    def test_titre_inconnu_retourne_none(self):
        code, typ, _, _ = parse_ade_title("Séminaire professionnel")
        assert code is None

    def test_tp_type(self):
        code, typ, _, _ = parse_ade_title("INFO632_TP")
        assert code == "INFO632"
        assert typ  == "TP"

    def test_exam_et(self):
        code, typ, is_exam, _ = parse_ade_title("INFO731_ET")
        assert typ == "EXAM"
        assert is_exam is True

    def test_td_space_format(self):
        code, typ, _, _ = parse_ade_title("TD INFO734")
        assert code == "INFO734"
        assert typ  == "TD"


# ─────────────────────────────────────────────────────────────
# _parse_location
# ─────────────────────────────────────────────────────────────

class TestParseLocation:

    def test_salle_avec_capacite(self):
        salle, cap = _parse_location("A-C217 (24pl.)")
        assert salle == "A-C217"
        assert cap   == 24

    def test_salle_sans_capacite(self):
        salle, cap = _parse_location("Amphi A")
        assert salle == "Amphi A"
        assert cap   is None

    def test_location_vide(self):
        salle, cap = _parse_location("")
        assert salle == ""
        assert cap   is None

    def test_capacite_grande_salle(self):
        salle, cap = _parse_location("Amphi Jules Verne (200pl.)")
        assert cap == 200


# ─────────────────────────────────────────────────────────────
# get_famille_hors_maquette
# ─────────────────────────────────────────────────────────────

class TestModulesManquants:

    def test_lang_reconnu_comme_manquant(self):
        assert get_famille_manquante("LANG500") == "Langues vivantes"

    def test_easi_reconnu_comme_manquant(self):
        assert "Électronique" in get_famille_manquante("EASI501")

    def test_info_present_dans_maquette(self):
        """INFO631 est dans la maquette, donc pas marqué manquant."""
        assert get_famille_manquante("INFO631") is None

    def test_none_code(self):
        assert get_famille_manquante(None) is None

    def test_math_reconnu_comme_manquant(self):
        assert "Mathématiques" in get_famille_manquante("MATH501")

    def test_ddrs_reconnu_comme_manquant(self):
        assert "Développement Durable" in get_famille_manquante("DDRS501")


class TestLv2Conditionnel:

    def test_lv2_codes_detectes(self):
        assert is_lv2_optionnel("LANG602") is True
        assert is_lv2_optionnel("LANG702") is True
        assert is_lv2_optionnel("LANG802") is True

    def test_lv1_pas_lv2(self):
        assert is_lv2_optionnel("LANG501") is False
        assert is_lv2_optionnel("LANG601") is False
        assert is_lv2_optionnel("LANG801") is False

    def test_non_lang_pas_lv2(self):
        assert is_lv2_optionnel("INFO631") is False

    def test_none_pas_lv2(self):
        assert is_lv2_optionnel(None) is False

    def test_lv2_codes_constante_complete(self):
        assert "LANG602" in LV2_CODES
        assert "LANG702" in LV2_CODES
        assert "LANG802" in LV2_CODES


# ─────────────────────────────────────────────────────────────
# deduplicate_parallel_groups
# ─────────────────────────────────────────────────────────────

class TestDeduplicateParallelGroups:

    def _make_seances(self):
        return pd.DataFrame([
            {"title_original": "INFO633_A01_G1", "is_parallel_grp": True,
             "starts_utc": pd.Timestamp("2024-09-10 08:00", tz="UTC"),
             "code_prefix": "INFO633", "type_seance": "TD"},
            {"title_original": "INFO633_A01_G2", "is_parallel_grp": True,
             "starts_utc": pd.Timestamp("2024-09-10 08:00", tz="UTC"),
             "code_prefix": "INFO633", "type_seance": "TD"},
            {"title_original": "DATA931_CM", "is_parallel_grp": False,
             "starts_utc": pd.Timestamp("2024-09-10 10:00", tz="UTC"),
             "code_prefix": "DATA931", "type_seance": "CM"},
        ])

    def test_un_doublon_supprime(self):
        df = self._make_seances()
        result = deduplicate_parallel_groups(df)
        assert len(result) == 2

    def test_seances_normales_conservees(self):
        df = self._make_seances()
        result = deduplicate_parallel_groups(df)
        assert "DATA931_CM" in result["title_original"].values

    def test_pas_de_parallele_inchange(self):
        df = pd.DataFrame([
            {"title_original": "INFO631_CM", "is_parallel_grp": False,
             "starts_utc": pd.Timestamp("2024-09-10 08:00", tz="UTC"),
             "code_prefix": "INFO631", "type_seance": "CM"},
        ])
        result = deduplicate_parallel_groups(df)
        assert len(result) == 1


# ─────────────────────────────────────────────────────────────
# build_parse_report
# ─────────────────────────────────────────────────────────────

class TestBuildParseReport:

    def _make_maquette(self):
        return pd.DataFrame([
            {"code_module": "INFO631_IDU", "nom": "Logique", "ects": 2.75,
             "cm_h": 10.5, "td_h": 10.5, "tp_h": 20, "total_h": 41},
        ])

    def test_taux_code_correct(self):
        seances = pd.DataFrame([
            {"title_original": "INFO631_CM", "code_prefix": "INFO631",
             "code_maquette": "INFO631_IDU", "type_seance": "CM"},
            {"title_original": "Inconnu event", "code_prefix": None,
             "code_maquette": None, "type_seance": None},
        ])
        rapport = build_parse_report(seances, self._make_maquette())
        assert rapport["with_code_pct"].iloc[0] == 50.0

    def test_dataframe_vide_ne_crash_pas(self):
        seances = pd.DataFrame(columns=["title_original", "code_prefix",
                                        "code_maquette", "type_seance"])
        maquette = self._make_maquette()
        rapport = build_parse_report(seances, maquette)
        assert rapport["total_events"].iloc[0] == 0
        assert rapport["with_code_pct"].iloc[0] == 0.0

    def test_codes_vraiment_inconnus(self):
        """XXXX999 = code complètement inattendu → catégorie 'vraiment inconnu'."""
        seances = pd.DataFrame([
            {"title_original": "XXXX999_CM", "code_prefix": "XXXX999",
             "code_maquette": "XXXX999", "type_seance": "CM"},
        ])
        rapport = build_parse_report(seances, self._make_maquette())
        assert "XXXX999" in rapport["codes_vraiment_inconnus"].iloc[0]
        assert "XXXX999" not in rapport["modules_manquants_connus"].iloc[0]

    def test_modules_manquants_connus_separes(self):
        """LANG/SHES/EASI/MATH/DDRS → 'modules_manquants_connus' (anomalie connue)."""
        seances = pd.DataFrame([
            {"title_original": "LANG500_PACY", "code_prefix": "LANG500",
             "code_maquette": "LANG500", "type_seance": None},
            {"title_original": "SHES501_TD", "code_prefix": "SHES501",
             "code_maquette": "SHES501", "type_seance": "TD"},
        ])
        rapport = build_parse_report(seances, self._make_maquette())
        manquants = rapport["modules_manquants_connus"].iloc[0]
        assert "LANG500" in manquants
        assert "SHES501" in manquants
        # ne doit PAS être dans la liste vraiment inconnus
        assert "LANG500" not in rapport["codes_vraiment_inconnus"].iloc[0]


# ─────────────────────────────────────────────────────────────
# Cohérence des constantes
# ─────────────────────────────────────────────────────────────

class TestConstants:

    def test_type_map_valeurs_valides(self):
        valides = {"CM", "TD", "TP", "EXAM", "PROJ"}
        for k, v in TYPE_MAP.items():
            assert v in valides, f"TYPE_MAP[{k!r}] = {v!r} invalide"

    def test_ade_to_maquette_format(self):
        for ade_code, maq_code in ADE_TO_MAQUETTE.items():
            assert re.match(r"^[A-Z]+\d+$", ade_code), f"Clé ADE invalide : {ade_code!r}"
            assert "_IDU" in maq_code or "_PACY" in maq_code, \
                f"Code maquette sans suffixe : {maq_code!r}"


# ─────────────────────────────────────────────────────────────
# _parse_description (enseignants + groupes depuis ADE)
# ─────────────────────────────────────────────────────────────

class TestParseDescription:

    def test_enseignant_simple_extrait(self):
        desc = "IDU-3-G-TD\nVERNIER FLAVIEN\n(Exporté le:29/04/2026 10:58)"
        ens, grp = _parse_description(desc)
        assert "VERNIER FLAVIEN" in ens
        # Note : lignes "IDU-..." filtrées comme bruit avant matcher groupe

    def test_enseignant_compose_extrait(self):
        desc = "IDU-4\nDE LA TORRE JEAN-LUC"
        ens, grp = _parse_description(desc)
        assert any("DE LA TORRE" in e or "JEAN-LUC" in e for e in ens)

    def test_lignes_bruit_ignorees(self):
        desc = (
            "Exporté le:29/04/2026\nFISE-N3IE\nScolarité IDU\n"
            "1234567890123\nDUPONT MARIE"
        )
        ens, _ = _parse_description(desc)
        # Seul DUPONT MARIE doit passer le filtre
        assert ens == ["DUPONT MARIE"]

    def test_idu_line_filtree_comme_bruit(self):
        """Les lignes contenant 'IDU-' sont caught par noise_line — comportement actuel."""
        desc = "IDU-3-G2-TP"
        ens, grp = _parse_description(desc)
        assert ens == []
        assert grp == []

    def test_description_vide(self):
        ens, grp = _parse_description("")
        assert ens == []
        assert grp == []

    def test_minuscules_pas_enseignant(self):
        """Pattern exige NOM en MAJ + Prénom Capitalized — minuscules ignorées."""
        desc = "vernier flavien"
        ens, _ = _parse_description(desc)
        assert ens == []


# ─────────────────────────────────────────────────────────────
# Parsers I/O — fixtures temporaires
# ─────────────────────────────────────────────────────────────

import json
from pathlib import Path
from src.parsers.parse_all import (
    parse_responsables, parse_dependances, parse_moodle, load_all_sources,
)


class TestParseResponsables:

    def test_charge_table_simple(self, tmp_path):
        data = [
            {"type": "metadata", "info": "header"},
            {"type": "table", "data": [
                {"code_module": "INFO631_IDU", "nom": "DUPONT", "prenom": "Jean"},
                {"code_module": "INFO632_IDU", "nom": "MARTIN", "prenom": "Marie"},
            ]},
        ]
        path = tmp_path / "resp.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        df = parse_responsables(path)
        assert len(df) == 2
        assert "nom_complet" in df.columns
        assert df.iloc[0]["nom_complet"] == "DUPONT Jean"

    def test_strip_espaces(self, tmp_path):
        data = [{"type": "table", "data": [
            {"code_module": "  INFO631_IDU  ", "nom": " DUPONT ", "prenom": " Jean "},
        ]}]
        path = tmp_path / "resp.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        df = parse_responsables(path)
        assert df.iloc[0]["code_module"] == "INFO631_IDU"
        assert df.iloc[0]["nom_complet"] == "DUPONT Jean"


class TestParseDependances:

    def test_renomme_colonnes_et_extrait_prefix(self, tmp_path):
        data = [{"type": "table", "data": [
            {
                "module_precedent": "INFO631_IDU", "type_precedent": "CM",
                "numero_precedent": 1,
                "module_suivant": "INFO631_IDU", "type_suivant": "TD",
                "numero_suivant": 1,
            },
        ]}]
        path = tmp_path / "dep.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        df = parse_dependances(path)
        assert df.iloc[0]["module_prec"] == "INFO631_IDU"
        assert df.iloc[0]["prefix_prec"] == "INFO631"
        assert df.iloc[0]["prefix_suiv"] == "INFO631"
        assert df.iloc[0]["num_prec"] == 1
        assert df.iloc[0]["num_suiv"] == 1


class TestParseMoodle:

    def test_extrait_codes_modules(self, tmp_path):
        html = """
        <html><body>
        <p>Cours INFO631 - Logique</p>
        <p>DATA931 et MATH501 référencés</p>
        <p>PROJ901 hors scope</p>
        <p>XYZW999 ignoré (préfixe non listé)</p>
        </body></html>
        """
        path = tmp_path / "moodle.html"
        path.write_text(html, encoding="utf-8")
        df = parse_moodle(path)
        codes = set(df["code_prefix"])
        assert "INFO631" in codes
        assert "DATA931" in codes
        assert "MATH501" in codes
        assert "PROJ901" in codes
        assert "XYZW999" not in codes

    def test_html_vide(self, tmp_path):
        path = tmp_path / "moodle.html"
        path.write_text("<html></html>", encoding="utf-8")
        df = parse_moodle(path)
        assert df.empty
        assert "code_prefix" in df.columns


class TestLoadAllSources:

    def test_invocation_dossier_inexistant_leve(self, tmp_path):
        """Dossier sans fichiers attendus → exception au chargement."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(Exception):
            load_all_sources(data_dir=str(empty_dir))
