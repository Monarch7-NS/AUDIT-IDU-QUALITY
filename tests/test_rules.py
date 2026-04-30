"""
tests/test_rules.py
===================
Tests unitaires pour le moteur de règles d'audit qualité.
"""

import pandas as pd
import pytest

from src.parsers.parse_all import ParsedSources
from src.rules.base import Anomaly, Severity, Dimension
from src.rules import completude, exactitude, coherence, conformite, unicite, tracabilite
from src.rules.engine import (
    run_all_rules,
    anomalies_to_dataframe,
    compute_quality_score,
    compute_global_score,
    audit,
)


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

def _make_minimal_sources(
    maquette=None, seances=None, responsables=None,
    dependances=None, moodle=None,
) -> ParsedSources:
    """Construit un ParsedSources minimal pour les tests."""
    if maquette is None:
        maquette = pd.DataFrame([{
            "code_module": "INFO631_IDU", "nom": "Logique", "ects": 2.75,
            "cm_h": 10.5, "td_h": 10.5, "tp_h": 20.0, "total_h": 41.0,
        }])
    if seances is None:
        seances = pd.DataFrame(columns=[
            "title_original", "code_prefix", "code_maquette", "type_seance",
            "is_exam", "is_parallel_grp", "famille_manquante", "lv2_conditionnel",
            "starts_utc", "ends_utc", "duration_h",
            "location", "salle", "capacite", "enseignants", "groupes", "promo",
        ])
    if responsables is None:
        responsables = pd.DataFrame(columns=["code_module", "nom", "prenom", "nom_complet"])
    if dependances is None:
        dependances = pd.DataFrame(columns=[
            "module_prec", "type_prec", "num_prec",
            "module_suiv", "type_suiv", "num_suiv",
            "prefix_prec", "prefix_suiv",
        ])
    if moodle is None:
        moodle = pd.DataFrame(columns=["code_prefix", "present_moodle"])

    return ParsedSources(
        maquette=maquette,
        seances=seances,
        responsables=responsables,
        dependances=dependances,
        moodle=moodle,
        parse_report=pd.DataFrame(),
    )


# ─────────────────────────────────────────────────────────────
# Anomaly / base
# ─────────────────────────────────────────────────────────────

class TestAnomaly:

    def test_creation_basique(self):
        a = Anomaly(
            rule_id="R1.1",
            dimension=Dimension.COMPLETUDE,
            severity=Severity.BLOQUANT,
            description="test",
        )
        assert a.rule_id == "R1.1"
        assert a.dimension == Dimension.COMPLETUDE

    def test_to_dict(self):
        a = Anomaly(
            rule_id="R1.1",
            dimension=Dimension.COMPLETUDE,
            severity=Severity.BLOQUANT,
            description="test",
            code_module="INFO631",
            details={"heures_prev": 10.0},
        )
        d = a.to_dict()
        assert d["rule_id"]     == "R1.1"
        assert d["dimension"]   == "Complétude"
        assert d["severity"]    == "bloquant"
        assert d["heures_prev"] == 10.0


# ─────────────────────────────────────────────────────────────
# Complétude
# ─────────────────────────────────────────────────────────────

