"""
Audit Engine — orchestrates all quality rules and produces
the consolidated anomaly report.

Usage (CLI):
    python -m src.rules.engine
    python -m src.rules.engine --data-dir ./data --output-dir ./output
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

from source_code.src.parsers import (
    parse_maquette,
    parse_ade,
    parse_responsables,
    parse_dependances,
    parse_moodle,
)
from source_code.src.rules import (
    check_completeness,
    check_exactitude,
    check_sequencing,
    check_overlaps,
    check_responsables,
)


def run_audit(
    data_dir: Path,
    output_dir: Path,
) -> dict:
    """
    Run the full data quality audit pipeline.

    Args:
        data_dir:   Directory containing all source JSON/HTML files
        output_dir: Directory where report files will be written

    Returns:
        Audit result dict with keys:
            generated_at, summary, anomalies, scores
    """
    print("=== Audit IDU — Qualité de la Donnée ===\n")

    # ------------------------------------------------------------------ #
    # 1. Ingestion
    # ------------------------------------------------------------------ #
    print("[1/3] Chargement des sources…")
    maquette = parse_maquette(data_dir / "MAQUETTE_IDU.json")
    responsables_map = parse_responsables(
        data_dir / "Responsables_modules_IDU.json"
    )
    dependances = parse_dependances(
        data_dir / "dependance_sequence_IDU.json"
    )

    known_codes = {m["code_module"] for m in maquette}

    ade3 = parse_ade(data_dir / "ADECal_IDU3.json", "IDU3", known_codes)
    ade4 = parse_ade(data_dir / "ADECal_IDU4.json", "IDU4", known_codes)
    ade5 = parse_ade(data_dir / "ADECal_IDU5.json", "IDU5", known_codes)
    all_events = ade3 + ade4 + ade5

    moodle_path = data_dir / "Résumé Moodle IDU.html"
    moodle_courses = parse_moodle(moodle_path) if moodle_path.exists() else []

    print(
        f"   Maquette: {len(maquette)} modules | "
        f"ADE events: {len(all_events)} | "
        f"Moodle courses: {len(moodle_courses)}"
    )

    # ------------------------------------------------------------------ #
    # 2. Rules engine
    # ------------------------------------------------------------------ #
    print("[2/3] Application des règles qualité…")

    completeness_anomalies = check_completeness(maquette, all_events)
    exactitude_anomalies = check_exactitude(maquette, all_events)
    sequencing_violations = check_sequencing(all_events, dependances)
    overlap_anomalies = check_overlaps(all_events)
    responsable_anomalies = check_responsables(maquette, responsables_map)

    all_anomalies = (
        [a.to_dict() for a in completeness_anomalies]
        + [a.to_dict() for a in exactitude_anomalies]
        + [a.to_dict() for a in sequencing_violations]
        + [a.to_dict() for a in overlap_anomalies]
        + [a.to_dict() for a in responsable_anomalies]
    )

    # ------------------------------------------------------------------ #
    # 3. Scoring
    # ------------------------------------------------------------------ #
    scores = _compute_scores(
        maquette=maquette,
        completeness_anomalies=completeness_anomalies,
        exactitude_anomalies=exactitude_anomalies,
        sequencing_violations=sequencing_violations,
        overlap_anomalies=overlap_anomalies,
        responsable_anomalies=responsable_anomalies,
        dependances=dependances,
    )

    summary = {
        "total_anomalies": len(all_anomalies),
        "bloquant": sum(1 for a in all_anomalies if a["criticite"] == "bloquant"),
        "majeur": sum(1 for a in all_anomalies if a["criticite"] == "majeur"),
        "mineur": sum(1 for a in all_anomalies if a["criticite"] == "mineur"),
        "global_score": scores["global"],
    }

    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "scores": scores,
        "anomalies": all_anomalies,
        "events": all_events,
    }

    # ------------------------------------------------------------------ #
    # 4. Output
    # ------------------------------------------------------------------ #
    print("[3/3] Génération du rapport…")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "audit_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    _print_summary(summary, scores)
    print(f"\nRapport écrit dans : {output_dir.resolve()}")
    print(f"  → {json_path.name}")

    return report


def _compute_scores(
    maquette,
    completeness_anomalies,
    exactitude_anomalies,
    sequencing_violations,
    overlap_anomalies,
    responsable_anomalies,
    dependances,
) -> dict:
    n_modules = len(maquette)
    n_deps = len(dependances)

    completeness_score = max(
        0, 100 - len(completeness_anomalies) / max(n_modules, 1) * 100
    )
    exactitude_score = max(
        0, 100 - len(exactitude_anomalies) / max(n_modules * 3, 1) * 100
    )
    sequencing_score = max(
        0, 100 - len(sequencing_violations) / max(n_deps, 1) * 100
    )
    overlap_score = 100.0 if not overlap_anomalies else max(
        0, 100 - len(overlap_anomalies) * 10
    )
    responsable_score = max(
        0, 100 - len(responsable_anomalies) / max(n_modules, 1) * 100
    )

    # Weighted global score (weights reflect pedagogical criticality)
    weights = {
        "completeness": 0.25,
        "exactitude": 0.20,
        "sequencing": 0.25,
        "overlaps": 0.15,
        "responsables": 0.15,
    }
    global_score = (
        completeness_score * weights["completeness"]
        + exactitude_score * weights["exactitude"]
        + sequencing_score * weights["sequencing"]
        + overlap_score * weights["overlaps"]
        + responsable_score * weights["responsables"]
    )

    return {
        "global": round(global_score, 1),
        "completude": round(completeness_score, 1),
        "exactitude": round(exactitude_score, 1),
        "conformite": round(sequencing_score, 1),
        "unicite": round(overlap_score, 1),
        "coherence": round(responsable_score, 1),
    }


def _print_summary(summary: dict, scores: dict) -> None:
    print("\n" + "=" * 50)
    print(f"  Score global : {scores['global']:.0f}/100")
    print("=" * 50)
    print(f"  Total anomalies : {summary['total_anomalies']}")
    print(f"    Bloquantes     : {summary['bloquant']}")
    print(f"    Majeures       : {summary['majeur']}")
    print(f"    Mineures       : {summary['mineur']}")
    print("-" * 50)
    print(f"  Complétude   : {scores['completude']:.0f}/100")
    print(f"  Exactitude   : {scores['exactitude']:.0f}/100")
    print(f"  Conformité   : {scores['conformite']:.0f}/100")
    print(f"  Unicité      : {scores['unicite']:.0f}/100")
    print(f"  Cohérence    : {scores['coherence']:.0f}/100")
    print("=" * 50)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit de qualité des données pédagogiques IDU"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Répertoire contenant les fichiers sources (défaut: ./data)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Répertoire de sortie pour les rapports (défaut: ./output)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_audit(data_dir=args.data_dir, output_dir=args.output_dir)
