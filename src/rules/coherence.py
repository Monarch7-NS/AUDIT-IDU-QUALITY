"""
src/rules/coherence.py
======================
Dimension Cohérence : les codes modules sont-ils uniformes entre toutes les sources ?
"""

import re
from typing import List

from src.parsers.parse_all import ParsedSources, ADE_TO_MAQUETTE
from src.rules.base import Anomaly, Severity, Dimension
from src.rules.exactitude import _calcul_heures_ade_par_module


def rule_R3_codes_ade_non_normalises(sources: ParsedSources) -> List[Anomaly]:
    """
    R3.1 — Code ADE différent du code maquette pour le même module
    (ex INFO641 ADE → INFO634_IDU maquette).
    Sévérité : MINEUR (mapping géré par ADE_TO_MAQUETTE mais à signaler).
    """
    anomalies: List[Anomaly] = []
    for code_ade, code_maq in ADE_TO_MAQUETTE.items():
        seances_concernees = sources.seances[sources.seances["code_prefix"] == code_ade]
        if seances_concernees.empty:
            continue
        anomalies.append(Anomaly(
            rule_id     = "R3.1",
            dimension   = Dimension.COHERENCE,
            severity    = Severity.MINEUR,
            code_module = code_maq,
            description = (
                f"Code ADE '{code_ade}' utilisé pour {len(seances_concernees)} séances "
                f"correspond au module maquette '{code_maq}' — codes non normalisés."
            ),
            details = {
                "code_ade":      code_ade,
                "code_maquette": code_maq,
                "nb_seances":    int(len(seances_concernees)),
            },
        ))
    return anomalies


def rule_R3_2_doublons_responsables(sources: ParsedSources) -> List[Anomaly]:
    """
    R3.2 — Module avec plusieurs responsables (doublons dans la table).
    Sévérité : MAJEUR (gouvernance ambigüe).
    """
    anomalies: List[Anomaly] = []
    counts = sources.responsables["code_module"].value_counts()
    doublons = counts[counts > 1]

    for code, n in doublons.items():
        responsables = sources.responsables[sources.responsables["code_module"] == code]
        anomalies.append(Anomaly(
            rule_id     = "R3.2",
            dimension   = Dimension.COHERENCE,
            severity    = Severity.MAJEUR,
            code_module = code,
            description = (
                f"Module '{code}' a {n} responsables : "
                f"{', '.join(responsables['nom_complet'].tolist())}."
            ),
            details = {
                "nb_responsables": int(n),
                "responsables":    responsables["nom_complet"].tolist(),
            },
        ))
    return anomalies


def rule_R3_3_titres_inconsistants(sources: ParsedSources) -> List[Anomaly]:
    """
    R3.3 — Titres ADE non parsables (pattern non standard).
    Sévérité : MINEUR (qualité de saisie).
    """
    anomalies: List[Anomaly] = []
    titres_inconnus = (
        sources.seances[sources.seances["code_prefix"].isna()]["title_original"]
        .value_counts()
        .head(20)  # top 20 pour limiter le bruit
    )

    for title, n in titres_inconnus.items():
        if not title:
            continue
        anomalies.append(Anomaly(
            rule_id     = "R3.3",
            dimension   = Dimension.COHERENCE,
            severity    = Severity.MINEUR,
            code_module = None,
            description = (
                f"Titre ADE non normalisé : '{title}' "
                f"({n} occurrence{'s' if n > 1 else ''})."
            ),
            details = {"title": title, "occurrences": int(n)},
        ))
    return anomalies


def rule_R3_4_possible_mauvais_tag_td_tp(sources: ParsedSources) -> List[Anomaly]:
    """
    R3.4 — Excédent de TD ≈ manque de TP : suspicion de TP mal tagués en TD dans ADE.
    Conditions (toutes vraies) :
        tph_maquette > 0
        heures_tp_ade == 0
        excedent_td > 0  ET  abs(excedent_td - tph_maquette) <= 2.0
    Sévérité : MINEUR.
    """
    anomalies: List[Anomaly] = []
    heures_ade = _calcul_heures_ade_par_module(sources.seances)

    for _, mod in sources.maquette.iterrows():
        code     = mod["code_module"]
        prefix_m = re.match(r"^([A-Z]+\d+)", code)
        if not prefix_m:
            continue
        prefix = prefix_m.group(1)

        tph_maq = float(mod["tp_h"])
        tdh_maq = float(mod["td_h"])
        if tph_maq <= 0:
            continue

        tp_ade = heures_ade[
            (heures_ade["code_prefix"] == prefix) & (heures_ade["type_seance"] == "TP")
        ]
        td_ade = heures_ade[
            (heures_ade["code_prefix"] == prefix) & (heures_ade["type_seance"] == "TD")
        ]
        heures_tp_ade = float(tp_ade["heures_ade"].sum()) if not tp_ade.empty else 0.0
        heures_td_ade = float(td_ade["heures_ade"].sum()) if not td_ade.empty else 0.0

        if heures_tp_ade != 0:
            continue

        excedent_td = heures_td_ade - tdh_maq
        if excedent_td <= 0:
            continue
        if abs(excedent_td - tph_maq) > 2.0:
            continue

        anomalies.append(Anomaly(
            rule_id     = "R3.4",
            dimension   = Dimension.COHERENCE,
            severity    = Severity.MINEUR,
            code_module = code,
            description = (
                "Des séances TD en excès correspondent aux TP manquants — "
                "vérifier si des TP ont été mal tagués en TD dans ADE"
            ),
            details = {
                "excedent_td": round(excedent_td, 2),
                "manque_tp":   round(tph_maq, 2),
                "code_module": code,
            },
        ))

    return anomalies


def run(sources: ParsedSources) -> List[Anomaly]:
    return (
        rule_R3_codes_ade_non_normalises(sources)
        + rule_R3_2_doublons_responsables(sources)
        + rule_R3_3_titres_inconsistants(sources)
        + rule_R3_4_possible_mauvais_tag_td_tp(sources)
    )
