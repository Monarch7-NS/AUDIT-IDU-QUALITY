"""
src/parsers/parse_all.py
========================
Parser principal — Hackathon IDU Qualité de la donnée
Transforme les 6 sources hétérogènes en DataFrames pandas unifiés.

Usage:
    from src.parsers.parse_all import load_all_sources
    sources = load_all_sources()
    print(sources.maquette)
    print(sources.seances)
    print(sources.responsables)
    print(sources.dependances)
    print(sources.parse_report)
"""

import json
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# MODÈLE DE DONNÉES UNIFIÉ
# ─────────────────────────────────────────────────────────────

@dataclass
class ParsedSources:
    """
    Contient tous les DataFrames normalisés issus des 6 sources.
    C'est l'objet central que P2 (règles) et P3 (dashboard) utilisent.
    """
    maquette:     pd.DataFrame   # 37 modules officiels
    seances:      pd.DataFrame   # tous les événements ADE parsés (dédupliqués)
    responsables: pd.DataFrame   # correspondance module → enseignant
    dependances:  pd.DataFrame   # contraintes de séquencement (DAG)
    moodle:       pd.DataFrame   # codes modules détectés dans Moodle
    parse_report: pd.DataFrame   # rapport sur la qualité du parsing lui-même


# ─────────────────────────────────────────────────────────────
# CONSTANTES : MAPPING DES TYPES DE SÉANCES
# ─────────────────────────────────────────────────────────────

TYPE_MAP: dict[str, str] = {
    "CM": "CM", "CMEX": "EXAM",
    "TD": "TD", "TDG": "TD", "TDG1": "TD", "TDG2": "TD",
    "TP": "TP", "TPG": "TP", "TPG1": "TP", "TPG2": "TP",
    "TPTD": "TP", "TPPTD": "TP", "TDTP": "TD",
    "ET": "EXAM", "CT": "EXAM", "EXAM": "EXAM", "CC": "EXAM", "CONCOURS": "EXAM",
    "PROJ": "PROJ", "APP": "PROJ", "TPD": "PROJ", "AUTO": "PROJ",
}

EXAM_KEYWORDS = frozenset([
    "2EMESESSION", "SESSION2", "TIERSTPS", "TIER", "TIERS",
    "RATTRAP", "EXAMEN", "CONTROLE",
])

# Événements administratifs sans contenu pédagogique IDU — à ignorer
NOISE_PATTERNS = [
    re.compile(r"^(BDE|BDS|BDA)\b", re.IGNORECASE),
    re.compile(r"^Rentr[eé]e\b", re.IGNORECASE),
    re.compile(r"^(En entreprise|Bilan S\d|Atelier_APEC)\b", re.IGNORECASE),
    re.compile(r"^(Pr[eé]vention|Bienvenue|Asie|Semaine Emploi)\b", re.IGNORECASE),
    re.compile(r"^\[Club\b", re.IGNORECASE),
    re.compile(r"^\[Evénement\b", re.IGNORECASE),
    re.compile(r"^\[COM\]\b", re.IGNORECASE),
    re.compile(r"^\[RI\]\b", re.IGNORECASE),
]

# Mapping manuel : codes ADE non standards → codes maquette IDU
# Confirmé par correspondance de contenu ET enseignant dans les descriptions ADE
ADE_TO_MAQUETTE: dict[str, str] = {
    "INFO641": "INFO634_IDU",   # Conception OO (CIMPAN) → même module
    "INFO743": "INFO733_IDU",   # Réseaux répartis (SALAMATIAN) → même module
}

# Familles de modules IDU OBLIGATOIRES mais ABSENTS de MAQUETTE_IDU.json.
# Confirmé par l'équipe pédagogique : ces modules sont réellement suivis par les
# étudiants IDU mais ne sont pas enregistrés dans la maquette officielle.
# → C'est une ANOMALIE de complétude de la maquette (finding majeur de l'audit).
MODULES_MANQUANTS_MAQUETTE: dict[str, str] = {
    "LANG": "Langues vivantes",
    "SHES": "Sciences Humaines et Sociales",
    "MATH": "Mathématiques (modules transverses)",
    "DDRS": "Développement Durable et Responsabilité Sociétale",
    "EASI": "Électronique et systèmes embarqués (filière partagée)",
}

