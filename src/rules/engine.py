"""
src/rules/engine.py
===================
Orchestrateur du moteur de règles : exécute toutes les règles sur ParsedSources
et produit un DataFrame consolidé d'anomalies + un score qualité par dimension.
"""

from typing import List
import pandas as pd

from src.parsers.parse_all import ParsedSources
from src.rules.base import Anomaly, Severity, Dimension
from src.rules import (
    completude,
    exactitude,
    coherence,
    conformite,
    unicite,
    tracabilite,
)


# Pondération des sévérités pour le calcul du score qualité
POIDS_SEVERITE = {
    Severity.BLOQUANT: 5.0,
    Severity.MAJEUR:   2.0,
    Severity.MINEUR:   0.5,
}


def run_all_rules(sources: ParsedSources) -> List[Anomaly]:
    """Exécute toutes les règles et retourne la liste plate des anomalies."""
    anomalies: List[Anomaly] = []
    for module in [completude, exactitude, coherence, conformite, unicite, tracabilite]:
        anomalies.extend(module.run(sources))
    return anomalies


def anomalies_to_dataframe(anomalies: List[Anomaly]) -> pd.DataFrame:
    """Convertit une liste d'anomalies en DataFrame triable/filtrable."""
    if not anomalies:
        return pd.DataFrame(columns=[
            "rule_id", "dimension", "severity", "code_module", "description"
        ])
    return pd.DataFrame([a.to_dict() for a in anomalies])


def compute_quality_score(anomalies: List[Anomaly]) -> pd.DataFrame:
    """
    Calcule un score qualité par dimension (0-100, 100 = parfait).
    Score = max(0, 100 - sum(poids_sévérité * nb_anomalies) / nb_max_attendu)
    Cap à 100 anomalies pondérées par dimension.
    """
    rows = []
    for dim in Dimension:
        anos = [a for a in anomalies if a.dimension == dim]
        nb_bloquant = sum(1 for a in anos if a.severity == Severity.BLOQUANT)
        nb_majeur   = sum(1 for a in anos if a.severity == Severity.MAJEUR)
        nb_mineur   = sum(1 for a in anos if a.severity == Severity.MINEUR)

        penalite = (
            POIDS_SEVERITE[Severity.BLOQUANT] * nb_bloquant
            + POIDS_SEVERITE[Severity.MAJEUR]   * nb_majeur
            + POIDS_SEVERITE[Severity.MINEUR]   * nb_mineur
        )
        score = max(0.0, 100.0 - penalite)

        rows.append({
            "dimension":  dim.value,
            "nb_total":   len(anos),
            "bloquant":   nb_bloquant,
            "majeur":     nb_majeur,
            "mineur":     nb_mineur,
            "score":      round(score, 1),
        })
    return pd.DataFrame(rows)


def compute_global_score(score_df: pd.DataFrame) -> float:
    """Score global = moyenne arithmétique des scores par dimension."""
    return round(float(score_df["score"].mean()), 1)


def audit(sources: ParsedSources) -> dict:
    """
    Point d'entrée principal : exécute l'audit complet et retourne :
        {
            "anomalies":     DataFrame des anomalies détectées,
            "score_par_dim": DataFrame des scores par dimension,
            "score_global":  float (0-100),
            "raw":           List[Anomaly] (pour traitement avancé)
        }
    """
    anomalies = run_all_rules(sources)
    df_anom   = anomalies_to_dataframe(anomalies)
    df_score  = compute_quality_score(anomalies)
    return {
        "anomalies":     df_anom,
        "score_par_dim": df_score,
        "score_global":  compute_global_score(df_score),
        "raw":           anomalies,
    }


# ─────────────────────────────────────────────────────────────
# SCRIPT DE TEST RAPIDE
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from src.parsers.parse_all import load_all_sources

    print("Chargement des sources...")
    sources = load_all_sources()

    print("\nExecution du moteur de regles...")
    result = audit(sources)

    SEP = "-" * 70
    print(f"\n{SEP}")
    print(f"  AUDIT IDU - SCORE GLOBAL : {result['score_global']}/100")
    print(f"{SEP}")

    print("\n== SCORE PAR DIMENSION ==")
    print(SEP)
    print(result["score_par_dim"].to_string(index=False))

    print("\n== ANOMALIES PAR SEVERITE ==")
    print(SEP)
    print(result["anomalies"]["severity"].value_counts().to_string())

    print("\n== TOP 15 ANOMALIES BLOQUANTES ==")
    print(SEP)
    bloquantes = result["anomalies"][result["anomalies"]["severity"] == "bloquant"]
    cols = ["rule_id", "dimension", "code_module", "description"]
    print(bloquantes[cols].head(15).to_string(index=False))

    print(f"\n== TOTAL : {len(result['anomalies'])} anomalies detectees ==")
