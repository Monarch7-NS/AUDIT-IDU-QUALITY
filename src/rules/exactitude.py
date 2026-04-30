"""
src/rules/exactitude.py
=======================
Dimension Exactitude : les volumes horaires ADE correspondent-ils à la maquette ?
"""

import re
from typing import List

import pandas as pd

from src.parsers.parse_all import ParsedSources
from src.rules.base import Anomaly, Severity, Dimension


# Seuil d'écart toléré entre heures maquette et heures ADE (±15% selon brief)
SEUIL_ECART = 0.15


def _calcul_heures_ade_par_module(seances: pd.DataFrame) -> pd.DataFrame:
    """
    Agrège les heures ADE par (préfixe module, type de séance).
    Utilise code_maquette (qui intègre le mapping ADE→Maquette).
    Exclut séances sans code, sans type, manquantes en maquette, et examens.

    Déduplication des groupes parallèles : pour les séances is_parallel_grp=True,
    on ne compte qu'une seule occurrence par (code_prefix, type_seance, starts_utc)
    afin que G1+G2 au même horaire ne pèsent que pour un créneau réel.
    """
    df = seances[
        seances["code_maquette"].notna()
        & seances["type_seance"].notna()
        & seances["famille_manquante"].isna()
        & ~seances["is_exam"]
    ].copy()
    # Préfixe extrait du code_maquette pour matcher la maquette
    df["prefix_maq"] = df["code_maquette"].str.extract(r"^([A-Z]+\d+)")
    df = df.dropna(subset=["prefix_maq"])

    non_parallel = df[~df["is_parallel_grp"].fillna(False).astype(bool)]
    parallel     = df[ df["is_parallel_grp"].fillna(False).astype(bool)]
    parallel_dedup = parallel.drop_duplicates(
        subset=["code_prefix", "type_seance", "starts_utc"]
    )
    df_dedup = pd.concat([non_parallel, parallel_dedup], ignore_index=True)

    return (
        df_dedup.groupby(["prefix_maq", "type_seance"])["duration_h"]
        .sum()
        .reset_index()
        .rename(columns={"duration_h": "heures_ade", "prefix_maq": "code_prefix"})
    )


def rule_R2_ecart_heures_par_type(sources: ParsedSources) -> List[Anomaly]:
    """
    R2.1 — Écart heures maquette vs heures ADE par type (CM, TD, TP).
    Sévérité : BLOQUANT si écart > 50%, MAJEUR si > 25%, MINEUR si > 15%.
    """
    anomalies: List[Anomaly] = []
    heures_ade = _calcul_heures_ade_par_module(sources.seances)

    for _, mod in sources.maquette.iterrows():
        code      = mod["code_module"]
        prefix_m  = re.match(r"^([A-Z]+\d+)", code)
        if not prefix_m:
            continue
        prefix = prefix_m.group(1)

        for type_canon, col_h in [("CM", "cm_h"), ("TD", "td_h"), ("TP", "tp_h")]:
            heures_prev = float(mod[col_h])
            ade_match = heures_ade[
                (heures_ade["code_prefix"] == prefix)
                & (heures_ade["type_seance"] == type_canon)
            ]
            heures_reel = float(ade_match["heures_ade"].sum()) if not ade_match.empty else 0.0

            # Pas de séance ET pas prévu → rien à signaler
            if heures_prev == 0 and heures_reel == 0:
                continue

            # Type prévu mais 0 séance → géré par R1.1 globalement
            if heures_prev > 0 and heures_reel == 0:
                anomalies.append(Anomaly(
                    rule_id     = "R2.1",
                    dimension   = Dimension.EXACTITUDE,
                    severity    = Severity.BLOQUANT,
                    code_module = code,
                    description = (
                        f"{code} : {heures_prev:.1f}h de {type_canon} prévues "
                        f"en maquette mais 0 séance trouvée dans ADE."
                    ),
                    details = {
                        "type":         type_canon,
                        "heures_prev":  heures_prev,
                        "heures_ade":   heures_reel,
                        "ecart_pct":    -100.0,
                    },
                ))
                continue

            # Séance ADE non prévue par maquette
            if heures_prev == 0 and heures_reel > 0:
                anomalies.append(Anomaly(
                    rule_id     = "R2.2",
                    dimension   = Dimension.EXACTITUDE,
                    severity    = Severity.MAJEUR,
                    code_module = code,
                    description = (
                        f"{code} : {heures_reel:.1f}h de {type_canon} dans ADE "
                        f"mais 0h prévue par la maquette pour ce type."
                    ),
                    details = {
                        "type":         type_canon,
                        "heures_prev":  heures_prev,
                        "heures_ade":   heures_reel,
                    },
                ))
                continue

            # Calcul de l'écart relatif
            ecart      = heures_reel - heures_prev
            ecart_pct  = ecart / heures_prev * 100
            ecart_abs  = abs(ecart_pct)

            if ecart_abs <= SEUIL_ECART * 100:
                continue

            if ecart_abs > 50:
                severity = Severity.BLOQUANT
            elif ecart_abs > 25:
                severity = Severity.MAJEUR
            else:
                severity = Severity.MINEUR

            anomalies.append(Anomaly(
                rule_id     = "R2.1",
                dimension   = Dimension.EXACTITUDE,
                severity    = severity,
                code_module = code,
                description = (
                    f"{code} ({type_canon}) : écart de {ecart_pct:+.0f}% — "
                    f"prévu {heures_prev:.1f}h, déployé {heures_reel:.1f}h."
                ),
                details = {
                    "type":         type_canon,
                    "heures_prev":  heures_prev,
                    "heures_ade":   round(heures_reel, 2),
                    "ecart_h":      round(ecart, 2),
                    "ecart_pct":    round(ecart_pct, 1),
                },
            ))

    return anomalies


