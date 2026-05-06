"""
Rule: Exactitude
ADE hours per module/type must match maquette within ±15%.
Sessions are deduplicated by (code, type, start, end) to avoid
double-counting multi-group events.
"""

from dataclasses import dataclass
from collections import defaultdict


THRESHOLD_PCT = 15.0


@dataclass
class ExactitudeAnomaly:
    code_module: str
    session_type: str
    planned_h: float
    ade_h: float
    pct_diff: float
    criticite: str

    def to_dict(self) -> dict:
        direction = "excès" if self.ade_h > self.planned_h else "manque"
        return {
            "dimension": "Exactitude",
            "code_module": self.code_module,
            "description": (
                f"{self.session_type} — prévu {self.planned_h}h, "
                f"ADE {self.ade_h:.1f}h "
                f"({direction} de {self.pct_diff:.0f}%)"
            ),
            "criticite": self.criticite,
        }


def check_exactitude(
    maquette: list[dict],
    ade_events: list[dict],
    threshold_pct: float = THRESHOLD_PCT,
) -> list[ExactitudeAnomaly]:
    """
    Compare planned hours (maquette) vs actual hours (ADE) per module/type.

    Sessions with the same (code, type, start, end) are counted once,
    regardless of how many groups appear in different ADE files.

    Args:
        maquette:       Output of parse_maquette()
        ade_events:     All events from all three ADE files (may contain dupes)
        threshold_pct:  Maximum acceptable percentage difference (default 15%)

    Returns:
        List of ExactitudeAnomaly for each module/type exceeding the threshold
    """
    ade_hours = _compute_ade_hours(ade_events)
    maquette_dict = {m["code_module"]: m for m in maquette}

    anomalies = []
    for code, mod in maquette_dict.items():
        for stype in ("CM", "TD", "TP"):
            planned = mod[stype.lower()]
            actual = ade_hours[code].get(stype, 0.0)

            if planned == 0 and actual == 0:
                continue

            if planned > 0:
                pct_diff = abs(actual - planned) / planned * 100
            else:
                pct_diff = 100.0  # something in ADE not in maquette

            if pct_diff > threshold_pct:
                criticite = _classify(planned, actual, pct_diff)
                anomalies.append(
                    ExactitudeAnomaly(
                        code_module=code,
                        session_type=stype,
                        planned_h=planned,
                        ade_h=round(actual, 1),
                        pct_diff=round(pct_diff, 1),
                        criticite=criticite,
                    )
                )

    # Sort by severity descending
    anomalies.sort(key=lambda a: -a.pct_diff)
    return anomalies


def _compute_ade_hours(events: list[dict]) -> dict[str, dict[str, float]]:
    """
    Sum ADE hours per (module_code, session_type), deduplicating
    sessions that appear multiple times due to multi-group scheduling.
    """
    seen_slots: set[tuple] = set()
    hours: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for evt in events:
        code = evt.get("code")
        stype = evt.get("session_type")
        if not code or stype == "UNKNOWN":
            continue

        slot_key = (code, stype, evt["start"], evt["end"])
        if slot_key in seen_slots:
            continue
        seen_slots.add(slot_key)

        hours[code][stype] += evt["duration_h"]

    return hours


def _classify(planned: float, actual: float, pct_diff: float) -> str:
    if planned == 0:
        return "majeur"
    if actual == 0:
        return "bloquant"
    if pct_diff >= 50:
        return "majeur"
    return "mineur"
