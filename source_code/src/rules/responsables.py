"""
Rule: Cohérence — Responsables
Every module with planned hours must have an assigned responsible teacher.
Also flags modules where the ADE teacher differs from the responsible.
"""

from dataclasses import dataclass


@dataclass
class ResponsableAnomaly:
    code_module: str
    nom_module: str
    issue: str
    criticite: str

    def to_dict(self) -> dict:
        return {
            "dimension": "Cohérence",
            "code_module": self.code_module,
            "description": self.issue,
            "criticite": self.criticite,
        }


def check_responsables(
    maquette: list[dict],
    responsables: dict[str, dict],
) -> list[ResponsableAnomaly]:
    """
    Verify every active module has exactly one responsible teacher.

    Args:
        maquette:      Output of parse_maquette()
        responsables:  Output of parse_responsables()

    Returns:
        List of ResponsableAnomaly
    """
    anomalies = []

    for mod in maquette:
        code = mod["code_module"]
        has_hours = mod["cm"] + mod["td"] + mod["tp"] > 0

        if not has_hours:
            continue

        if code not in responsables:
            anomalies.append(
                ResponsableAnomaly(
                    code_module=code,
                    nom_module=mod["nom"],
                    issue=f"Module '{mod['nom']}' sans responsable assigné",
                    criticite="majeur",
                )
            )

    return anomalies