class TestCompletude:

    def test_module_sans_seance_detecte(self):
        sources = _make_minimal_sources()
        anomalies = completude.rule_R1_modules_maquette_sans_seance(sources)
        assert len(anomalies) == 1
        assert anomalies[0].rule_id == "R1.1"
        assert anomalies[0].code_module == "INFO631_IDU"
        assert anomalies[0].severity == Severity.BLOQUANT

    def test_module_avec_seance_pas_detecte(self):
        seances = pd.DataFrame([{
            "title_original": "INFO631_CM", "code_prefix": "INFO631",
            "code_maquette": "INFO631_IDU", "type_seance": "CM",
            "is_exam": False, "is_parallel_grp": False,
            "famille_manquante": None, "lv2_conditionnel": False,
            "starts_utc": pd.Timestamp("2024-09-10", tz="UTC"),
            "ends_utc": pd.Timestamp("2024-09-10 02:00", tz="UTC"),
            "duration_h": 2.0, "location": "A101", "salle": "A101",
            "capacite": 30, "enseignants": ["VERNIER FLAVIEN"],
            "groupes": ["IDU-3"], "promo": "IDU3",
        }])
        sources = _make_minimal_sources(seances=seances)
        anomalies = completude.rule_R1_modules_maquette_sans_seance(sources)
        assert len(anomalies) == 0

    def test_lv2_ignore_completement(self):
        """LV2 conditionnel = choix étudiant après TOEIC → 0 anomalie."""
        seances = pd.DataFrame([{
            "title_original": "LANG602_TD", "code_prefix": "LANG602",
            "code_maquette": "LANG602", "type_seance": "TD",
            "is_exam": False, "is_parallel_grp": False,
            "famille_manquante": "Langues vivantes",
            "lv2_conditionnel": True,
            "starts_utc": pd.Timestamp("2024-09-10", tz="UTC"),
            "ends_utc": pd.Timestamp("2024-09-10 02:00", tz="UTC"),
            "duration_h": 2.0, "location": "B202", "salle": "B202",
            "capacite": 25, "enseignants": [], "groupes": ["IDU-3"], "promo": "IDU3",
        }])
        sources = _make_minimal_sources(seances=seances)
        anomalies = completude.rule_R1_2_maquette_incomplete(sources)
        assert len(anomalies) == 0

    def test_module_manquant_shes_detecte_majeur(self):
        seances = pd.DataFrame([{
            "title_original": "SHES501_TD", "code_prefix": "SHES501",
            "code_maquette": "SHES501", "type_seance": "TD",
            "is_exam": False, "is_parallel_grp": False,
            "famille_manquante": "Sciences Humaines et Sociales",
            "lv2_conditionnel": False,
            "starts_utc": pd.Timestamp("2024-09-10", tz="UTC"),
            "ends_utc": pd.Timestamp("2024-09-10 02:00", tz="UTC"),
            "duration_h": 2.0, "location": "B202", "salle": "B202",
            "capacite": 25, "enseignants": [], "groupes": ["IDU-3"], "promo": "IDU3",
        }])
        sources = _make_minimal_sources(seances=seances)
        anomalies = completude.rule_R1_2_maquette_incomplete(sources)
        assert len(anomalies) == 1
        # Non-LV2 → MAJEUR
        assert anomalies[0].severity == Severity.MAJEUR

    def test_module_sans_responsable_detecte(self):
        # Maquette a INFO631_IDU mais pas dans responsables
        sources = _make_minimal_sources()
        anomalies = completude.rule_R1_3_modules_sans_responsable(sources)
        assert len(anomalies) == 1
        assert anomalies[0].code_module == "INFO631_IDU"

    def test_responsables_familles_manquantes_toutes_detectees(self):
        sources = _make_minimal_sources()
        anomalies = completude.rule_R1_4_responsables_familles_manquantes(sources)
        # Toutes les familles MODULES_MANQUANTS_MAQUETTE doivent être flaggées
        assert len(anomalies) == 5  # LANG, SHES, MATH, EASI, DDRS


# ─────────────────────────────────────────────────────────────
# Exactitude
# ─────────────────────────────────────────────────────────────

class TestExactitude:

    def test_duree_aberrante_nulle(self):
        seances = pd.DataFrame([{
            "title_original": "INFO631_CM", "code_prefix": "INFO631",
            "code_maquette": "INFO631_IDU", "type_seance": "CM",
            "is_exam": False, "is_parallel_grp": False,
            "famille_manquante": None, "lv2_conditionnel": False,
            "starts_utc": pd.Timestamp("2024-09-10", tz="UTC"),
            "ends_utc": pd.Timestamp("2024-09-10", tz="UTC"),
            "duration_h": 0.0, "location": "A101", "salle": "A101",
            "capacite": 30, "enseignants": [], "groupes": [], "promo": "IDU3",
        }])
        sources = _make_minimal_sources(seances=seances)
        anomalies = exactitude.rule_R2_3_durees_aberrantes(sources)
        assert len(anomalies) == 1
        assert anomalies[0].severity == Severity.MINEUR

    def test_duree_aberrante_trop_longue(self):
        seances = pd.DataFrame([{
            "title_original": "INFO631_CM", "code_prefix": "INFO631",
            "code_maquette": "INFO631_IDU", "type_seance": "CM",
            "is_exam": False, "is_parallel_grp": False,
            "famille_manquante": None, "lv2_conditionnel": False,
            "starts_utc": pd.Timestamp("2024-09-10 08:00", tz="UTC"),
            "ends_utc": pd.Timestamp("2024-09-10 18:00", tz="UTC"),
            "duration_h": 10.0, "location": "A101", "salle": "A101",
            "capacite": 30, "enseignants": [], "groupes": [], "promo": "IDU3",
        }])
        sources = _make_minimal_sources(seances=seances)
        anomalies = exactitude.rule_R2_3_durees_aberrantes(sources)
        assert len(anomalies) == 1


# ─────────────────────────────────────────────────────────────
# Cohérence
# ─────────────────────────────────────────────────────────────

class TestCoherence:

    def test_doublons_responsables_detectes(self):
        responsables = pd.DataFrame([
            {"code_module": "INFO631_IDU", "nom": "VERNIER", "prenom": "F",
             "nom_complet": "VERNIER F"},
            {"code_module": "INFO631_IDU", "nom": "DUPONT",  "prenom": "J",
             "nom_complet": "DUPONT J"},
        ])
        sources = _make_minimal_sources(responsables=responsables)
        anomalies = coherence.rule_R3_2_doublons_responsables(sources)
        assert len(anomalies) == 1
        assert anomalies[0].details["nb_responsables"] == 2


