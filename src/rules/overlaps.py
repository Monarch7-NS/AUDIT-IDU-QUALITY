"""
Rule: Unicité — Chevauchements
Detect scheduling conflicts where the same teacher or room is
assigned to two different sessions at the same time.
"""

from dataclasses import dataclass
from collections import defaultdict


@dataclass
class OverlapAnomaly:
    conflict_type: str   # "teacher" or "room"
    entity: str          # teacher name or room name
    event1_title: str
    event2_title: str
    start: str
    criticite: str = "bloquant"

    def to_dict(self) -> dict:
        label = "Enseignant" if self.conflict_type == "teacher" else "Salle"
        return {
            "dimension": "Unicité",
            "code_module": self.entity,
            "description": (
                f"{label} '{self.entity}' en double le {self.start}: "
                f"'{self.event1_title}' ET '{self.event2_title}'"
            ),
            "criticite": self.criticite,
        }


def check_overlaps(ade_events: list[dict]) -> list[OverlapAnomaly]:
    """
    Check for teacher and room scheduling conflicts.

    Uses a sweep-line approach per entity to detect overlapping intervals.

    Args:
        ade_events: All ADE events (from all three promo files, deduplicated)

    Returns:
        List of OverlapAnomaly
    """
    anomalies = []
    anomalies.extend(_check_teacher_overlaps(ade_events))
    anomalies.extend(_check_room_overlaps(ade_events))
    return anomalies


def _check_teacher_overlaps(events: list[dict]) -> list[OverlapAnomaly]:
    """One teacher cannot be in two places simultaneously."""
    by_teacher: dict[str, list[dict]] = defaultdict(list)
    for evt in events:
        for teacher in evt.get("teachers", []):
            name = teacher.strip().upper()
            if name:
                by_teacher[name].append(evt)

    return _find_overlaps(by_teacher, "teacher")


def _check_room_overlaps(events: list[dict]) -> list[OverlapAnomaly]:
    """One room cannot host two sessions simultaneously."""
    by_room: dict[str, list[dict]] = defaultdict(list)
    for evt in events:
        room = evt.get("location", "").strip()
        if room:
            by_room[room].append(evt)

    return _find_overlaps(by_room, "room")


def _find_overlaps(
    grouped: dict[str, list[dict]],
    conflict_type: str,
) -> list[OverlapAnomaly]:
    anomalies = []
    for entity, evts in grouped.items():
        sorted_evts = sorted(evts, key=lambda e: e["start"])
        for i in range(len(sorted_evts) - 1):
            e1 = sorted_evts[i]
            e2 = sorted_evts[i + 1]
            # True overlap: e2 starts before e1 ends
            if e2["start"] < e1["end"]:
                anomalies.append(
                    OverlapAnomaly(
                        conflict_type=conflict_type,
                        entity=entity,
                        event1_title=e1["title"],
                        event2_title=e2["title"],
                        start=e1["start"].strftime("%Y-%m-%d %H:%M"),
                    )
                )
    return anomalies
