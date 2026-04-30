# Audit IDU — Qualité de la Donnée Pédagogique

> Hackathon IDU · Polytech Annecy-Chambéry

Pipeline d'audit de qualité des données pédagogiques de la filière IDU.

---

## Structure du projet


## Installation

```bash
git clone https://github.com/TON-PSEUDO/audit-idu-qualite.git
cd audit-idu-qualite
pip install -r requirements.txt
```

## Données sources

Placer ces fichiers dans `data/` (partagés via Drive, **non versionnés**) :

```
data/MAQUETTE_IDU.json
data/ADECal_IDU3.json
data/ADECal_IDU4.json
data/ADECal_IDU5.json
data/Responsables_modules_IDU.json
data/dependance_sequence_IDU.json
data/Résumé Moodle IDU.html
```

## Utilisation

```bash
# Lancer l'audit (CLI) → génère output/audit_report.json + .html
make audit

# Lancer le dashboard interactif
make run

# Tests avec couverture
make test

# Lint
make lint
```

## Dimensions auditées

| Dimension | Règle | Fichier |
|-----------|-------|---------|
| Complétude | Chaque module maquette a ≥1 séance ADE | `completeness.py` |
| Exactitude | Heures ADE ≈ heures maquette (±15%) | `exactitude.py` |
| Conformité | CM planifié avant TD/TP | `sequencing.py` |
| Unicité | Pas de chevauchement enseignant/salle | `overlaps.py` |
| Cohérence | Chaque module a un responsable | `responsables.py` |

## Conventions de commits

```
feat:   Nouvelle fonctionnalité
test:   Ajout/modification de tests
fix:    Correction de bug
chore:  Maintenance / config
docs:   Documentation
```
