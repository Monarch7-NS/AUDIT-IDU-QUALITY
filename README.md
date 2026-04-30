# Audit IDU — Qualité de la Donnée Pédagogique

> Hackathon IDU · Polytech Annecy-Chambéry

Pipeline d'audit de qualité des données pédagogiques de la filière IDU.

---

## Structure du projet

```
audit-idu-qualite/
├── src/
│   ├── parsers/          # Ingestion des sources hétérogènes
│   │   ├── maquette.py   # MAQUETTE_IDU.json
│   │   ├── ade.py        # ADECal_IDU3/4/5.json
│   │   ├── responsables.py
│   │   ├── dependances.py
│   │   └── moodle.py     # Résumé Moodle IDU.html
│   └── rules/            # Moteur de règles qualité
│       ├── engine.py     # Orchestrateur principal
│       ├── completeness.py
│       ├── exactitude.py
│       ├── sequencing.py
│       ├── overlaps.py
│       └── responsables.py
├── app/
│   └── dashboard.py      # Dashboard Streamlit interactif
├── tests/
│   ├── test_parsers.py
│   └── test_rules.py
├── data/                 # Fichiers sources (non versionnés)
├── output/               # Rapports générés (non versionnés)
├── .github/workflows/ci.yml
├── Makefile
└── requirements.txt
```

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
