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

from src.parsers import (
    parse_maquette,
    parse_ade,
    parse_responsables,
    parse_dependances,
    parse_moodle,
)
from src.rules import (
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
    }

    # ------------------------------------------------------------------ #
    # 4. Output
    # ------------------------------------------------------------------ #
    print("[3/3] Génération du rapport…")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "audit_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    html_path = output_dir / "audit_report.html"
    _write_html_report(report, html_path)

    _print_summary(summary, scores)
    print(f"\nRapports écrits dans : {output_dir.resolve()}")
    print(f"  → {json_path.name}")
    print(f"  → {html_path.name}")

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


def _write_html_report(report: dict, path: Path) -> None:
    """Write a minimal standalone HTML audit report."""
    anomalies = report["anomalies"]
    scores = report["scores"]
    summary = report["summary"]
    generated = report["generated_at"][:19].replace("T", " ")

    color_map = {"bloquant": "#E24B4A", "majeur": "#EF9F27", "mineur": "#639922"}

    rows = ""
    for a in anomalies:
        c = a["criticite"]
        color = color_map.get(c, "#888")
        rows += (
            f"<tr>"
            f"<td>{a['dimension']}</td>"
            f"<td><code>{a['code_module']}</code></td>"
            f"<td>{a['description']}</td>"
            f"<td style='color:{color};font-weight:500'>{c}</td>"
            f"</tr>\n"
        )

    dim_rows = ""
    labels = {
        "completude": "Complétude",
        "exactitude": "Exactitude",
        "conformite": "Conformité",
        "unicite": "Unicité",
        "coherence": "Cohérence",
    }
    for key, label in labels.items():
        score = scores[key]
        bar_color = "#E24B4A" if score < 60 else "#EF9F27" if score < 80 else "#639922"
        dim_rows += (
            f"<tr><td>{label}</td><td>"
            f"<div style='background:#eee;border-radius:4px;height:12px;width:200px'>"
            f"<div style='background:{bar_color};width:{score}%;height:12px;"
            f"border-radius:4px'></div></div></td>"
            f"<td><b>{score:.0f}/100</b></td></tr>\n"
        )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Rapport Audit IDU — Qualité des données</title>
<style>
  body{{font-family:sans-serif;max-width:1100px;margin:2rem auto;color:#222}}
  h1{{color:#534AB7}}h2{{color:#3C3489;margin-top:2rem}}
  table{{border-collapse:collapse;width:100%;margin-top:1rem}}
  th,td{{padding:8px 12px;border:1px solid #ddd;font-size:13px;text-align:left}}
  th{{background:#f4f4f8;font-weight:500}}
  tr:nth-child(even){{background:#fafafa}}
  .score{{font-size:3rem;font-weight:700;color:#534AB7}}
  .meta{{color:#888;font-size:13px}}
  .badge{{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500;color:#fff}}
</style>
</head>
<body>
<h1>Rapport d'Audit — Qualité de la Donnée IDU</h1>
<p class="meta">Généré le {generated}</p>

<h2>Score global</h2>
<p class="score">{scores['global']:.0f}<span style="font-size:1.5rem">/100</span></p>
<p>
  <span class="badge" style="background:#E24B4A">{summary['bloquant']} bloquantes</span>
  <span class="badge" style="background:#EF9F27">{summary['majeur']} majeures</span>
  <span class="badge" style="background:#639922">{summary['mineur']} mineures</span>
  — {summary['total_anomalies']} anomalies au total
</p>

<h2>Scores par dimension</h2>
<table><thead><tr><th>Dimension</th><th>Score</th><th>Valeur</th></tr></thead>
<tbody>{dim_rows}</tbody></table>

<h2>Toutes les anomalies ({summary['total_anomalies']})</h2>
<table>
<thead><tr><th>Dimension</th><th>Module</th><th>Description</th><th>Criticité</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body></html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


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