# ─────────────────────────────────────────────────────────────
# Unicité
# ─────────────────────────────────────────────────────────────

class TestUnicite:

    def test_enseignant_double_creneau_detecte(self):
        seances = pd.DataFrame([
            {
                "title_original": "INFO631_CM", "code_prefix": "INFO631",
                "code_maquette": "INFO631_IDU", "type_seance": "CM",
                "is_exam": False, "is_parallel_grp": False,
                "famille_manquante": None, "lv2_conditionnel": False,
                "starts_utc": pd.Timestamp("2024-09-10 08:00", tz="UTC"),
                "ends_utc": pd.Timestamp("2024-09-10 10:00", tz="UTC"),
                "duration_h": 2.0, "location": "A101", "salle": "A101",
                "capacite": 30, "enseignants": ["SALAMATIAN KAVE"],
                "groupes": ["IDU-3"], "promo": "IDU3",
            },
            {
                "title_original": "INFO632_TD", "code_prefix": "INFO632",
                "code_maquette": "INFO632_IDU", "type_seance": "TD",
                "is_exam": False, "is_parallel_grp": False,
                "famille_manquante": None, "lv2_conditionnel": False,
                "starts_utc": pd.Timestamp("2024-09-10 08:00", tz="UTC"),
                "ends_utc": pd.Timestamp("2024-09-10 10:00", tz="UTC"),
                "duration_h": 2.0, "location": "B202", "salle": "B202",
                "capacite": 25, "enseignants": ["SALAMATIAN KAVE"],
                "groupes": ["IDU-4"], "promo": "IDU4",
            },
        ])
        sources = _make_minimal_sources(seances=seances)
        anomalies = unicite.rule_R5_enseignant_double_creneau(sources)
        assert len(anomalies) == 1
        assert anomalies[0].severity == Severity.BLOQUANT
        assert "SALAMATIAN" in anomalies[0].description


# ─────────────────────────────────────────────────────────────
# Traçabilité
# ─────────────────────────────────────────────────────────────

class TestTracabilite:

    def test_module_maquette_absent_moodle(self):
        moodle = pd.DataFrame([{"code_prefix": "AUTRE001", "present_moodle": True}])
        sources = _make_minimal_sources(moodle=moodle)
        anomalies = tracabilite.rule_R6_modules_maquette_absents_moodle(sources)
        # INFO631 absent du moodle mock
        assert any("INFO631" in a.code_module for a in anomalies)

    def test_code_moodle_absent_maquette(self):
        moodle = pd.DataFrame([{"code_prefix": "PROJ901", "present_moodle": True}])
        sources = _make_minimal_sources(moodle=moodle)
        anomalies = tracabilite.rule_R6_2_codes_moodle_inconnus(sources)
        assert len(anomalies) == 1
        assert anomalies[0].code_module == "PROJ901"
        assert anomalies[0].severity == Severity.MAJEUR


# ─────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────

class TestEngine:

    def test_run_all_rules_retourne_liste(self):
        sources = _make_minimal_sources()
        anomalies = run_all_rules(sources)
        assert isinstance(anomalies, list)

    def test_anomalies_to_dataframe_vide(self):
        df = anomalies_to_dataframe([])
        assert df.empty
        assert "rule_id" in df.columns

    def test_anomalies_to_dataframe_avec_anomalies(self):
        anos = [
            Anomaly("R1.1", Dimension.COMPLETUDE, Severity.BLOQUANT, "test1"),
            Anomaly("R2.1", Dimension.EXACTITUDE, Severity.MAJEUR, "test2"),
        ]
        df = anomalies_to_dataframe(anos)
        assert len(df) == 2
        assert df.iloc[0]["rule_id"] == "R1.1"

    def test_compute_quality_score_six_dimensions(self):
        df = compute_quality_score([])
        assert len(df) == 6
        assert df["score"].iloc[0] == 100.0  # aucune anomalie → score parfait

    def test_compute_quality_score_avec_bloquant(self):
        anos = [Anomaly("R1.1", Dimension.COMPLETUDE, Severity.BLOQUANT, "x")]
        df = compute_quality_score(anos)
        ligne_complet = df[df["dimension"] == "Complétude"].iloc[0]
        assert ligne_complet["score"] == 95.0  # 100 - 5

    def test_compute_global_score(self):
        df = pd.DataFrame([
            {"dimension": "A", "score": 80.0},
            {"dimension": "B", "score": 100.0},
        ])
        assert compute_global_score(df) == 90.0

    def test_audit_retourne_structure_complete(self):
        sources = _make_minimal_sources()
        result = audit(sources)
        assert "anomalies" in result
        assert "score_par_dim" in result
        assert "score_global" in result
        assert "raw" in result
        assert isinstance(result["score_global"], float)


