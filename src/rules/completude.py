"""
src/rules/completude.py
=======================
Dimension Complétude : tous les modules de la maquette sont-ils présents en ADE ?
La maquette est-elle elle-même complète ?
"""

import re
from typing import List

import pandas as pd

from src.parsers.parse_all import ParsedSources, MODULES_MANQUANTS_MAQUETTE
from src.rules.base import Anomaly, Severity, Dimension


def rule_R1_modules_maquette_sans_seance(sources: ParsedSources) -> List[Anomaly]:
    """
    R1.1 — Module maquette avec heures prévues mais 0 séance ADE.
    Sévérité : BLOQUANT (volume horaire entièrement manquant).

    On compare contre les préfixes de `code_maquette` (qui intègre déjà
    le mapping ADE_TO_MAQUETTE pour INFO641→INFO634, INFO743→INFO733).
    """
    anomalies: List[Anomaly] = []
    seances_prefixes_maq = {
        re.match(r"^([A-Z]+\d+)", str(c)).group(1)
        for c in sources.seances["code_maquette"].dropna().unique()
        if re.match(r"^([A-Z]+\d+)", str(c))
    }

    for _, mod in sources.maquette.iterrows():
        prefix_match = re.match(r"^([A-Z]+\d+)", mod["code_module"])
        if not prefix_match:
            continue
        prefix = prefix_match.group(1)
        if prefix not in seances_prefixes_maq and mod["total_h"] > 0:
            anomalies.append(Anomaly(
                rule_id     = "R1.1",
                dimension   = Dimension.COMPLETUDE,
                severity    = Severity.BLOQUANT,
                code_module = mod["code_module"],
                description = f"Module '{mod['nom']}' ({mod['code_module']}) prévu en maquette "
                              f"({mod['total_h']:.1f}h) mais aucune séance trouvée dans ADE.",
                details     = {
                    "nom":         mod["nom"],
                    "heures_prev": mod["total_h"],
                    "ects":        mod["ects"],
                },
            ))
    return anomalies


def rule_R1_2_maquette_incomplete(sources: ParsedSources) -> List[Anomaly]:
    """
    R1.2 — Modules réellement suivis par les étudiants IDU mais ABSENTS de la maquette.
    LANG, SHES, EASI, MATH, DDRS sont obligatoires.
    LV2 (lv2_conditionnel=True) ignoré : choix étudiant après TOEIC, pas une erreur.
    Sévérité : MAJEUR (anomalie de la maquette officielle elle-même).
    """
    anomalies: List[Anomaly] = []
    codes_manquants = (
        sources.seances[sources.seances["famille_manquante"].notna()]
        .groupby("code_prefix")
        .agg(
            famille=("famille_manquante", "first"),
            nb_seances=("title_original", "count"),
            heures_totales=("duration_h", "sum"),
            lv2=("lv2_conditionnel", "first"),
        )
        .reset_index()
    )

    for _, row in codes_manquants.iterrows():
        if bool(row["lv2"]):
            continue
        anomalies.append(Anomaly(
            rule_id     = "R1.2",
            dimension   = Dimension.COMPLETUDE,
            severity    = Severity.MAJEUR,
            code_module = row["code_prefix"],
            description = (
                f"Module obligatoire '{row['code_prefix']}' (famille: {row['famille']}) "
                f"absent de MAQUETTE_IDU.json — {row['nb_seances']} séances "
                f"({row['heures_totales']:.1f}h) déployées en ADE."
            ),
            details = {
                "famille":         row["famille"],
                "nb_seances_ade":  int(row["nb_seances"]),
                "heures_ade":      round(float(row["heures_totales"]), 2),
                "lv2_optionnel":   False,
            },
        ))
    return anomalies


def rule_R1_3_modules_sans_responsable(sources: ParsedSources) -> List[Anomaly]:
    """
    R1.3 — Module maquette sans responsable défini.
    Sévérité : MAJEUR (gouvernance pédagogique).
    """
    anomalies: List[Anomaly] = []
    codes_avec_resp = set(sources.responsables["code_module"])

    for _, mod in sources.maquette.iterrows():
        if mod["code_module"] not in codes_avec_resp:
            anomalies.append(Anomaly(
                rule_id     = "R1.3",
                dimension   = Dimension.COMPLETUDE,
                severity    = Severity.MAJEUR,
                code_module = mod["code_module"],
                description = f"Module '{mod['code_module']}' ({mod['nom']}) sans "
                              f"responsable défini dans Responsables_modules_IDU.json.",
                details     = {"nom": mod["nom"]},
            ))
    return anomalies


def rule_R1_4_responsables_familles_manquantes(sources: ParsedSources) -> List[Anomaly]:
    """
    R1.4 — Aucun responsable défini pour les familles obligatoires manquantes
    (LANG, SHES, EASI, MATH, DDRS).
    Sévérité : MAJEUR.
    """
    anomalies: List[Anomaly] = []
    familles_avec_resp = {
        re.match(r"^([A-Z]+)", c).group(1)
        for c in sources.responsables["code_module"]
        if re.match(r"^([A-Z]+)", c)
    }

    for prefix, famille in MODULES_MANQUANTS_MAQUETTE.items():
        if prefix not in familles_avec_resp:
            anomalies.append(Anomaly(
                rule_id     = "R1.4",
                dimension   = Dimension.COMPLETUDE,
                severity    = Severity.MAJEUR,
                code_module = None,
                description = (
                    f"Aucun responsable défini pour la famille '{famille}' "
                    f"(préfixe {prefix}) — modules obligatoires non gouvernés."
                ),
                details = {"famille": famille, "prefix": prefix},
            ))
    return anomalies


def run(sources: ParsedSources) -> List[Anomaly]:
    """Exécute toutes les règles de complétude et retourne les anomalies trouvées."""
    return (
        rule_R1_modules_maquette_sans_seance(sources)
        + rule_R1_2_maquette_incomplete(sources)
        + rule_R1_3_modules_sans_responsable(sources)
        + rule_R1_4_responsables_familles_manquantes(sources)
    )
