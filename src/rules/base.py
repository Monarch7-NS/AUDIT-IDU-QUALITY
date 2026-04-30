"""
src/rules/base.py
=================
Modèle commun à toutes les règles d'audit.
Définit les types Anomaly, Severity, Dimension utilisés par chaque module de règles.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    """Criticité d'une anomalie selon la grille du sujet hackathon."""
    BLOQUANT = "bloquant"
    MAJEUR   = "majeur"
    MINEUR   = "mineur"


class Dimension(str, Enum):
    """Les 6 dimensions du référentiel qualité de la donnée."""
    COMPLETUDE   = "Complétude"
    EXACTITUDE   = "Exactitude"
    COHERENCE    = "Cohérence"
    CONFORMITE   = "Conformité"
    UNICITE      = "Unicité"
    TRACABILITE  = "Traçabilité"


@dataclass
class Anomaly:
    """
    Une anomalie détectée par une règle.

    Attributs:
        rule_id     : identifiant de la règle (ex "R1.1")
        dimension   : dimension qualité concernée
        severity    : niveau de criticité
        description : description en langage naturel pour le rapport
        code_module : module IDU concerné (None si transverse)
        details     : informations contextuelles (heures, dates, salles, etc.)
    """
    rule_id:     str
    dimension:   Dimension
    severity:    Severity
    description: str
    code_module: Optional[str]    = None
    details:     dict[str, Any]   = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_id":     self.rule_id,
            "dimension":   self.dimension.value,
            "severity":    self.severity.value,
            "code_module": self.code_module,
            "description": self.description,
            **self.details,
        }