def rule_R2_3_durees_aberrantes(sources: ParsedSources) -> List[Anomaly]:
    """
    R2.3 — Séances avec durée aberrante (≤0h, >8h).
    Sévérité : MINEUR (probable erreur de saisie).
    """
    anomalies: List[Anomaly] = []
    s = sources.seances
    aberrantes = s[(s["duration_h"] <= 0) | (s["duration_h"] > 8)]

    for _, row in aberrantes.iterrows():
        anomalies.append(Anomaly(
            rule_id     = "R2.3",
            dimension   = Dimension.EXACTITUDE,
            severity    = Severity.MINEUR,
            code_module = row["code_prefix"],
            description = (
                f"Séance '{row['title_original']}' avec durée aberrante "
                f"({row['duration_h']:.2f}h) le {row['starts_utc']}."
            ),
            details = {
                "title":      row["title_original"],
                "duration_h": float(row["duration_h"]),
                "starts_utc": str(row["starts_utc"]),
                "salle":      row["salle"],
            },
        ))
    return anomalies


def _no_enseignant(val) -> bool:
    """True si le champ enseignants est vide (liste vide, str vide, None, NaN)."""
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, (list, tuple, str)):
        return len(val) == 0
    return False


def rule_R2_4_tp_duree_courte(sources: ParsedSources) -> List[Anomaly]:
    """
    R2.4 — TP de moins de 4h : probablement un CM ou TD mal tagué.
    Sévérité : MINEUR.
    Exclut EXAM et séances is_parallel_grp=True.
    """
    anomalies: List[Anomaly] = []
    s = sources.seances
    if s.empty:
        return anomalies
    mask = (
        (s["type_seance"] == "TP")
        & (s["duration_h"] < 4.0)
        & ~s["is_exam"].fillna(False).astype(bool)
        & ~s["is_parallel_grp"].fillna(False).astype(bool)
    )
    for _, row in s[mask].iterrows():
        anomalies.append(Anomaly(
            rule_id     = "R2.4",
            dimension   = Dimension.EXACTITUDE,
            severity    = Severity.MINEUR,
            code_module = row.get("code_prefix"),
            description = "TP de moins de 4h — probablement un CM ou TD mal tagué",
            details = {
                "duration_h": float(row["duration_h"]),
                "title":      row["title_original"],
            },
        ))
    return anomalies


def rule_R2_5_seance_sans_enseignant(sources: ParsedSources) -> List[Anomaly]:
    """
    R2.5 — Séance sans enseignant (asymétrique selon le type) :
        CM → BLOQUANT (saisie ADE incomplète)
        TP → MINEUR  (auto-formation ou oubli ?)
        TD/EXAM → ignoré.
    """
    anomalies: List[Anomaly] = []
    s = sources.seances
    if s.empty:
        return anomalies

    no_ens = s["enseignants"].apply(_no_enseignant)

    for _, row in s[(s["type_seance"] == "CM") & no_ens].iterrows():
        anomalies.append(Anomaly(
            rule_id     = "R2.5",
            dimension   = Dimension.EXACTITUDE,
            severity    = Severity.BLOQUANT,
            code_module = row.get("code_prefix"),
            description = "CM sans enseignant — saisie ADE incomplète",
            details = {
                "title":      row["title_original"],
                "starts_utc": str(row.get("starts_utc")),
                "type":       "CM",
            },
        ))

    for _, row in s[(s["type_seance"] == "TP") & no_ens].iterrows():
        anomalies.append(Anomaly(
            rule_id     = "R2.5",
            dimension   = Dimension.EXACTITUDE,
            severity    = Severity.MINEUR,
            code_module = row.get("code_prefix"),
            description = "TP sans enseignant — auto-formation ou oubli ?",
            details = {
                "title":      row["title_original"],
                "starts_utc": str(row.get("starts_utc")),
                "type":       "TP",
            },
        ))

    return anomalies


def run(sources: ParsedSources) -> List[Anomaly]:
    """Exécute toutes les règles d'exactitude."""
    return (
        rule_R2_ecart_heures_par_type(sources)
        + rule_R2_3_durees_aberrantes(sources)
        + rule_R2_4_tp_duree_courte(sources)
        + rule_R2_5_seance_sans_enseignant(sources)
    )
