"""
src/rules/tracabilite.py
========================
Dimension Traçabilité : la chaîne Maquette → Moodle → ADE est-elle complète ?
"""

import re
from typing import List

from src.parsers.parse_all import ParsedSources
from src.rules.base import Anomaly, Severity, Dimension


def rule_R6_modules_maquette_absents_moodle(sources: ParsedSources) -> List[Anomaly]:
    """
    R6.1 — Module présent dans la maquette mais absent du résumé Moodle.
    Sévérité : MINEUR (suivi pédagogique non outillé).
    """
    anomalies: List[Anomaly] = []
    moodle_codes = set(sources.moodle["code_prefix"])
    maq_prefixes = {
        re.match(r"^([A-Z]+\d+)", c).group(1)
        for c in sources.maquette["code_module"]
        if re.match(r"^([A-Z]+\d+)", c)
    }
    absents = maq_prefixes - moodle_codes

    for prefix in sorted(absents):
        ligne = sources.maquette[
            sources.maquette["code_module"].str.startswith(prefix)
        ]
        nom = ligne["nom"].iloc[0] if not ligne.empty else ""
        code_full = ligne["code_module"].iloc[0] if not ligne.empty else prefix
        anomalies.append(Anomaly(
            rule_id     = "R6.1",
            dimension   = Dimension.TRACABILITE,
            severity    = Severity.MINEUR,
            code_module = code_full,
            description = (
                f"Module '{code_full}' ({nom}) absent du résumé Moodle — "
                f"ressources pédagogiques non déployées ou non détectées."
            ),
            details = {"nom": nom},
        ))
    return anomalies


def rule_R6_2_codes_moodle_inconnus(sources: ParsedSources) -> List[Anomaly]:
    """
    R6.2 — Code détecté dans Moodle mais absent de la maquette officielle.
    Ex : PROJ801, PROJ901, PROJ902 dans Moodle mais pas en maquette.
    Sévérité : MAJEUR (incohérence inter-source).
    """
    anomalies: List[Anomaly] = []
    moodle_codes = set(sources.moodle["code_prefix"])
    maq_prefixes = {
        re.match(r"^([A-Z]+\d+)", c).group(1)
        for c in sources.maquette["code_module"]
        if re.match(r"^([A-Z]+\d+)", c)
    }
    inconnus = moodle_codes - maq_prefixes

    for code in sorted(inconnus):
        anomalies.append(Anomaly(
            rule_id     = "R6.2",
            dimension   = Dimension.TRACABILITE,
            severity    = Severity.MAJEUR,
            code_module = code,
            description = (
                f"Code '{code}' présent dans Moodle mais absent de "
                f"MAQUETTE_IDU.json — incohérence référentielle."
            ),
        ))
    return anomalies


def run(sources: ParsedSources) -> List[Anomaly]:
    return (
        rule_R6_modules_maquette_absents_moodle(sources)
        + rule_R6_2_codes_moodle_inconnus(sources)
    )
