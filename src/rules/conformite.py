"""
src/rules/conformite.py
=======================
Dimension Conformité : les séquences pédagogiques (CM avant TD, etc.) sont-elles respectées ?
"""

from typing import List
import pandas as pd

from src.parsers.parse_all import ParsedSources
from src.rules.base import Anomaly, Severity, Dimension


def _seances_par_module_type_chrono(sources: ParsedSources) -> dict:
    """
    Construit un index : {(prefix, type, n_occurrence) → starts_utc}
    où n_occurrence est le rang chronologique (1, 2, 3, ...) de la séance.
    """
    df = sources.seances[
        sources.seances["code_prefix"].notna()
        & sources.seances["type_seance"].notna()
        & ~sources.seances["is_exam"]
    ].copy()
    df = df.sort_values("starts_utc")

    index = {}
    for (prefix, typ), groupe in df.groupby(["code_prefix", "type_seance"]):
        for n, (_, row) in enumerate(groupe.iterrows(), start=1):
            index[(prefix, typ, n)] = row["starts_utc"]
    return index


def rule_R4_violations_sequencement(sources: ParsedSources) -> List[Anomaly]:
    """
    R4.1 — Une séance dépendante (suivante) a été planifiée AVANT
    sa séance prérequise (précédente) dans ADE.
    Sévérité : BLOQUANT (un TD a eu lieu avant son CM).
    """
    anomalies: List[Anomaly] = []
    chrono_index = _seances_par_module_type_chrono(sources)

    for _, dep in sources.dependances.iterrows():
        prefix_p = dep["prefix_prec"]
        prefix_s = dep["prefix_suiv"]
        if pd.isna(prefix_p) or pd.isna(prefix_s):
            continue

        key_prec = (prefix_p, dep["type_prec"], int(dep["num_prec"]))
        key_suiv = (prefix_s, dep["type_suiv"], int(dep["num_suiv"]))

        starts_prec = chrono_index.get(key_prec)
        starts_suiv = chrono_index.get(key_suiv)

        if starts_prec is None or starts_suiv is None:
            continue
        if pd.isna(starts_prec) or pd.isna(starts_suiv):
            continue

        if starts_suiv < starts_prec:
            anomalies.append(Anomaly(
                rule_id     = "R4.1",
                dimension   = Dimension.CONFORMITE,
                severity    = Severity.BLOQUANT,
                code_module = dep["module_suiv"],
                description = (
                    f"Violation séquencement : "
                    f"{dep['module_suiv']} {dep['type_suiv']}#{int(dep['num_suiv'])} "
                    f"({starts_suiv}) planifié AVANT "
                    f"{dep['module_prec']} {dep['type_prec']}#{int(dep['num_prec'])} "
                    f"({starts_prec})."
                ),
                details = {
                    "module_prec":  dep["module_prec"],
                    "type_prec":    dep["type_prec"],
                    "num_prec":     int(dep["num_prec"]),
                    "starts_prec":  str(starts_prec),
                    "module_suiv":  dep["module_suiv"],
                    "type_suiv":    dep["type_suiv"],
                    "num_suiv":     int(dep["num_suiv"]),
                    "starts_suiv":  str(starts_suiv),
                },
            ))
    return anomalies


def rule_R4_2_dependances_orphelines(sources: ParsedSources) -> List[Anomaly]:
    """
    R4.2 — Contrainte de dépendance dont les séances ne sont pas trouvables dans ADE.
    Sévérité : MINEUR (incohérence référentielle, pas un blocage pédagogique).
    """
    anomalies: List[Anomaly] = []
    chrono_index = _seances_par_module_type_chrono(sources)

    for _, dep in sources.dependances.iterrows():
        prefix_p = dep["prefix_prec"]
        prefix_s = dep["prefix_suiv"]
        if pd.isna(prefix_p) or pd.isna(prefix_s):
            continue

        key_prec = (prefix_p, dep["type_prec"], int(dep["num_prec"]))
        key_suiv = (prefix_s, dep["type_suiv"], int(dep["num_suiv"]))

        if key_prec not in chrono_index or key_suiv not in chrono_index:
            anomalies.append(Anomaly(
                rule_id     = "R4.2",
                dimension   = Dimension.CONFORMITE,
                severity    = Severity.MINEUR,
                code_module = dep["module_suiv"],
                description = (
                    f"Dépendance orpheline : impossible de localiser dans ADE "
                    f"{dep['module_prec']} {dep['type_prec']}#{int(dep['num_prec'])} "
                    f"→ {dep['module_suiv']} {dep['type_suiv']}#{int(dep['num_suiv'])}."
                ),
                details = {
                    "prec_trouve":   key_prec in chrono_index,
                    "suiv_trouve":   key_suiv in chrono_index,
                    "key_prec":      list(key_prec),
                    "key_suiv":      list(key_suiv),
                },
            ))
    return anomalies


def run(sources: ParsedSources) -> List[Anomaly]:
    return (
        rule_R4_violations_sequencement(sources)
        + rule_R4_2_dependances_orphelines(sources)
    )