# ─────────────────────────────────────────────────────────────
# Helpers séances
# ─────────────────────────────────────────────────────────────

def _seance(**overrides) -> dict:
    """Séance factice avec valeurs par défaut — override via kwargs."""
    base = {
        "title_original": "INFO631_CM",
        "code_prefix": "INFO631",
        "code_maquette": "INFO631_IDU",
        "type_seance": "CM",
        "is_exam": False,
        "is_parallel_grp": False,
        "famille_manquante": None,
        "lv2_conditionnel": False,
        "starts_utc": pd.Timestamp("2024-09-10 08:00", tz="UTC"),
        "ends_utc":   pd.Timestamp("2024-09-10 10:00", tz="UTC"),
        "duration_h": 2.0,
        "location": "A101",
        "salle": "A101",
        "capacite": 30,
        "enseignants": ["VERNIER FLAVIEN"],
        "groupes": ["IDU-3"],
        "promo": "IDU3",
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────
# Exactitude — R2.1 / R2.2 (écart heures par type)
# ─────────────────────────────────────────────────────────────

class TestExactitudeEcartHeures:

    def _maquette_info631(self, cm_h=10.5, td_h=10.5, tp_h=20.0):
        return pd.DataFrame([{
            "code_module": "INFO631_IDU", "nom": "Logique", "ects": 2.75,
            "cm_h": cm_h, "td_h": td_h, "tp_h": tp_h,
            "total_h": cm_h + td_h + tp_h,
        }])

    def test_type_prevu_sans_seance_bloquant(self):
        """CM prévu en maquette, 0 séance ADE → BLOQUANT R2.1."""
        seances = pd.DataFrame([_seance(type_seance="TD", duration_h=10.5)])
        sources = _make_minimal_sources(
            maquette=self._maquette_info631(), seances=seances,
        )
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        # CM (10.5h prév, 0h ADE) + TP (20h prév, 0h ADE) → 2 BLOQUANT
        bloquants = [a for a in anos if a.severity == Severity.BLOQUANT]
        assert len(bloquants) == 2
        assert all(a.rule_id == "R2.1" for a in bloquants)

    def test_seance_non_prevue_majeur(self):
        """TP en ADE mais 0h TP prévu → MAJEUR R2.2."""
        maquette = pd.DataFrame([{
            "code_module": "INFO631_IDU", "nom": "Logique", "ects": 1.0,
            "cm_h": 10.0, "td_h": 0.0, "tp_h": 0.0, "total_h": 10.0,
        }])
        seances = pd.DataFrame([
            _seance(type_seance="CM", duration_h=10.0),
            _seance(title_original="INFO631_TP", type_seance="TP", duration_h=4.0,
                    starts_utc=pd.Timestamp("2024-09-11 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-11 12:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(maquette=maquette, seances=seances)
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        r22 = [a for a in anos if a.rule_id == "R2.2"]
        assert len(r22) == 1
        assert r22[0].severity == Severity.MAJEUR
        assert r22[0].details["type"] == "TP"

    def test_ecart_dans_seuil_aucune_anomalie(self):
        """Écart ≤ 15% → aucune anomalie."""
        seances = pd.DataFrame([
            _seance(type_seance="CM", duration_h=10.0),  # prévu 10.5h, écart -4.8%
            _seance(title_original="INFO631_TD", type_seance="TD", duration_h=10.5,
                    starts_utc=pd.Timestamp("2024-09-11 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-11 18:30", tz="UTC")),
            _seance(title_original="INFO631_TP", type_seance="TP", duration_h=20.0,
                    starts_utc=pd.Timestamp("2024-09-12 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-13 04:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(
            maquette=self._maquette_info631(), seances=seances,
        )
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        assert anos == []

    def test_ecart_majeur_seuil_25(self):
        """Écart entre 25% et 50% → MAJEUR."""
        seances = pd.DataFrame([
            _seance(type_seance="CM", duration_h=14.5),  # prévu 10.5, +38%
            _seance(title_original="INFO631_TD", type_seance="TD", duration_h=10.5,
                    starts_utc=pd.Timestamp("2024-09-11 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-11 18:30", tz="UTC")),
            _seance(title_original="INFO631_TP", type_seance="TP", duration_h=20.0,
                    starts_utc=pd.Timestamp("2024-09-12 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-13 04:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(
            maquette=self._maquette_info631(), seances=seances,
        )
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        assert len(anos) == 1
        assert anos[0].severity == Severity.MAJEUR
        assert anos[0].details["type"] == "CM"

    def test_ecart_bloquant_seuil_50(self):
        """Écart > 50% → BLOQUANT."""
        seances = pd.DataFrame([
            _seance(type_seance="CM", duration_h=20.0),  # prévu 10.5, +90%
            _seance(title_original="INFO631_TD", type_seance="TD", duration_h=10.5,
                    starts_utc=pd.Timestamp("2024-09-11 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-11 18:30", tz="UTC")),
            _seance(title_original="INFO631_TP", type_seance="TP", duration_h=20.0,
                    starts_utc=pd.Timestamp("2024-09-12 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-13 04:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(
            maquette=self._maquette_info631(), seances=seances,
        )
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        bloquants = [a for a in anos if a.severity == Severity.BLOQUANT]
        assert len(bloquants) == 1
        assert bloquants[0].details["type"] == "CM"

    def test_examens_exclus_du_calcul(self):
        """Séances is_exam=True ne comptent pas dans heures_ade."""
        seances = pd.DataFrame([
            _seance(type_seance="CM", duration_h=10.0,
                    title_original="INFO631_ET", is_exam=True),
        ])
        sources = _make_minimal_sources(
            maquette=self._maquette_info631(), seances=seances,
        )
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        # CM prévu 10.5h, 0h ADE (examen exclu) → BLOQUANT type prévu sans séance
        cm_anos = [a for a in anos if a.details.get("type") == "CM"]
        assert len(cm_anos) == 1
        assert cm_anos[0].severity == Severity.BLOQUANT


# ─────────────────────────────────────────────────────────────
# Cohérence — R3.1 codes ADE non normalisés
# ─────────────────────────────────────────────────────────────

class TestCoherenceCodesAde:

    def test_code_ade_mappe_detecte(self):
        """Séance avec code_prefix dans ADE_TO_MAQUETTE → R3.1."""
        from src.parsers.parse_all import ADE_TO_MAQUETTE
        # Prend la première clé du mapping
        code_ade = next(iter(ADE_TO_MAQUETTE))
        code_maq = ADE_TO_MAQUETTE[code_ade]
        seances = pd.DataFrame([
            _seance(title_original=f"{code_ade}_CM",
                    code_prefix=code_ade, code_maquette=code_maq),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = coherence.rule_R3_codes_ade_non_normalises(sources)
        assert len(anos) >= 1
        assert any(a.code_module == code_maq for a in anos)
        assert all(a.severity == Severity.MINEUR for a in anos)

    def test_pas_de_seance_pas_anomalie(self):
        sources = _make_minimal_sources()
        anos = coherence.rule_R3_codes_ade_non_normalises(sources)
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Cohérence — R3.3 titres inconsistants
# ─────────────────────────────────────────────────────────────

class TestCoherenceTitresInconsistants:

    def test_titre_non_parsable_detecte(self):
        seances = pd.DataFrame([
            _seance(title_original="Réunion BDE", code_prefix=None,
                    code_maquette=None, type_seance=None),
            _seance(title_original="Réunion BDE", code_prefix=None,
                    code_maquette=None, type_seance=None,
                    starts_utc=pd.Timestamp("2024-09-11 10:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = coherence.rule_R3_3_titres_inconsistants(sources)
        assert len(anos) == 1
        assert anos[0].severity == Severity.MINEUR
        assert anos[0].details["occurrences"] == 2
        assert "Réunion BDE" in anos[0].description

    def test_seance_avec_code_pas_concernee(self):
        seances = pd.DataFrame([_seance()])  # code_prefix = INFO631
        sources = _make_minimal_sources(seances=seances)
        anos = coherence.rule_R3_3_titres_inconsistants(sources)
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Conformité — R4.1 violations séquencement
# ─────────────────────────────────────────────────────────────

class TestConformiteSequencement:

    def _dependances_cm_avant_td(self):
        return pd.DataFrame([{
            "module_prec": "INFO631_IDU", "type_prec": "CM", "num_prec": 1,
            "module_suiv": "INFO631_IDU", "type_suiv": "TD", "num_suiv": 1,
            "prefix_prec": "INFO631", "prefix_suiv": "INFO631",
        }])

    def test_td_avant_cm_detecte_bloquant(self):
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TD", type_seance="TD",
                    starts_utc=pd.Timestamp("2024-09-09 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-09 10:00", tz="UTC")),
            _seance(title_original="INFO631_CM", type_seance="CM",
                    starts_utc=pd.Timestamp("2024-09-10 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-10 10:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(
            seances=seances, dependances=self._dependances_cm_avant_td(),
        )
        anos = conformite.rule_R4_violations_sequencement(sources)
        assert len(anos) == 1
        assert anos[0].rule_id == "R4.1"
        assert anos[0].severity == Severity.BLOQUANT
        assert anos[0].code_module == "INFO631_IDU"

    def test_ordre_correct_pas_anomalie(self):
        seances = pd.DataFrame([
            _seance(title_original="INFO631_CM", type_seance="CM",
                    starts_utc=pd.Timestamp("2024-09-09 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-09 10:00", tz="UTC")),
            _seance(title_original="INFO631_TD", type_seance="TD",
                    starts_utc=pd.Timestamp("2024-09-10 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-10 10:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(
            seances=seances, dependances=self._dependances_cm_avant_td(),
        )
        anos = conformite.rule_R4_violations_sequencement(sources)
        assert anos == []

    def test_seance_introuvable_ignore(self):
        """Si la séance prec/suiv n'existe pas → pas d'anomalie R4.1 (R4.2 prend le relais)."""
        seances = pd.DataFrame([_seance()])  # CM only
        sources = _make_minimal_sources(
            seances=seances, dependances=self._dependances_cm_avant_td(),
        )
        anos = conformite.rule_R4_violations_sequencement(sources)
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Conformité — R4.2 dépendances orphelines
# ─────────────────────────────────────────────────────────────

class TestConformiteDependancesOrphelines:

    def test_dependance_sans_seances_detectee(self):
        dependances = pd.DataFrame([{
            "module_prec": "INFO631_IDU", "type_prec": "CM", "num_prec": 1,
            "module_suiv": "INFO631_IDU", "type_suiv": "TD", "num_suiv": 1,
            "prefix_prec": "INFO631", "prefix_suiv": "INFO631",
        }])
        # Aucune séance → R4.2
        sources = _make_minimal_sources(dependances=dependances)
        anos = conformite.rule_R4_2_dependances_orphelines(sources)
        assert len(anos) == 1
        assert anos[0].rule_id == "R4.2"
        assert anos[0].severity == Severity.MINEUR
        assert anos[0].details["prec_trouve"] is False

    def test_dependance_avec_seances_pas_orpheline(self):
        dependances = pd.DataFrame([{
            "module_prec": "INFO631_IDU", "type_prec": "CM", "num_prec": 1,
            "module_suiv": "INFO631_IDU", "type_suiv": "TD", "num_suiv": 1,
            "prefix_prec": "INFO631", "prefix_suiv": "INFO631",
        }])
        seances = pd.DataFrame([
            _seance(type_seance="CM",
                    starts_utc=pd.Timestamp("2024-09-09 08:00", tz="UTC")),
            _seance(title_original="INFO631_TD", type_seance="TD",
                    starts_utc=pd.Timestamp("2024-09-10 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-10 10:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(seances=seances, dependances=dependances)
        anos = conformite.rule_R4_2_dependances_orphelines(sources)
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Unicité — R5.2 capacité salle insuffisante
# ─────────────────────────────────────────────────────────────

class TestUniciteCapaciteSalle:

    def test_cm_petite_salle_detecte(self):
        seances = pd.DataFrame([
            _seance(type_seance="CM", capacite=8, salle="P101"),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = unicite.rule_R5_2_capacite_salle_insuffisante(sources)
        assert len(anos) == 1
        assert anos[0].severity == Severity.MINEUR
        assert anos[0].details["capacite"] == 8

    def test_td_petite_salle_detecte(self):
        seances = pd.DataFrame([
            _seance(type_seance="TD", capacite=10, salle="P102"),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = unicite.rule_R5_2_capacite_salle_insuffisante(sources)
        assert len(anos) == 1

    def test_tp_ignore(self):
        """TP en petite salle = normal (groupes restreints)."""
        seances = pd.DataFrame([
            _seance(type_seance="TP", capacite=8, salle="P103"),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = unicite.rule_R5_2_capacite_salle_insuffisante(sources)
        assert anos == []

    def test_grande_salle_ignore(self):
        seances = pd.DataFrame([
            _seance(type_seance="CM", capacite=30, salle="A101"),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = unicite.rule_R5_2_capacite_salle_insuffisante(sources)
        assert anos == []

    def test_capacite_nan_ignore(self):
        import numpy as np
        seances = pd.DataFrame([
            _seance(type_seance="CM", capacite=np.nan),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = unicite.rule_R5_2_capacite_salle_insuffisante(sources)
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Intégration — audit complet multi-règles
# ─────────────────────────────────────────────────────────────

class TestAuditIntegration:

    def test_audit_complet_avec_anomalies_multiples(self):
        """Sources couvrant 3 dimensions → score < 100 et anomalies présentes."""
        maquette = pd.DataFrame([{
            "code_module": "INFO631_IDU", "nom": "Logique", "ects": 2.75,
            "cm_h": 10.0, "td_h": 10.0, "tp_h": 0.0, "total_h": 20.0,
        }])
        seances = pd.DataFrame([
            # Durée aberrante → R2.3 MINEUR (Exactitude)
            _seance(type_seance="CM", duration_h=12.0,
                    starts_utc=pd.Timestamp("2024-09-09 06:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-09 18:00", tz="UTC")),
            # Conflit enseignant double salle → R5.1 BLOQUANT (Unicité)
            _seance(title_original="INFO631_TD", type_seance="TD",
                    salle="A101",
                    starts_utc=pd.Timestamp("2024-09-10 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-10 10:00", tz="UTC"),
                    enseignants=["DUPONT JEAN"]),
            _seance(title_original="INFO632_TD", code_prefix="INFO632",
                    code_maquette="INFO632_IDU", type_seance="TD",
                    salle="B202",
                    starts_utc=pd.Timestamp("2024-09-10 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-10 10:00", tz="UTC"),
                    enseignants=["DUPONT JEAN"]),
        ])
        sources = _make_minimal_sources(maquette=maquette, seances=seances)
        result = audit(sources)

        assert len(result["raw"]) > 0
        assert result["score_global"] < 100.0
        # Au moins 1 BLOQUANT (conflit enseignant)
        bloquants = [a for a in result["raw"] if a.severity == Severity.BLOQUANT]
        assert len(bloquants) >= 1
        # Vérifie présence dimensions multiples
        dims_touchees = {a.dimension for a in result["raw"]}
        assert Dimension.UNICITE in dims_touchees

    def test_score_dimension_jamais_negatif(self):
        """Beaucoup d'anomalies ne doivent pas créer un score < 0."""
        anos = [
            Anomaly(f"R1.{i}", Dimension.COMPLETUDE, Severity.BLOQUANT, "x")
            for i in range(50)
        ]
        df = compute_quality_score(anos)
        completude_score = df[df["dimension"] == "Complétude"]["score"].iloc[0]
        assert completude_score >= 0.0

    def test_to_dataframe_colonnes_completes(self):
        anos = [
            Anomaly("R1.1", Dimension.COMPLETUDE, Severity.BLOQUANT, "x",
                    code_module="INFO631", details={"foo": "bar"}),
        ]
        df = anomalies_to_dataframe(anos)
        assert "rule_id" in df.columns
        assert "dimension" in df.columns
        assert "severity" in df.columns
        assert "foo" in df.columns  # détails fusionnés
        assert df["foo"].iloc[0] == "bar"


# ─────────────────────────────────────────────────────────────
# Exactitude — R2 déduplication groupes parallèles
# ─────────────────────────────────────────────────────────────

class TestExactitudeParalleleDedup:

    def _maquette_info633(self, cm_h=0.0, td_h=0.0, tp_h=20.0):
        return pd.DataFrame([{
            "code_module": "INFO633_IDU", "nom": "X", "ects": 1.0,
            "cm_h": cm_h, "td_h": td_h, "tp_h": tp_h,
            "total_h": cm_h + td_h + tp_h,
        }])

    def test_heures_groupes_paralleles_meme_horaire_non_dupliquees(self):
        """G1 + G2 même horaire → comptés comme 1 seule séance."""
        same_start = pd.Timestamp("2024-09-10 08:00", tz="UTC")
        same_end   = pd.Timestamp("2024-09-10 12:00", tz="UTC")
        seances = pd.DataFrame([
            _seance(title_original="INFO633A01G1", code_prefix="INFO633",
                    code_maquette="INFO633_IDU", type_seance="TP",
                    is_parallel_grp=True, duration_h=4.0,
                    starts_utc=same_start, ends_utc=same_end),
            _seance(title_original="INFO633A01G2", code_prefix="INFO633",
                    code_maquette="INFO633_IDU", type_seance="TP",
                    is_parallel_grp=True, duration_h=4.0,
                    starts_utc=same_start, ends_utc=same_end),
        ])
        sources = _make_minimal_sources(
            maquette=self._maquette_info633(tp_h=4.0), seances=seances,
        )
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        # 4h prévu, 4h ADE après dedup → aucune anomalie
        assert anos == []

    def test_heures_groupes_paralleles_horaires_differents_comptes_deux_fois(self):
        """G1 lundi + G2 mercredi → 2 créneaux réels, comptés 2 fois."""
        seances = pd.DataFrame([
            _seance(title_original="INFO633A01G1", code_prefix="INFO633",
                    code_maquette="INFO633_IDU", type_seance="TP",
                    is_parallel_grp=True, duration_h=4.0,
                    starts_utc=pd.Timestamp("2024-09-09 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-09 12:00", tz="UTC")),
            _seance(title_original="INFO633A01G2", code_prefix="INFO633",
                    code_maquette="INFO633_IDU", type_seance="TP",
                    is_parallel_grp=True, duration_h=4.0,
                    starts_utc=pd.Timestamp("2024-09-11 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-11 12:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(
            maquette=self._maquette_info633(tp_h=8.0), seances=seances,
        )
        anos = exactitude.rule_R2_ecart_heures_par_type(sources)
        # 8h prévu, 8h ADE (2 créneaux distincts) → 0 anomalie
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Exactitude — R2.4 incohérence durée/type TP
# ─────────────────────────────────────────────────────────────

class TestExactitudeR24TpDureeCourte:

    def test_tp_moins_4h_mineur(self):
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TP", type_seance="TP", duration_h=2.0),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = exactitude.rule_R2_4_tp_duree_courte(sources)
        assert len(anos) == 1
        assert anos[0].rule_id == "R2.4"
        assert anos[0].severity == Severity.MINEUR
        assert anos[0].details["duration_h"] == 2.0

    def test_tp_exactement_4h_ok(self):
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TP", type_seance="TP", duration_h=4.0),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = exactitude.rule_R2_4_tp_duree_courte(sources)
        assert anos == []

    def test_cm_moins_4h_ok(self):
        """CM courts = normal — règle ne s'applique qu'aux TP."""
        seances = pd.DataFrame([
            _seance(type_seance="CM", duration_h=1.5),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = exactitude.rule_R2_4_tp_duree_courte(sources)
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Exactitude — R2.5 séance sans enseignant (asymétrique)
# ─────────────────────────────────────────────────────────────

class TestExactitudeR25SansEnseignant:

    def test_cm_sans_enseignant_bloquant(self):
        seances = pd.DataFrame([
            _seance(type_seance="CM", enseignants=[]),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = exactitude.rule_R2_5_seance_sans_enseignant(sources)
        assert len(anos) == 1
        assert anos[0].rule_id == "R2.5"
        assert anos[0].severity == Severity.BLOQUANT

    def test_td_sans_enseignant_ignore(self):
        """TD sans enseignant = auto-formation normale."""
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TD", type_seance="TD", enseignants=[]),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = exactitude.rule_R2_5_seance_sans_enseignant(sources)
        assert anos == []

    def test_tp_sans_enseignant_mineur(self):
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TP", type_seance="TP", enseignants=[]),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = exactitude.rule_R2_5_seance_sans_enseignant(sources)
        assert len(anos) == 1
        assert anos[0].severity == Severity.MINEUR

    def test_cm_avec_enseignant_ok(self):
        seances = pd.DataFrame([
            _seance(type_seance="CM", enseignants=["DUPONT"]),
        ])
        sources = _make_minimal_sources(seances=seances)
        anos = exactitude.rule_R2_5_seance_sans_enseignant(sources)
        assert anos == []


# ─────────────────────────────────────────────────────────────
# Cohérence — R3.4 possible mauvais tag TD/TP
# ─────────────────────────────────────────────────────────────

class TestCoherenceR34MauvaisTagTdTp:

    def _maq(self, cm_h=0.0, td_h=10.0, tp_h=20.0):
        return pd.DataFrame([{
            "code_module": "INFO631_IDU", "nom": "X", "ects": 1.0,
            "cm_h": cm_h, "td_h": td_h, "tp_h": tp_h,
            "total_h": cm_h + td_h + tp_h,
        }])

    def test_exces_td_correspond_manque_tp_detecte(self):
        """tph_maq=20, tdh_maq=10, ADE TD=30 TP=0 → excedent_td=20 ≈ tph_maq → MINEUR."""
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TD", type_seance="TD", duration_h=30.0,
                    starts_utc=pd.Timestamp("2024-09-09 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-10 14:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(maquette=self._maq(), seances=seances)
        anos = coherence.rule_R3_4_possible_mauvais_tag_td_tp(sources)
        assert len(anos) == 1
        assert anos[0].rule_id == "R3.4"
        assert anos[0].severity == Severity.MINEUR
        assert anos[0].code_module == "INFO631_IDU"

    def test_exces_td_sans_manque_tp_ignore(self):
        """ADE TP=20 → heures_tp_ade != 0 → règle ne déclenche pas."""
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TD", type_seance="TD", duration_h=15.0,
                    starts_utc=pd.Timestamp("2024-09-09 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-09 23:00", tz="UTC")),
            _seance(title_original="INFO631_TP", type_seance="TP", duration_h=20.0,
                    starts_utc=pd.Timestamp("2024-09-12 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-13 04:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(maquette=self._maq(), seances=seances)
        anos = coherence.rule_R3_4_possible_mauvais_tag_td_tp(sources)
        assert anos == []

    def test_ecart_trop_grand_ignore(self):
        """tph_maq=20, excedent_td=4 → abs(4-20)=16 > 2 → 0 anomalie."""
        seances = pd.DataFrame([
            _seance(title_original="INFO631_TD", type_seance="TD", duration_h=14.0,
                    starts_utc=pd.Timestamp("2024-09-09 08:00", tz="UTC"),
                    ends_utc=pd.Timestamp("2024-09-09 22:00", tz="UTC")),
        ])
        sources = _make_minimal_sources(maquette=self._maq(), seances=seances)
        anos = coherence.rule_R3_4_possible_mauvais_tag_td_tp(sources)
        assert anos == []
