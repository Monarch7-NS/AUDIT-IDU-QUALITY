"""
Rule: Complétude
Every module in the maquette must have at least one identifiable
session in ADE. Modules with 0 planned hours of a given type
are exempt for that type.
"""

from dataclasses import dataclass


@dataclass
class CompletenessAnomaly:
    code_module: str
    nom: str
    missing_types: list[str]
    criticite: str = "bloquant"

    def to_dict(self) -> dict:
        return {
            "dimension": "Complétude",
            "code_module": self.code_module,
            "description": (
                f"Module '{self.nom}' absent de l'ADE pour les types: "
                f"{', '.join(self.missing_types)}"
            ),
            "criticite": self.criticite,
        }


def check_completeness(
    maquette: list[dict],
    ade_events: list[dict],
) -> list[CompletenessAnomaly]:
    """
    Check that every maquette module has ≥1 ADE session per planned type.

    Args:
        maquette:   Output of parse_maquette()
        ade_events: Deduplicated events from all three ADE files

    Returns:
        List of CompletenessAnomaly (one per fully-missing module)
    """
    # Build set of (code, type) pairs actually present in ADE
    ade_present: set[tuple[str, str]] = set()
    for evt in ade_events:
        if evt["code"] and evt["session_type"] != "UNKNOWN":
            ade_present.add((evt["code"], evt["session_type"]))

    anomalies = []
    for mod in maquette:
        code = mod["code_module"]
        missing = []
        for stype in ("CM", "TD", "TP"):
            planned_hours = mod[stype.lower()]
            if planned_hours > 0:
                if (code, stype) not in ade_present:
                    missing.append(stype)

        if missing:
            # Bloquant if ALL planned types are missing, majeur otherwise
            all_types = [
                s for s in ("CM", "TD", "TP") if mod[s.lower()] > 0
            ]
            criticite = "bloquant" if set(missing) == set(all_types) else "majeur"
            anomalies.append(
                CompletenessAnomaly(
                    code_module=code,
                    nom=mod["nom"],
                    missing_types=missing,
                    criticite=criticite,
                )
            )

    return anomalies