# Codes LANG correspondant à la LV2 (optionnelle, pour étudiants ayant validé le TOEIC).
# Les autres codes LANG sont obligatoires (LV1 = anglais).
LV2_CODES = frozenset(["LANG602", "LANG702", "LANG802"])

RE_CODE       = re.compile(r"^([A-Z]{2,6}\d{3,4})")
RE_FMT2       = re.compile(r"^(CM|TD|TP|EXAM|PROJ)\s+([A-Z]{2,6}\d{3,4})\b", re.IGNORECASE)
RE_PROJ_IDU   = re.compile(r"^(PROJ\d{3,4})_IDU_\d+")
RE_ATELIER    = re.compile(r"^([A-Z]{2,6}\d{3,4})_A\d{2}_G\d")
RE_PROJET_GRP = re.compile(r"^([A-Z]{2,6}\d{3,4})_P\d{2}_G\d")
RE_CC         = re.compile(r"^([A-Z]{2,6}\d{3,4})_CC\d")


# ─────────────────────────────────────────────────────────────
# PARSEUR DE TITRE ADE
# ─────────────────────────────────────────────────────────────

def get_famille_manquante(code: Optional[str]) -> Optional[str]:
    """
    Retourne la famille si le module appartient à une famille obligatoire IDU
    absente de la maquette officielle (LANG, SHES, MATH, EASI, DDRS).
    Retourne None si le module est présent dans la maquette ou si code invalide.
    """
    if not code:
        return None
    for prefix, famille in MODULES_MANQUANTS_MAQUETTE.items():
        if code.startswith(prefix):
            return famille
    return None


def is_lv2_optionnel(code: Optional[str]) -> bool:
    """Indique si le code correspond à un module LV2 (langue optionnelle)."""
    return code in LV2_CODES if code else False


def parse_ade_title(title: str) -> tuple[Optional[str], Optional[str], bool, bool]:
    """
    Analyse un titre ADE et retourne (code_module, type_seance, is_exam, is_parallel_group).

    Gère les formats de titres rencontrés dans les données IDU :
      F1a : CODE_INGE_TYPE  → INFO631_INGE_TDG
      F1b : CODE_TYPE       → DATA931_CM
      F1c : CODE_libre      → ISOC831_Ingénieur_BI (type inconnu)
      F2  : TYPE CODE       → CM INFO931
      F3  : CODE_IDU_N      → PROJ631_IDU_01_4H1
      F4  : Ateliers/CC     → INFO633_A01_G1, INFO633_CC1
    """
    is_parallel = False
    is_exam = False

    for noise_pat in NOISE_PATTERNS:
        if noise_pat.search(title):
            return None, None, False, False

    # Format F2 : "TYPE CODE" avec espace
    m2 = RE_FMT2.match(title)
    if m2:
        typ_raw = m2.group(1).upper()
        code = m2.group(2).upper()
        typ = TYPE_MAP.get(typ_raw, typ_raw)
        is_exam = typ == "EXAM"
        return code, typ, is_exam, False

    # Format F3 : PROJ631_IDU_01_4H1
    mp = RE_PROJ_IDU.match(title)
    if mp:
        return mp.group(1).upper(), "PROJ", False, False

    # Format F4a : INFO633_A01_G1 (ateliers → TD en groupe parallèle)
    ma = RE_ATELIER.match(title)
    if ma:
        return ma.group(1).upper(), "TD", False, True

    # Format F4b : INFO633_P01_G1 (projets → TP en groupe parallèle)
    mpg = RE_PROJET_GRP.match(title)
    if mpg:
        return mpg.group(1).upper(), "TP", False, True

    # Format F4c : INFO633_CC1 (contrôles continus)
    mcc = RE_CC.match(title)
    if mcc:
        return mcc.group(1).upper(), "EXAM", True, False

    # Format F1a/F1b/F1c : CODE_SUFFIX
    m1 = RE_CODE.match(title)
    if not m1:
        return None, None, False, False

    code = m1.group(1).upper()
    rest = title[len(code):].lstrip("_").upper()

    if re.search(r"_G[12]$", title, re.IGNORECASE):
        is_parallel = True

    detected_type = None

    # Essai 1 : correspondance exacte au début du reste
    for kw in sorted(TYPE_MAP, key=len, reverse=True):
        if rest.startswith(kw):
            next_char = rest[len(kw):len(kw)+1]
            if not next_char or next_char in "_-123456789 ":
                detected_type = TYPE_MAP[kw]
                is_exam = detected_type == "EXAM"
                break

    # Essai 2 : scan de toutes les parties du titre
    if not detected_type:
        parts = re.split(r"[_\-\s]", title.upper())
        for part in parts[1:]:
            clean = re.sub(r"\d+", "", part)
            if clean in TYPE_MAP:
                detected_type = TYPE_MAP[clean]
                is_exam = detected_type == "EXAM"
                break
            if clean in EXAM_KEYWORDS:
                detected_type = "EXAM"
                is_exam = True
                break

    return code, detected_type, is_exam, is_parallel


