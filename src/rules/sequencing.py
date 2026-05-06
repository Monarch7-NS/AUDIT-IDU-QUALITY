"""
Rule: Conformité — Séquencement pédagogique
For each dependency (A must precede B) in dependance_sequence_IDU.json,
verify that session A is scheduled before session B in ADE.
"""

from dataclasses import dataclass
from collections import defaultdict


@dataclass
class SequencingViolation:
    module: str
    preceding: str       # e.g. "CM #3"
    following: str       # e.g. "TD #3"
    prec_date: str
    suiv_date: str
    delta_days: int
    criticite: str

    def to_dict(self) -> dict:
        return {
            "dimension": "Conformité",
            "code_module": self.module,
            "description": (
                f"{self.following} ({self.suiv_date}) planifié avant "
                f"{self.preceding} ({self.prec_date}) "
                f"— écart {abs(self.delta_days)}j"
            ),
            "criticite": self.criticite,
        }


def check_sequencing(
    ade_events: list[dict],
    dependances: list[dict],
) -> list[SequencingViolation]:
    """
    Detect sessions scheduled in the wrong pedagogical order.

    Args:
        ade_events:  Deduplicated ADE events (from parse_ade × 3 files)
        dependances: Output of parse_dependances()

    Returns:
        List of SequencingViolation where a following session
        is scheduled before (or the same time as) its preceding session
    """
    # Index: (code, type) → list of events sorted by start date
    session_index = _build_session_index(ade_events)

    violations = []
    for dep in dependances:
        mod_prec = dep["module_precedent"]
        type_prec = dep["type_precedent"]
        num_prec = dep["numero_precedent"]
        mod_suiv = dep["module_suivant"]
        type_suiv = dep["type_suivant"]
        num_suiv = dep["numero_suivant"]

        sessions_prec = session_index.get((mod_prec, type_prec), [])
        sessions_suiv = session_index.get((mod_suiv, type_suiv), [])

        # Only check if both sessions exist in ADE
        if len(sessions_prec) < num_prec or len(sessions_suiv) < num_suiv:
            continue

        prec_evt = sessions_prec[num_prec - 1]
        suiv_evt = sessions_suiv[num_suiv - 1]

        # Violation: following session ends before preceding starts
        if suiv_evt["start"] <= prec_evt["end"]:
            delta = (
                suiv_evt["start"] - prec_evt["start"]
            ).days
            criticite = "bloquant" if delta < -7 else "majeur" if delta < 0 else "mineur"
            violations.append(
                SequencingViolation(
                    module=mod_prec,
                    preceding=f"{type_prec} #{num_prec}",
                    following=f"{type_suiv} #{num_suiv}",
                    prec_date=prec_evt["start"].strftime("%Y-%m-%d"),
                    suiv_date=suiv_evt["start"].strftime("%Y-%m-%d"),
                    delta_days=delta,
                    criticite=criticite,
                )
            )

    return violations


def _build_session_index(
    events: list[dict],
) -> dict[tuple[str, str], list[dict]]:
    """
    Build a dict mapping (code, session_type) → sessions sorted by start.
    Deduplicated by (code, type, start, end).
    """
    seen: set[tuple] = set()
    grouped: dict[tuple, list] = defaultdict(list)

    for evt in events:
        code = evt.get("code")
        stype = evt.get("session_type")
        if not code or stype == "UNKNOWN":
            continue
        key = (code, stype, evt["start"], evt["end"])
        if key in seen:
            continue
        seen.add(key)
        grouped[(code, stype)].append(evt)

    # Sort each group by start time
    return {k: sorted(v, key=lambda e: e["start"]) for k, v in grouped.items()}
