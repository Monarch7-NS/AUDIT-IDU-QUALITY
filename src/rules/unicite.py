"""
src/rules/unicite.py
====================
Dimension Unicité : pas de double-affectation enseignant/groupe/salle au même créneau.
"""

from typing import List
import pandas as pd

from src.parsers.parse_all import ParsedSources
from src.rules.base import Anomaly, Severity, Dimension


def rule_R5_enseignant_double_creneau(sources: ParsedSources) -> List[Anomaly]:
    """
    R5.1 — Un même enseignant planifié dans deux séances distinctes au même créneau.
    Sévérité : BLOQUANT (impossibilité physique).
    """
    anomalies: List[Anomaly] = []
    df = sources.seances[
        sources.seances["enseignants"].apply(lambda x: bool(x))
        & sources.seances["starts_utc"].notna()
    ].copy()

    # Explode pour avoir une ligne par (enseignant, séance)
    df_exp = df.explode("enseignants").rename(columns={"enseignants": "enseignant"})
    df_exp = df_exp[df_exp["enseignant"].notna()]

    # Clé : enseignant + créneau
    grouped = df_exp.groupby(["enseignant", "starts_utc"])
    for (ens, starts), groupe in grouped:
        if len(groupe) <= 1:
            continue
        salles = groupe["salle"].dropna().unique().tolist()
        if len(salles) <= 1:
            continue  # même salle → pas de conflit physique
        titres = groupe["title_original"].tolist()
        anomalies.append(Anomaly(
            rule_id     = "R5.1",
            dimension   = Dimension.UNICITE,
            severity    = Severity.BLOQUANT,
            code_module = None,
            description = (
                f"Enseignant {ens} planifié dans {len(salles)} salles "
                f"simultanément le {starts} : {salles}."
            ),
            details = {
                "enseignant": ens,
                "starts_utc": str(starts),
                "salles":     salles,
                "titres":     titres,
            },
        ))
    return anomalies


def rule_R5_2_capacite_salle_insuffisante(sources: ParsedSources) -> List[Anomaly]:
    """
    R5.2 — Salle de capacité < 12 utilisée pour une séance non-TP/non-projet.
    Heuristique simple — la vraie règle dépend de la taille du groupe.
    Sévérité : MINEUR.
    """
    anomalies: List[Anomaly] = []
    df = sources.seances[
        sources.seances["capacite"].notna()
        & (sources.seances["capacite"] < 12)
        & sources.seances["type_seance"].isin(["CM", "TD"])
    ]

    for _, row in df.iterrows():
        anomalies.append(Anomaly(
            rule_id     = "R5.2",
            dimension   = Dimension.UNICITE,
            severity    = Severity.MINEUR,
            code_module = row["code_prefix"],
            description = (
                f"Séance {row['type_seance']} '{row['title_original']}' planifiée "
                f"dans salle '{row['salle']}' avec {int(row['capacite'])} places — "
                f"capacité potentiellement insuffisante."
            ),
            details = {
                "salle":     row["salle"],
                "capacite":  int(row["capacite"]),
                "type":      row["type_seance"],
                "starts":    str(row["starts_utc"]),
            },
        ))
    return anomalies


def run(sources: ParsedSources) -> List[Anomaly]:
    return (
        rule_R5_enseignant_double_creneau(sources)
        + rule_R5_2_capacite_salle_insuffisante(sources)
    )