# ─────────────────────────────────────────────────────────────
# PARSEUR MAQUETTE
# ─────────────────────────────────────────────────────────────

def parse_maquette(path: Path) -> pd.DataFrame:
    """
    Charge MAQUETTE_IDU.json (export PHPMyAdmin).
    Colonnes : code_module, nom, ects, cm_h, td_h, tp_h, total_h
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    table_entry = next(e for e in raw if e.get("type") == "table")
    df = pd.DataFrame(table_entry["data"])

    for col in ["cm", "td", "tp", "ects"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df.rename(columns={"cm": "cm_h", "td": "td_h", "tp": "tp_h"})
    df["total_h"] = df["cm_h"] + df["td_h"] + df["tp_h"]
    df["nom"] = df["nom"].str.strip()
    df["code_module"] = df["code_module"].str.strip()

    logger.info(f"Maquette : {len(df)} modules chargés")
    return df[["code_module", "nom", "ects", "cm_h", "td_h", "tp_h", "total_h"]]


# ─────────────────────────────────────────────────────────────
# PARSEUR ADE
# ─────────────────────────────────────────────────────────────

def parse_ade(path: Path, promo: str) -> pd.DataFrame:
    """
    Charge un fichier ADECal_IDUx.json.
    Colonnes : title_original, code_prefix, code_maquette, type_seance,
               is_exam, is_parallel_grp, hors_maquette,
               starts_utc, ends_utc, duration_h,
               location, salle, capacite, enseignants, groupes, promo
    """
    with open(path, encoding="utf-8") as f:
        events = json.load(f)

    rows = []
    for e in events:
        title = e.get("Title", "").strip()
        code, typ, is_exam, is_parallel = parse_ade_title(title)

        location = e.get("Location", "").strip()
        salle, capacite = _parse_location(location)

        desc = e.get("Description", "")
        enseignants, groupes = _parse_description(desc)

        try:
            starts = pd.to_datetime(e["Starts"], utc=True)
            ends   = pd.to_datetime(e["Ends"],   utc=True)
            duration_h = (ends - starts).total_seconds() / 3600
        except Exception:
            starts = ends = pd.NaT
            duration_h = 0.0

        rows.append({
            "title_original":     title,
            "code_prefix":        code,
            "code_maquette":      ADE_TO_MAQUETTE.get(code, code) if code else None,
            "type_seance":        typ,
            "is_exam":            is_exam,
            "is_parallel_grp":    is_parallel,
            "famille_manquante":  get_famille_manquante(code),
            "lv2_conditionnel":   is_lv2_optionnel(code),
            "starts_utc":         starts,
            "ends_utc":           ends,
            "duration_h":         duration_h,
            "location":           location,
            "salle":              salle,
            "capacite":           capacite,
            "enseignants":        enseignants,
            "groupes":            groupes,
            "promo":              promo,
        })

    df = pd.DataFrame(rows)
    pct = df["code_prefix"].notna().sum() / len(df) * 100 if len(df) > 0 else 0
    logger.info(
        f"ADE {promo} : {len(df)} événements — "
        f"{df['code_prefix'].notna().sum()} avec code reconnu ({pct:.0f}%)"
    )
    return df


def _parse_location(location: str) -> tuple[str, Optional[int]]:
    """Extrait salle et capacité depuis 'A-C217 (24pl.)' → ('A-C217', 24)."""
    if not location:
        return "", None
    cap_match = re.search(r"\((\d+)\s*pl", location)
    capacite = int(cap_match.group(1)) if cap_match else None
    salle = re.sub(r"\s*\(.*?\)", "", location).strip()
    return salle, capacite


def _parse_description(desc: str) -> tuple[list[str], list[str]]:
    """
    Extrait enseignants et groupes depuis le champ Description ADE.

    Format typique :
        IDU-3-G-TD
        VERNIER FLAVIEN
        (Exporté le:29/04/2026 10:58)
    """
    lines = [l.strip() for l in desc.strip().split("\n") if l.strip()]

    # NOM_MAJ PRENOM_Maj — accepte prénoms composés (JEAN-LUC, etc.)
    pat_teacher = re.compile(
        r"^[A-ZÀÂÉÈÊËÎÏÔÙÛÜ][A-ZÀÂÉÈÊËÎÏÔÙÛÜ\-]{1,}"
        r"(?:\s+[A-ZÀÂÉÈÊËÎÏÔÙÛÜ][A-ZÀÂÉÈÊËÎÏÔÙÛÜ\-]+)?"
        r"\s+"
        r"[A-ZÀÂÉÈÊËÎÏÔÙÛÜ][A-Za-zàâéèêëîïôùûü\-]+"
    )
    noise_line = re.compile(
        r"(Exporté|Export[eé]|IDU-|INGE-|FISE|FISA|SNI-|EPU-|MECA-|"
        r"Scolarité|N[34]IE|NTRANS|N\dIE|^\d{13})"
    )
    pat_group = re.compile(r"IDU-\d[-\w]*", re.IGNORECASE)

    enseignants: list[str] = []
    groupes: list[str] = []

    for line in lines:
        if noise_line.search(line):
            continue
        if pat_group.search(line):
            groupes.append(line)
        elif pat_teacher.match(line):
            enseignants.append(line.upper())

    return enseignants, groupes


# ─────────────────────────────────────────────────────────────
# PARSEUR RESPONSABLES
# ─────────────────────────────────────────────────────────────

def parse_responsables(path: Path) -> pd.DataFrame:
    """
    Charge Responsables_modules_IDU.json.
    Colonnes : code_module, nom, prenom, nom_complet
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    table_entry = next(e for e in raw if e.get("type") == "table")
    df = pd.DataFrame(table_entry["data"])
    df["nom_complet"] = df["nom"].str.strip() + " " + df["prenom"].str.strip()
    df["code_module"] = df["code_module"].str.strip()

    logger.info(f"Responsables : {len(df)} entrées chargées")
    return df[["code_module", "nom", "prenom", "nom_complet"]]


