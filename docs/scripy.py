
doc = """# Documentation Technique — Audit Qualité IDU
## Projet : Hackathon IDU — Qualité de la donnée ADE / Maquette

---

## Table des matières

1. [Architecture générale](#1-architecture-générale)
2. [Parsers — `parse_all.py`](#2-parsers--parse_allpy)
   - 2.1 [Constantes et mappings](#21-constantes-et-mappings)
   - 2.2 [parse_ade_title](#22-parse_ade_title)
   - 2.3 [parse_maquette](#23-parse_maquette)
   - 2.4 [parse_ade](#24-parse_ade)
   - 2.5 [parse_responsables](#25-parse_responsables)
   - 2.6 [parse_dependances](#26-parse_dependances)
   - 2.7 [parse_moodle](#27-parse_moodle)
   - 2.8 [deduplicate_parallel_groups](#28-deduplicate_parallel_groups)
   - 2.9 [build_parse_report](#29-build_parse_report)
   - 2.10 [load_all_sources](#210-load_all_sources)
3. [Règles d'audit](#3-règles-daudit)
   - 3.1 [base.py — Anomaly, Severity, Dimension](#31-basepy--anomaly-severity-dimension)
   - 3.2 [Complétude (R1.x)](#32-complétude-r1x)
   - 3.3 [Exactitude (R2.x)](#33-exactitude-r2x)
   - 3.4 [Cohérence (R3.x)](#34-cohérence-r3x)
   - 3.5 [Conformité (R4.x)](#35-conformité-r4x)
   - 3.6 [Unicité (R5.x)](#36-unicité-r5x)
   - 3.7 [Traçabilité (R6.x)](#37-traçabilité-r6x)
   - 3.8 [engine.py — Orchestrateur](#38-enginepy--orchestrateur)
4. [Tests unitaires](#4-tests-unitaires)
   - 4.1 [test_parsers.py](#41-test_parserspy)
   - 4.2 [test_rules.py](#42-test_rulespy)

---

## 1. Architecture générale

Le projet est structuré en 3 phases :

```
Phase 1 (P1) : Parsing      → src/parsers/parse_all.py
Phase 2 (P2) : Règles       → src/rules/
Phase 3 (P3) : Dashboard    → (visualisation des anomalies)
```

### Flux de données

```
6 fichiers sources hétérogènes
        │
        ▼
  load_all_sources()
        │
        ▼
  ParsedSources (dataclass)
  ├── maquette       : 37 modules officiels IDU
  ├── seances        : tous les événements ADE (IDU3 + IDU4 + IDU5)
  ├── responsables   : correspondance module → enseignant responsable
  ├── dependances    : contraintes de séquencement (CM avant TD, etc.)
  ├── moodle         : codes modules détectés dans le résumé Moodle
  └── parse_report   : rapport qualité du parsing lui-même
        │
        ▼
  run_all_rules(sources)
        │
        ▼
  audit(sources) → { anomalies, score_par_dim, score_global, raw }
```

### Sources de données

| Fichier | Format | Contenu |
|---|---|---|
| `MAQUETTE_IDU.json` | JSON PHPMyAdmin | 37 modules officiels, heures CM/TD/TP, ECTS |
| `ADECal_IDU3.json` | JSON calendrier ADE | Emploi du temps promo IDU3 |
| `ADECal_IDU4.json` | JSON calendrier ADE | Emploi du temps promo IDU4 |
| `ADECal_IDU5.json` | JSON calendrier ADE | Emploi du temps promo IDU5 |
| `Responsables_modules_IDU.json` | JSON PHPMyAdmin | Enseignants responsables par module |
| `dependance_sequence_IDU.json` | JSON PHPMyAdmin | Règles de séquencement pédagogique |
| `Résumé Moodle IDU.html` | HTML | Page Moodle listant les modules |

---

## 2. Parsers — `parse_all.py`

### 2.1 Constantes et mappings

#### `TYPE_MAP`
Dictionnaire qui normalise les suffixes bruts des titres ADE vers 5 types canoniques.

| Type canonique | Suffixes ADE reconnus |
|---|---|
| `CM` | `CM` |
| `TD` | `TD`, `TDG`, `TDG1`, `TDG2`, `TDTP` |
| `TP` | `TP`, `TPG`, `TPG1`, `TPG2`, `TPTD`, `TPPTD` |
| `EXAM` | `ET`, `CT`, `CC`, `EXAM`, `CMEX`, `CONCOURS` |
| `PROJ` | `PROJ`, `APP`, `TPD`, `AUTO` |

#### `EXAM_KEYWORDS`
Mots-clés détectés dans un titre pour qualifier une séance d'examen :
`2EMESESSION`, `SESSION2`, `TIERSTPS`, `TIER`, `TIERS`, `RATTRAP`, `EXAMEN`, `CONTROLE`

#### `NOISE_PATTERNS`
Liste de patterns regex pour ignorer les événements administratifs non pédagogiques :
BDE, BDS, BDA, Rentrée, En entreprise, Bilan S_, Atelier_APEC, Prévention,
Bienvenue, Asie, Semaine Emploi, [Club, [Evénement, [COM], [RI]

#### `ADE_TO_MAQUETTE`
Mapping manuel de codes ADE non standards vers les codes maquette IDU officiels.
Confirmé par correspondance de contenu ET d'enseignant dans les descriptions ADE.

| Code ADE | Code maquette | Raison |
|---|---|---|
| `INFO641` | `INFO634_IDU` | Conception OO (CIMPAN) → même module |
| `INFO743` | `INFO733_IDU` | Réseaux répartis (SALAMATIAN) → même module |

#### `MODULES_MANQUANTS_MAQUETTE`
Familles de modules IDU **obligatoires** mais **absents** de `MAQUETTE_IDU.json`.
C'est un finding majeur de l'audit : ces modules sont réellement suivis par les étudiants
mais ne sont pas enregistrés dans la maquette officielle.

| Préfixe | Famille |
|---|---|
| `LANG` | Langues vivantes |
| `SHES` | Sciences Humaines et Sociales |
| `MATH` | Mathématiques (modules transverses) |
| `DDRS` | Développement Durable et Responsabilité Sociétale |
| `EASI` | Électronique et systèmes embarqués (filière partagée) |

#### `LV2_CODES`
Codes correspondant à la **LV2 optionnelle** : `LANG602`, `LANG702`, `LANG802`.
Ces cours sont réservés aux étudiants ayant **validé le TOEIC** et ayant choisi
une 2ème langue. Ils sont structurellement absents de la maquette IDU car optionnels
pour un sous-groupe — ce n'est jamais une erreur de saisie ADE.

---

### 2.2 `parse_ade_title`

**Signature** : `parse_ade_title(title: str) → (code, type, is_exam, is_parallel)`

Analyse un titre ADE brut et retourne 4 valeurs :
- `code` : code module extrait (ex: `INFO631`), ou `None` si non reconnu
- `type` : type canonique (`CM`, `TD`, `TP`, `EXAM`, `PROJ`), ou `None`
- `is_exam` : `True` si la séance est un examen/contrôle
- `is_parallel` : `True` si la séance appartient à un groupe parallèle (G1, G2...)

#### Formats de titres gérés

| Format | Exemple | Description |
|---|---|---|
| F1a | `INFO631_INGE_TDG` | CODE + filière + type |
| F1b | `DATA931_CM` | CODE + type (le plus courant) |
| F1c | `ISOC831_Ingénieur_BI` | CODE + libellé libre (type inconnu) |
| F2 | `CM INFO931` | TYPE espace CODE (format inversé) |
| F3 | `PROJ631_IDU_01_4H1` | Projets IDU numérotés |
| F4a | `INFO633_A01_G1` | Ateliers en groupes parallèles → type TD |
| F4b | `INFO633_P01_G2` | Projets en groupes parallèles → type TP |
| F4c | `INFO633_CC1` | Contrôles continus numérotés → type EXAM |

#### Algorithme (ordre de priorité)

1. Vérification bruit → si titre matche un `NOISE_PATTERN` → `(None, None, False, False)`
2. Format F2 (TYPE espace CODE) → détection directe
3. Format F3 (PROJ_IDU_N) → type PROJ
4. Format F4a (atelier _A##_G#) → type TD, `is_parallel=True`
5. Format F4b (projet _P##_G#) → type TP, `is_parallel=True`
6. Format F4c (CC#) → type EXAM, `is_exam=True`
7. Format F1 (CODE_SUFFIX) :
   - Essai 1 : correspondance exacte du suffixe dans `TYPE_MAP`
   - Essai 2 : scan de toutes les parties du titre séparées par `_`, `-`, espace
   - Scan des `EXAM_KEYWORDS`

---

### 2.3 `parse_maquette`

**Entrée** : `MAQUETTE_IDU.json` (format export PHPMyAdmin)
**Sortie** : DataFrame avec colonnes `code_module`, `nom`, `ects`, `cm_h`, `td_h`, `tp_h`, `total_h`

Calcule `total_h = cm_h + td_h + tp_h`. Nettoie les espaces sur `code_module` et `nom`.

---

### 2.4 `parse_ade`

**Entrée** : `ADECal_IDUx.json` + identifiant promo (`"IDU3"`, `"IDU4"`, `"IDU5"`)
**Sortie** : DataFrame avec 17 colonnes par séance

Pour chaque événement ADE :
1. Appelle `parse_ade_title` pour extraire code, type, is_exam, is_parallel
2. Appelle `_parse_location` pour extraire salle et capacité
3. Appelle `_parse_description` pour extraire enseignants et groupes
4. Calcule `duration_h` depuis les timestamps `Starts` / `Ends`
5. Applique `ADE_TO_MAQUETTE` sur `code_prefix` pour obtenir `code_maquette`
6. Calcule `famille_manquante` via `get_famille_manquante`
7. Calcule `lv2_conditionnel` via `is_lv2_optionnel`

#### `_parse_location`
Extrait salle et capacité depuis une chaîne comme `"A-C217 (24pl.)"`.
- Salle : supprime la partie entre parenthèses
- Capacité : extrait le nombre avant `pl.` (ex: `24`)

#### `_parse_description`
Extrait enseignants et groupes depuis le champ Description ADE.

Format typique :
```
IDU-3-G-TD
VERNIER FLAVIEN
(Exporté le:29/04/2026 10:58)
```

- **Bruit** : lignes contenant `Exporté`, `IDU-`, `INGE-`, `FISE`, `N3IE`, numéros de 13 chiffres → ignorées
- **Enseignants** : lignes matchant `NOM_MAJ PRENOM_Maj` (regex strict, majuscules)
- **Groupes** : lignes matchant `IDU-\d[-\w]*`

---

### 2.5 `parse_responsables`

**Entrée** : `Responsables_modules_IDU.json`
**Sortie** : DataFrame avec `code_module`, `nom`, `prenom`, `nom_complet`

Construit `nom_complet = nom.strip() + " " + prenom.strip()`.

---

### 2.6 `parse_dependances`

**Entrée** : `dependance_sequence_IDU.json`
**Sortie** : DataFrame avec `module_prec`, `type_prec`, `num_prec`, `module_suiv`, `type_suiv`, `num_suiv`, `prefix_prec`, `prefix_suiv`

Renomme les colonnes PHPMyAdmin (`module_precedent` → `module_prec`, etc.).
Extrait les préfixes (`INFO631` depuis `INFO631_IDU`) pour la jointure avec les codes ADE.

---

### 2.7 `parse_moodle`

**Entrée** : `Résumé Moodle IDU.html`
**Sortie** : DataFrame avec `code_prefix`, `present_moodle`

Parse le HTML avec BeautifulSoup, extrait tous les codes correspondant au pattern
`(INFO|DATA|ISOC|MATH|PROJ)\d{3,4}` dans le texte brut de la page.

---

### 2.8 `deduplicate_parallel_groups`

**Problème** : Les séances en groupes parallèles (G1, G2) génèrent plusieurs événements
ADE pour la même séance physique → doublement des heures si non dédupliqué.

**Algorithme** :
1. Normalise le titre : supprime le suffixe `_G1` ou `_G2` → `title_base`
2. Sépare séances normales (`is_parallel_grp=False`) et parallèles (`True`)
3. Pour les parallèles : `drop_duplicates(subset=["title_base", "starts_utc"])`
4. Reconcat les deux → si G1 et G2 même horaire, 1 seule séance conservée

**Cas couverts** :
- G1 et G2 **même horaire** → dédupliqués → compte 1 fois ✅
- G1 lundi + G2 mercredi → horaires différents → **non** dédupliqués → compte 2 fois ✅
  (ce sont 2 créneaux réels que 2 groupes différents suivent)

---

### 2.9 `build_parse_report`

Génère un rapport de qualité sur le parsing lui-même (méta-audit).

**Métriques calculées** :
- `total_events` : nombre total d'événements ADE bruts
- `with_code` / `with_code_pct` : taux de reconnaissance des titres (code extrait)
- `with_type` / `with_type_pct` : taux d'extraction du type de séance
- `unrecognized_titles_count` : nombre de titres non reconnus
- `modules_manquants_connus` : codes ADE absents maquette mais familles connues (LANG, SHES...)
- `codes_vraiment_inconnus` : codes ADE sans correspondance ET sans famille connue

---

### 2.10 `load_all_sources`

Point d'entrée principal. Charge et normalise toutes les sources dans l'ordre :

1. Parse la maquette
2. Parse les 3 fichiers ADE (IDU3, IDU4, IDU5), concatène
3. Déduplique les groupes parallèles
4. Post-traitement : efface `famille_manquante` pour les codes présents dans la maquette
5. Parse responsables, dépendances, moodle
6. Génère le parse_report

---

## 3. Règles d'audit

### 3.1 `base.py` — Anomaly, Severity, Dimension

#### `Severity` (enum)
| Valeur | Poids | Signification |
|---|---|---|
| `BLOQUANT` | 5 | Erreur critique, données fiables à 0% |
| `MAJEUR` | 2 | Problème important, nécessite correction |
| `MINEUR` | 0.5 | Avertissement, à vérifier |

#### `Dimension` (enum)
6 dimensions qualité : `COMPLETUDE`, `EXACTITUDE`, `COHERENCE`, `CONFORMITE`, `UNICITE`, `TRACABILITE`

#### `Anomaly` (dataclass)
Champs : `rule_id`, `dimension`, `severity`, `description`, `code_module` (optionnel), `details` (dict optionnel)

Méthode `to_dict()` : sérialise l'anomalie en dictionnaire plat (les `details` sont fusionnés au niveau racine).

---

### 3.2 Complétude (R1.x)

> **Question** : Tous les modules de la maquette sont-ils présents en ADE ?
> La maquette est-elle elle-même complète ?

#### R1.1 — Modules maquette sans séance
- **Condition** : module présent dans la maquette avec `total_h > 0` mais **aucune séance ADE** trouvée
- **Sévérité** : BLOQUANT
- **Détails** : `nom`, `heures_prev`, `ects`
- **Note** : comparaison sur le préfixe extrait de `code_module` (ex: `INFO631` depuis `INFO631_IDU`)

#### R1.2 — Maquette incomplète
- **Condition** : séances ADE avec `famille_manquante` non nulle (LANG, SHES, MATH, DDRS, EASI)
- **Sévérité** : MAJEUR
- **Exception** : si `lv2_conditionnel=True` → **ignoré complètement** (LV2 = choix étudiant après TOEIC, pas une erreur)
- **Détails** : `famille`, `nb_seances_ade`, `heures_ade`, `lv2_optionnel`

#### R1.3 — Modules sans responsable
- **Condition** : module présent dans la maquette mais **absent** de la table responsables
- **Sévérité** : MAJEUR (gouvernance pédagogique)
- **Détails** : `nom`

#### R1.4 — Responsables familles manquantes
- **Condition** : aucun responsable défini pour une famille obligatoire (LANG, SHES, MATH, EASI, DDRS)
- **Sévérité** : MAJEUR
- **Détails** : `famille`, `prefix`

---

### 3.3 Exactitude (R2.x)

> **Question** : Les volumes horaires ADE correspondent-ils à la maquette ?

#### Fonction utilitaire : `calcul_heures_ade_par_module`
Agrège les heures ADE par `(préfixe module, type séance)`.

**Filtres appliqués avant le calcul** :
- Exclut séances sans `code_maquette`
- Exclut séances sans `type_seance`
- Exclut séances avec `famille_manquante` non nulle (hors maquette)
- Exclut séances `is_exam=True` (examens ne comptent pas dans les heures cours)

**Déduplication parallèles** :
- Sépare séances normales et parallèles
- Pour les parallèles : `drop_duplicates(subset=["code_prefix", "type_seance", "starts_utc"])`
- Résultat : G1 et G2 au même horaire = 1 seule occurrence dans le calcul

#### R2.1 — Écart heures prévu vs ADE
- **Seuil** : 15% de tolérance
- **Condition** (type prévu, 0h ADE) : `heure_prev > 0` ET `heures_ADE == 0` → BLOQUANT
- **Condition** (écart 25%-50%) : MAJEUR
- **Condition** (écart > 50%) : BLOQUANT
- **Condition** (écart 15%-25%) : MINEUR
- Appliqué pour chaque type (CM, TD, TP) séparément

#### R2.2 — Séance non prévue
- **Condition** : `heures_prev == 0` ET `heures_ADE > 0`
- **Sévérité** : MAJEUR
- **Détails** : `type`, `heures_prev`, `heures_ade`

#### R2.3 — Durées aberrantes
- **Condition** : `duration_h == 0` OU `duration_h > 8`
- **Sévérité** : MINEUR
- **Détails** : `title`, `duration_h`, `starts_utc`, `salle`

#### R2.4 — TP de durée courte *(nouvelle règle)*
- **Condition** : `type_seance == "TP"` ET `duration_h < 4.0`
- **Sévérité** : MINEUR
- **Exclut** : séances `is_exam=True` et `is_parallel_grp=True`
- **Interprétation** : un TP dure normalement 4h. En dessous, probable mauvais tag (CM ou TD saisi en TP)
- **Détails** : `duration_h`, `title`

#### R2.5 — Séance sans enseignant *(nouvelle règle, asymétrique)*
| Type | Enseignants vide | Sévérité | Raison |
|---|---|---|---|
| CM | `[]` ou `""` | BLOQUANT | Un CM sans prof = erreur de saisie |
| TP | `[]` ou `""` | MINEUR | Auto-formation possible mais à vérifier |
| TD | `[]` ou `""` | **Ignoré** | Séance d'auto-formation = normal |
| EXAM | `[]` ou `""` | **Ignoré** | Surveillant non saisi = normal |

---

### 3.4 Cohérence (R3.x)

> **Question** : Les codes modules sont-ils uniformes entre toutes les sources ?

#### R3.1 — Codes ADE non normalisés
- **Condition** : séance avec `code_prefix` présent dans `ADE_TO_MAQUETTE`
- **Sévérité** : MINEUR (mapping géré, mais à signaler)
- **Détails** : `code_ade`, `code_maquette`, `nb_seances`

#### R3.2 — Doublons responsables
- **Condition** : `code_module` avec plusieurs entrées dans la table responsables
- **Sévérité** : MAJEUR (gouvernance ambigüe)
- **Détails** : `nb_responsables`, `responsables` (liste)

#### R3.3 — Titres ADE non parsables
- **Condition** : titre ADE avec `code_prefix=None` (non reconnu), dédoublonné par titre
- **Sévérité** : MINEUR
- **Limite** : top 20 pour éviter le bruit
- **Détails** : `title`, `occurrences`

#### R3.4 — Possible mauvais tag TD/TP *(nouvelle règle)*
- **Objectif** : détecter quand des TP ont été saisis en TD dans ADE
- **Conditions** (les 3 doivent être vraies) :
  1. `tp_h_maquette > 0` (des TP sont prévus)
  2. `heures_tp_ade == 0` (aucune séance TP dans ADE)
  3. `excedent_td = heures_td_ade - td_h_maquette > 0` ET `abs(excedent_td - tp_h_maquette) <= 2.0`
     (l'excédent de TD ≈ le manque de TP, tolérance 2h)
- **Sévérité** : MINEUR
- **Exemple** : maquette `tdh=10h tph=20h`, ADE `TD=30h TP=0h` → excédent TD = 20h ≈ manque TP = 20h → R3.4
- **Détails** : `excedent_td`, `manque_tp`, `code_module`

---

### 3.5 Conformité (R4.x)

> **Question** : Les séquences pédagogiques (CM avant TD, etc.) sont-elles respectées ?

#### R4.1 — Violations de séquencement
- **Condition** : une séance "suivante" planifiée **AVANT** sa séance "précédente" dans ADE
- **Exemple** : TD planifié avant le CM qui le précède selon les dépendances
- **Sévérité** : BLOQUANT
- **Détails** : `module_prec`, `type_prec`, `num_prec`, `starts_prec`, `module_suiv`, `type_suiv`, `num_suiv`, `starts_suiv`
- **Note** : si une séance de la paire est introuvable dans ADE → pas d'anomalie R4.1 (R4.2 prend le relais)

#### R4.2 — Dépendances orphelines
- **Condition** : contrainte de dépendance dont **au moins une** des séances (prec ou suiv) est introuvable dans ADE
- **Sévérité** : MINEUR (incohérence référentielle, pas un blocage pédagogique)
- **Détails** : `prec_trouve` (bool), `suiv_trouve` (bool), `key_prec`, `key_suiv`

---

### 3.6 Unicité (R5.x)

> **Question** : Y a-t-il des conflits de ressources (enseignants, salles) ?

#### R5.1 — Enseignant en double créneau
- **Condition** : même enseignant assigné à 2 séances qui se chevauchent temporellement
- **Sévérité** : BLOQUANT
- **Détails** : `enseignant`, description mentionne le nom

#### R5.2 — Capacité salle insuffisante
- **Condition** : `type_seance ∈ {CM, TD}` ET `capacite < seuil` (valeur définie dans le code)
- **Sévérité** : MINEUR
- **Exclut** : séances TP (petites salles = normal pour groupes restreints) et `capacite=NaN`
- **Détails** : `capacite`, `salle`

---

### 3.7 Traçabilité (R6.x)

> **Question** : Les modules ADE sont-ils tous référencés dans Moodle et vice-versa ?

#### R6.1 — Module maquette absent de Moodle
- **Condition** : module dans la maquette mais **non détecté** dans le HTML Moodle
- **Sévérité** : MINEUR

#### R6.2 — Code Moodle inconnu en maquette
- **Condition** : code détecté dans Moodle mais **absent** de la maquette officielle
- **Sévérité** : MAJEUR
- **Détails** : `code_module`

---

### 3.8 `engine.py` — Orchestrateur

#### `run_all_rules(sources)`
Exécute les 6 modules de règles dans l'ordre et retourne une liste plate d'anomalies :
`completude → exactitude → coherence → conformite → unicite → tracabilite`

#### `anomalies_to_dataframe(anomalies)`
Convertit la liste d'anomalies en DataFrame pandas. Les `details` de chaque anomalie
sont fusionnés comme colonnes supplémentaires.

#### `compute_quality_score(anomalies)`
Calcule un score 0-100 par dimension.

Formule : `score = max(0, 100 - pénalité)`
Où `pénalité = nb_bloquant × 5 + nb_majeur × 2 + nb_mineur × 0.5`

Le score est plafonné à 0 (ne peut pas être négatif).

#### `compute_global_score(score_df)`
Moyenne arithmétique des scores par dimension.

#### `audit(sources)`
Point d'entrée principal de l'audit. Retourne un dictionnaire :
```python
{
    "anomalies":    pd.DataFrame,   # toutes les anomalies
    "score_par_dim": pd.DataFrame,  # score par dimension
    "score_global": float,          # score global 0-100
    "raw":          list[Anomaly],  # liste brute pour traitement avancé
}
```

---

## 4. Tests unitaires

### Convention générale

Tous les tests utilisent deux helpers communs :

**`_make_minimal_sources(**kwargs)`** : construit un `ParsedSources` avec des DataFrames minimaux.
Par défaut, la maquette contient 1 module (`INFO631_IDU`, 10.5h CM, 10.5h TD, 20h TP)
et les séances sont vides.

**`_seance(**overrides)`** : construit un dictionnaire séance avec des valeurs par défaut
(INFO631_CM, 2h, salle A101, enseignant VERNIER FLAVIEN) que l'on peut surcharger via kwargs.

---

### 4.1 `test_parsers.py`

#### `TestParseAdeTitle` — Tests de `parse_ade_title`

| Test | Titre ADE | Ce qui est vérifié |
|---|---|---|
| `test_format_code_type_simple` | `DATA931_CM` | code=DATA931, typ=CM, is_exam=False, is_par=False |
| `test_format_code_tdg` | `INFO631_INGE_TDG` | code=INFO631, typ=TD |
| `test_format_type_code_avec_espace` | `CM INFO931` | code=INFO931, typ=CM (format inversé F2) |
| `test_format_proj_idu` | `PROJ631_IDU_01_4H1` | code=PROJ631, typ=PROJ (format F3) |
| `test_format_atelier_groupe_parallele` | `INFO633_A01_G1` | code=INFO633, typ=TD, is_par=True |
| `test_format_projet_groupe_parallele` | `INFO633_P01_G2` | code=INFO633, typ=TP, is_par=True |
| `test_format_controle_continu` | `INFO634_CC1` | code=INFO634, typ=EXAM, is_exam=True |
| `test_bruit_bde_ignore` | `BDE Soirée étudiants` | code=None, typ=None (bruit ignoré) |
| `test_bruit_rentree_ignore` | `Rentrée IDU 2024` | code=None (bruit ignoré) |
| `test_exam_keyword_rattrap` | `INFO632_RATTRAP` | code=INFO632, is_exam=True (mot-clé exam) |
| `test_titre_inconnu_retourne_none` | `Séminaire professionnel` | code=None |
| `test_tp_type` | `INFO632_TP` | code=INFO632, typ=TP |
| `test_exam_et` | `INFO731ET` | typ=EXAM, is_exam=True (suffixe ET) |
| `test_td_space_format` | `TD INFO734` | code=INFO734, typ=TD |

#### `TestParseLocation` — Tests de `parse_location`

| Test | Entrée | Ce qui est vérifié |
|---|---|---|
| `test_salle_avec_capacite` | `A-C217 (24pl.)` | salle=A-C217, cap=24 |
| `test_salle_sans_capacite` | `Amphi A` | salle=Amphi A, cap=None |
| `test_location_vide` | `""` | salle="", cap=None |
| `test_capacite_grande_salle` | `Amphi Jules Verne (200pl.)` | cap=200 |

#### `TestModulesManquants` — Tests de `get_famille_manquante`

| Test | Code | Résultat attendu |
|---|---|---|
| `test_lang_reconnu_comme_manquant` | `LANG500` | `"Langues vivantes"` |
| `test_easi_reconnu_comme_manquant` | `EASI501` | contient `"Électronique"` |
| `test_info_present_dans_maquette` | `INFO631` | `None` (présent en maquette) |
| `test_none_code` | `None` | `None` |
| `test_math_reconnu_comme_manquant` | `MATH501` | contient `"Mathématiques"` |
| `test_ddrs_reconnu_comme_manquant` | `DDRS501` | contient `"Développement Durable"` |

#### `TestLv2Conditionnel` — Tests de `is_lv2_optionnel`

| Test | Ce qui est vérifié |
|---|---|
| `test_lv2_codes_detectes` | LANG602, LANG702, LANG802 → True |
| `test_lv1_pas_lv2` | LANG501, LANG601, LANG801 → False |
| `test_non_lang_pas_lv2` | INFO631 → False |
| `test_none_pas_lv2` | None → False |
| `test_lv2_codes_constante_complete` | Les 3 codes sont bien dans LV2_CODES |

#### `TestDeduplicateParallelGroups`

| Test | Ce qui est vérifié |
|---|---|
| `test_un_doublon_supprime` | G1 + G2 même horaire → 2 séances deviennent 1 (+ 1 normale = 2 total) |
| `test_seances_normales_conservees` | Séance non parallèle toujours présente après dédup |
| `test_pas_de_parallele_inchange` | DataFrame sans parallèles → non modifié |

#### `TestBuildParseReport`

| Test | Ce qui est vérifié |
|---|---|
| `test_taux_code_correct` | 1 séance avec code + 1 inconnue → `with_code_pct = 50.0%` |
| `test_dataframe_vide_ne_crash_pas` | DataFrame vide → `total_events=0`, `with_code_pct=0.0` |
| `test_codes_vraiment_inconnus` | `XXXX999` → dans `codes_vraiment_inconnus`, PAS dans `modules_manquants_connus` |
| `test_modules_manquants_connus_separes` | LANG500 et SHES501 → dans `modules_manquants_connus`, pas dans inconnus |

#### `TestConstants`

| Test | Ce qui est vérifié |
|---|---|
| `test_typemap_valeurs_valides` | Toutes les valeurs de TYPE_MAP ∈ {CM, TD, TP, EXAM, PROJ} |
| `test_adetomaquette_format` | Clés ADE matchent `[A-Z]+\d+`, valeurs contiennent `IDU` ou `PACY` |

#### `TestParseDescription`

| Test | Ce qui est vérifié |
|---|---|
| `test_enseignant_simple_extrait` | `VERNIER FLAVIEN` extrait correctement |
| `test_enseignant_compose_extrait` | `DE LA TORRE JEAN-LUC` extrait (prénom composé) |
| `test_lignes_bruit_ignorees` | Lignes `Export le:...` et numéros 13 chiffres ignorés |
| `test_idu_line_filtree_comme_bruit` | Lignes `IDU-3-G2-TP` ignorées (bruit) |
| `test_description_vide` | `""` → enseignants=[], groupes=[] |
| `test_minuscules_pas_enseignant` | Pattern exige MAJ → minuscules ignorées |

---

### 4.2 `test_rules.py`

#### `TestAnomaly`

| Test | Ce qui est vérifié |
|---|---|
| `test_creation_basique` | `rule_id`, `dimension` correctement assignés |
| `test_to_dict` | Sérialisation correcte + `details` fusionnés au niveau racine |

#### `TestCompletude`

| Test | Ce qui est vérifié |
|---|---|
| `test_module_sans_seance_detecte` | Maquette avec module, séances vides → 1 anomalie R1.1 BLOQUANT |
| `test_module_avec_seance_pas_detecte` | Séance INFO631_CM présente → 0 anomalie |
| `test_lv2_ignore_completement` | LANG602 avec `lv2_conditionnel=True` → 0 anomalie (ignoré entièrement) |
| `test_module_manquant_shes_detecte_majeur` | SHES501 hors maquette, non-LV2 → MAJEUR |
| `test_module_sans_responsable_detecte` | INFO631_IDU sans responsable → 1 anomalie |
| `test_responsables_familles_manquantes_toutes_detectees` | 5 familles (LANG, SHES, MATH, EASI, DDRS) → 5 anomalies |

#### `TestExactitude`

| Test | Ce qui est vérifié |
|---|---|
| `test_duree_aberrante_nulle` | Séance 0h → R2.3 MINEUR |
| `test_duree_aberrante_trop_longue` | Séance 10h → R2.3 MINEUR |

#### `TestExactitudeEcartHeures`

| Test | Ce qui est vérifié |
|---|---|
| `test_type_prevu_sans_seance_bloquant` | CM prévu, 0 séance ADE → R2.1 BLOQUANT × 2 (CM + TP) |
| `test_seance_non_prevue_majeur` | TP en ADE, 0h TP prévu → R2.2 MAJEUR |
| `test_ecart_dans_seuil_aucune_anomalie` | Écart < 15% → 0 anomalie |
| `test_ecart_majeur_seuil_25` | CM +38% → R2.1 MAJEUR |
| `test_ecart_bloquant_seuil_50` | CM +90% → R2.1 BLOQUANT |
| `test_examens_exclus_du_calcul` | Séance `is_exam=True` exclue → CM compte 0h → BLOQUANT |

#### `TestExactitudeParalleleDedup`

| Test | Ce qui est vérifié |
|---|---|
| `test_heures_groupes_paralleles_meme_horaire_non_dupliquees` | G1+G2 même heure, 4h prévu → dédup → 0 anomalie |
| `test_heures_groupes_paralleles_horaires_differents_comptes_deux_fois` | G1 lundi + G2 mercredi, 8h prévu → 2 créneaux distincts → 0 anomalie |

#### `TestExactitudeR24TpDureeCourte`

| Test | Ce qui est vérifié |
|---|---|
| `test_tp_moins_4h_mineur` | TP 2h → R2.4 MINEUR, `details.duration_h == 2.0` |
| `test_tp_exactement_4h_ok` | TP 4h → 0 anomalie |
| `test_cm_moins_4h_ok` | CM 1h30 → 0 anomalie (règle ne s'applique qu'aux TP) |

#### `TestExactitudeR25SansEnseignant`

| Test | Ce qui est vérifié |
|---|---|
| `test_cm_sans_enseignant_bloquant` | CM, enseignants=[] → R2.5 BLOQUANT |
| `test_td_sans_enseignant_ignore` | TD, enseignants=[] → 0 anomalie (auto-formation) |
| `test_tp_sans_enseignant_mineur` | TP, enseignants=[] → R2.5 MINEUR |
| `test_cm_avec_enseignant_ok` | CM, enseignants=["DUPONT"] → 0 anomalie |

#### `TestCoherence`

| Test | Ce qui est vérifié |
|---|---|
| `test_doublons_responsables_detectes` | 2 responsables pour INFO631_IDU → R3.2, `nb_responsables=2` |

#### `TestCoherenceCodesAde`

| Test | Ce qui est vérifié |
|---|---|
| `test_code_ade_mappe_detecte` | Code dans ADE_TO_MAQUETTE → R3.1 MINEUR |
| `test_pas_de_seance_pas_anomalie` | Séances vides → 0 anomalie |

#### `TestCoherenceTitresInconsistants`

| Test | Ce qui est vérifié |
|---|---|
| `test_titre_non_parsable_detecte` | "Réunion BDE" × 2 → R3.3 MINEUR, `occurrences=2` |
| `test_seance_avec_code_pas_concernee` | Séance normale avec code → 0 anomalie |

#### `TestCoherenceR34MauvaisTagTdTp`

| Test | Ce qui est vérifié |
|---|---|
| `test_exces_td_correspond_manque_tp_detecte` | tdh_maq=10, tph_maq=20, ADE TD=30 TP=0 → R3.4 MINEUR |
| `test_exces_td_sans_manque_tp_ignore` | TP présents en ADE → règle ne déclenche pas |
| `test_ecart_trop_grand_ignore` | excédent_td=4, manque_tp=20 → abs(4-20)=16 > 2 → 0 anomalie |

#### `TestConformiteSequencement`

| Test | Ce qui est vérifié |
|---|---|
| `test_td_avant_cm_detecte_bloquant` | TD planifié avant CM (contrainte CM→TD) → R4.1 BLOQUANT |
| `test_ordre_correct_pas_anomalie` | CM avant TD → 0 anomalie |
| `test_seance_introuvable_ignore` | Séance manquante → 0 anomalie R4.1 (R4.2 prend le relais) |

#### `TestConformiteDependancesOrphelines`

| Test | Ce qui est vérifié |
|---|---|
| `test_dependance_sans_seances_detectee` | Contrainte définie, séances absentes → R4.2 MINEUR, `prec_trouve=False` |
| `test_dependance_avec_seances_pas_orpheline` | Les 2 séances présentes → 0 anomalie |

#### `TestUniciteCapaciteSalle`

| Test | Ce qui est vérifié |
|---|---|
| `test_cm_petite_salle_detecte` | CM, capacité=8 → R5.2 MINEUR |
| `test_td_petite_salle_detecte` | TD, capacité=10 → R5.2 MINEUR |
| `test_tp_ignore` | TP petite salle → 0 anomalie (normal pour groupes restreints) |
| `test_grande_salle_ignore` | CM, capacité=30 → 0 anomalie |
| `test_capacite_nan_ignore` | CM, capacité=NaN → 0 anomalie |

#### `TestUnicite`

| Test | Ce qui est vérifié |
|---|---|
| `test_enseignant_double_creneau_detecte` | SALAMATIAN sur 2 séances simultanées → R5.1 BLOQUANT |

#### `TestTracabilite`

| Test | Ce qui est vérifié |
|---|---|
| `test_module_maquette_absent_moodle` | INFO631 absent du Moodle mock → anomalie R6.1 |
| `test_code_moodle_absent_maquette` | PROJ901 dans Moodle, absent maquette → R6.2 MAJEUR |

#### `TestEngine`

| Test | Ce qui est vérifié |
|---|---|
| `test_run_all_rules_retourne_liste` | `run_all_rules` retourne bien une liste |
| `test_anomalies_to_dataframe_vide` | Liste vide → DataFrame vide avec colonnes |
| `test_anomalies_to_dataframe_avec_anomalies` | 2 anomalies → 2 lignes, rule_id correct |
| `test_compute_quality_score_six_dimensions` | 6 lignes (une par dimension), score=100 sans anomalie |
| `test_compute_quality_score_avec_bloquant` | 1 BLOQUANT Complétude → score=95 (100-5) |
| `test_compute_global_score` | Moyenne 80+100 = 90.0 |
| `test_audit_retourne_structure_complete` | Dict avec clés `anomalies`, `score_par_dim`, `score_global`, `raw` |

#### `TestAuditIntegration`

| Test | Ce qui est vérifié |
|---|---|
| `test_audit_complet_avec_anomalies_multiples` | Sources avec durée aberrante + conflit enseignant → score < 100, BLOQUANT présent, dimension UNICITE touchée |
| `test_score_dimension_jamais_negatif` | 50 anomalies BLOQUANT → score Complétude ≥ 0 (pas négatif) |
| `test_to_dataframe_colonnes_completes` | `details` fusionnés comme colonnes dans le DataFrame |

---

*Documentation générée le 30/04/2026 — Projet Hackathon IDU Polytech Annecy*
"""

import os
os.makedirs("output", exist_ok=True)
with open("output/DOCUMENTATION_TECHNIQUE.md", "w", encoding="utf-8") as f:
    f.write(doc)

print(f"Fichier généré : {len(doc)} caractères, {doc.count(chr(10))} lignes")