# ─────────────────────────────────────────────────────────────
# PARSEUR DÉPENDANCES
# ─────────────────────────────────────────────────────────────

def parse_dependances(path: Path) -> pd.DataFrame:
    """
    Charge dependance_sequence_IDU.json.
    Colonnes : module_prec, type_prec, num_prec,
               module_suiv, type_suiv, num_suiv,
               prefix_prec, prefix_suiv
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    table_entry = next(e for e in raw if e.get("type") == "table")
    df = pd.DataFrame(table_entry["data"])

    df = df.rename(columns={
        "module_precedent": "module_prec",
        "type_precedent":   "type_prec",
        "numero_precedent": "num_prec",
        "module_suivant":   "module_suiv",
        "type_suivant":     "type_suiv",
        "numero_suivant":   "num_suiv",
    })

    df["num_prec"] = pd.to_numeric(df["num_prec"])
    df["num_suiv"] = pd.to_numeric(df["num_suiv"])
    # Préfixes (sans _IDU) pour jointure avec codes ADE
    df["prefix_prec"] = df["module_prec"].str.extract(r"^([A-Z]+\d+)")
    df["prefix_suiv"] = df["module_suiv"].str.extract(r"^([A-Z]+\d+)")

    logger.info(f"Dépendances : {len(df)} contraintes chargées")
    return df


# ─────────────────────────────────────────────────────────────
# PARSEUR MOODLE
# ─────────────────────────────────────────────────────────────

def parse_moodle(path: Path) -> pd.DataFrame:
    """
    Extrait les codes modules depuis Résumé Moodle IDU.html.
    Colonnes : code_prefix, present_moodle
    """
    with open(path, encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    text = soup.get_text(separator=" ")
    pattern = re.compile(r"\b((?:INFO|DATA|ISOC|MATH|PROJ)\d{3,4})\b")
    codes_found = sorted(set(pattern.findall(text)))

    rows = [{"code_prefix": code, "present_moodle": True} for code in codes_found]
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["code_prefix", "present_moodle"])

    logger.info(f"Moodle : {len(df)} codes modules détectés dans le HTML")
    return df


# ─────────────────────────────────────────────────────────────
# DÉDUPLICATION GROUPES PARALLÈLES
# ─────────────────────────────────────────────────────────────

def deduplicate_parallel_groups(seances: pd.DataFrame) -> pd.DataFrame:
    """
    Pour les séances is_parallel_grp=True (ex: INFO633_A01_G1 + _G2),
    ne conserve qu'une occurrence par créneau pour éviter de doubler les heures.
    """
    seances = seances.copy()
    seances["title_base"] = seances["title_original"].apply(
        lambda t: re.sub(r"_G[12]$", "", t, flags=re.IGNORECASE)
    )

    non_parallel   = seances[~seances["is_parallel_grp"]]
    parallel       = seances[ seances["is_parallel_grp"]]
    parallel_dedup = parallel.drop_duplicates(subset=["title_base", "starts_utc"])

    result = pd.concat([non_parallel, parallel_dedup], ignore_index=True)
    removed = len(seances) - len(result)
    if removed > 0:
        logger.info(f"Déduplication groupes parallèles : {removed} doublons supprimés")
    return result


# ─────────────────────────────────────────────────────────────
# RAPPORT DE QUALITÉ DU PARSING
# ─────────────────────────────────────────────────────────────

def build_parse_report(seances_raw: pd.DataFrame, maquette: pd.DataFrame) -> pd.DataFrame:
    """
    Génère un rapport sur la qualité du parsing :
    - taux de reconnaissance des titres ADE
    - codes ADE sans correspondance dans la maquette
    - titres non reconnus et titres sans type
    """
    total     = len(seances_raw)
    with_code = seances_raw["code_prefix"].notna().sum()
    with_type = seances_raw[seances_raw["code_prefix"].notna()]["type_seance"].notna().sum()

    maq_prefixes = set(
        m.group(1)
        for c in maquette["code_module"]
        if (m := re.match(r"^([A-Z]+\d+)", str(c).strip()))
    )
    ade_prefixes = set(
        m.group(1)
        for c in seances_raw["code_maquette"].dropna().unique()
        if (m := re.match(r"^([A-Z]+\d+)", str(c)))
    )
    codes_absents_maquette = ade_prefixes - maq_prefixes

    # Distinction : modules manquants connus (LANG/SHES/...) vs vrais inconnus
    modules_manquants_connus = sorted(
        c for c in codes_absents_maquette if get_famille_manquante(c)
    )
    codes_vraiment_inconnus = sorted(
        c for c in codes_absents_maquette if not get_famille_manquante(c)
    )

    unrecognized_titles = (
        seances_raw[seances_raw["code_prefix"].isna()]["title_original"]
        .value_counts().reset_index()
    )
    unrecognized_titles.columns = ["title", "count"]

    no_type = (
        seances_raw[
            seances_raw["code_prefix"].notna() &
            seances_raw["type_seance"].isna()
        ]["title_original"]
        .value_counts().reset_index()
    )
    no_type.columns = ["title", "count"]

    summary = pd.DataFrame([{
        "total_events":              total,
        "with_code":                 int(with_code),
        "with_code_pct":             round(with_code / total * 100, 1) if total else 0.0,
        "with_type":                 int(with_type),
        "with_type_pct":             round(with_type / total * 100, 1) if total else 0.0,
        "unrecognized_titles_count": len(unrecognized_titles),
        "modules_manquants_connus":  modules_manquants_connus,
        "codes_vraiment_inconnus":   codes_vraiment_inconnus,
    }])

    if total > 0:
        logger.info(
            f"Parse report : {with_code}/{total} événements avec code reconnu "
            f"({with_code / total * 100:.0f}%), "
            f"{with_type} avec type ({with_type / total * 100:.0f}%)"
        )
    else:
        logger.warning("Parse report : aucun événement à analyser (DataFrame vide)")

    return summary


# ─────────────────────────────────────────────────────────────
# POINT D'ENTRÉE PRINCIPAL
# ─────────────────────────────────────────────────────────────

def load_all_sources(data_dir: Optional[str] = None) -> ParsedSources:
    """
    Charge et normalise toutes les sources de données IDU.

    Args:
        data_dir: chemin vers le dossier data/. Si None, déduit depuis ce fichier.

    Returns:
        ParsedSources avec tous les DataFrames prêts à l'emploi.
    """
    # Ancrage au fichier source → indépendant du CWD
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    base = Path(data_dir)

    maquette     = parse_maquette(base / "MAQUETTE_IDU.json")

    adu3         = parse_ade(base / "ADECal_IDU3.json", "IDU3")
    adu4         = parse_ade(base / "ADECal_IDU4.json", "IDU4")
    adu5         = parse_ade(base / "ADECal_IDU5.json", "IDU5")
    seances_raw  = pd.concat([adu3, adu4, adu5], ignore_index=True)

    seances      = deduplicate_parallel_groups(seances_raw)

    # Post-traitement : un code marqué `famille_manquante` par préfixe (ex MATH531)
    # mais effectivement présent dans la maquette doit voir son flag effacé.
    maq_prefixes = {
        m.group(1)
        for c in maquette["code_module"]
        if (m := re.match(r"^([A-Z]+\d+)", str(c).strip()))
    }
    mask_dans_maquette = seances["code_prefix"].isin(maq_prefixes)
    seances.loc[mask_dans_maquette, "famille_manquante"] = None
    seances_raw.loc[seances_raw["code_prefix"].isin(maq_prefixes), "famille_manquante"] = None

    responsables = parse_responsables(base / "Responsables_modules_IDU.json")
    dependances  = parse_dependances(base / "dependance_sequence_IDU.json")
    moodle       = parse_moodle(base / "Résumé Moodle IDU.html")
    parse_report = build_parse_report(seances_raw, maquette)

    return ParsedSources(
        maquette=maquette,
        seances=seances,
        responsables=responsables,
        dependances=dependances,
        moodle=moodle,
        parse_report=parse_report,
    )


# ─────────────────────────────────────────────────────────────
# SCRIPT DE TEST RAPIDE
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    # Force UTF-8 sur Windows (terminal cp1252 par défaut)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data_path = sys.argv[1] if len(sys.argv) > 1 else None

    print("Chargement des sources...")
    sources = load_all_sources(data_path)

    SEP = "-" * 50

    print(f"\n== MAQUETTE ({len(sources.maquette)} modules) ==")
    print(SEP)
    print(sources.maquette.to_string(index=False))

    print(f"\n== SEANCES ADE ({len(sources.seances)} evenements, 10 premiers) ==")
    print(SEP)
    cols = ["title_original", "code_prefix", "type_seance", "is_exam",
            "is_parallel_grp", "duration_h", "promo"]
    print(sources.seances[cols].head(10).to_string(index=False))

    print("\n== RAPPORT PARSING ==")
    print(SEP)
    print(sources.parse_report.to_string(index=False))

    print(f"\n== DEPENDANCES ({len(sources.dependances)} contraintes, 5 premieres) ==")
    print(SEP)
    print(sources.dependances.head(5).to_string(index=False))

    print(f"\n== MOODLE ({len(sources.moodle)} codes detectes) ==")
    print(SEP)
    print(sources.moodle.to_string(index=False))

    print(f"\n== RESPONSABLES ({len(sources.responsables)} entrees) ==")
    print(SEP)
    print(sources.responsables.to_string(index=False))
