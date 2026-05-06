import pandas as pd
import json
import re
import os

NOISE_PATTERNS = [
    r'entreprise', r'rentrée', r'rentree', r'bde', r'lang',
    r'easi', r'férié', r'soutien', r'vacance', r'accueil', r'ferie'
]


def load_maquette_codes(maquette_path):
    """
    Load official module codes and create a lookup dictionary from prefix to full code.
    Example: 'INFO631' -> 'INFO631_IDU'
    """
    with open(maquette_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Locate the MAQUETTE_module table
    maquette_data = []
    for item in data:
        if isinstance(item, list):
            for sub_item in item:
                if isinstance(sub_item, dict) and sub_item.get('name') == 'MAQUETTE_module':
                    maquette_data = sub_item.get('data', [])
                    break
        elif isinstance(item, dict) and item.get('name') == 'MAQUETTE_module':
            maquette_data = item.get('data', [])
            break

    lookup = {}
    for mod in maquette_data:
        code = mod.get('code_module', '')
        if '_' in code:
            prefix = code.split('_')[0]
            lookup[prefix] = code
    return lookup


def extract_module_code(title, desc, lookup):
    """
    Extract the module code prefix (e.g. INFO631) and map to official code.
    """
    # Regex to find standard codes like INFO631, ISOC531, etc.
    match = re.search(r'([A-Z]{3,4}\d{3})', title)
    if not match:
        match = re.search(r'([A-Z]{3,4}\d{3})', desc)

    if match:
        prefix = match.group(1)
        if prefix in lookup:
            return lookup[prefix]
    return None


def extract_type_seance(title, desc):
    """
    Extract whether it's CM, TD, TP.
    """
    # Prefer explicit mentions in title like _TDG or (TD)
    if re.search(r'\b(CM)\b', title, re.IGNORECASE) or re.search(r'\(CM\)', desc, re.IGNORECASE):
        return 'CM'
    if re.search(
            r'\b(TD)\b',
            title,
            re.IGNORECASE) or re.search(
            r'\(TD\)',
            desc,
            re.IGNORECASE) or re.search(
                r'_TD',
                title,
            re.IGNORECASE):
        return 'TD'
    if re.search(
            r'\b(TP)\b',
            title,
            re.IGNORECASE) or re.search(
            r'\(TP\)',
            desc,
            re.IGNORECASE) or re.search(
                r'_TP',
                title,
            re.IGNORECASE):
        return 'TP'

    return 'UNKNOWN'


def extract_enseignants(desc):
    """
    Extract teacher names from description.
    They are typically all uppercase lines, not containing specific keywords.
    """
    lines = desc.split('\n')
    teachers = []
    for line in lines:
        line = line.strip()
        # Basic heuristic: if it's all uppercase and space/dash, and not a group like IDU-3
        if re.match(
                r'^[A-ZÉÈÀÇ\s\-]+$',
                line) and len(line) > 3 and not re.search(
                r'(IDU|MECA|SNI|EXPORT)',
                line):
            teachers.append(line)
    return ", ".join(teachers) if teachers else None


def extract_salle(location):
    """
    Extract room without the capacity (e.g. 'A-C217 (24pl.)' -> 'A-C217').
    """
    if pd.isna(location) or not location:
        return None
    # Just take everything before the first '('
    salles = []
    for loc in location.split(','):
        salles.append(loc.split('(')[0].strip())
    return ", ".join(salles)


def load_and_clean_ade_data(ade_files, maquette_path):
    # 1. Load official maquette mapping
    lookup = load_maquette_codes(maquette_path)

    # 2. Load and concatenate ADE JSON files
    dfs = []
    for f in ade_files:
        if os.path.exists(f):
            dfs.append(pd.read_json(f))
        else:
            print(f"Warning: File {f} not found.")

    if not dfs:
        raise ValueError("No ADE data loaded.")

    df = pd.concat(dfs, ignore_index=True)

    # 3. Filter Noise
    noise_regex = '|'.join(NOISE_PATTERNS)
    # Check title and description
    mask = df['Title'].str.contains(noise_regex, case=False, na=False) | \
        df['Description'].str.contains(noise_regex, case=False, na=False)

    df_clean = df[~mask].copy()

    # 4. Extract standard fields
    df_clean['module_code'] = df_clean.apply(
        lambda x: extract_module_code(
            x['Title'], x['Description'], lookup), axis=1)
    df_clean['type_seance'] = df_clean.apply(
        lambda x: extract_type_seance(
            x['Title'], x['Description']), axis=1)
    df_clean['enseignant'] = df_clean['Description'].apply(extract_enseignants)
    df_clean['salle'] = df_clean['Location'].apply(extract_salle)

    # 5. Handle Time (UTC -> Europe/Paris)
    df_clean['debut'] = pd.to_datetime(df_clean['Starts']).dt.tz_convert('Europe/Paris')
    df_clean['fin'] = pd.to_datetime(df_clean['Ends']).dt.tz_convert('Europe/Paris')

    # 6. Calculate Duration in hours
    df_clean['duree_h'] = (df_clean['fin'] - df_clean['debut']).dt.total_seconds() / 3600.0

    # Drop rows that don't match any official IDU module to stay within the perimeter
    # Since we only mapped official IDU codes, module_code will be None for non-IDU
    df_final = df_clean.dropna(subset=['module_code']).copy()

    # Reorder and keep only requested columns
    cols = ['module_code', 'type_seance', 'debut', 'fin', 'duree_h', 'enseignant', 'salle']
    df_final = df_final[cols]

    return df_final


if __name__ == "__main__":
    ade_files = [
        'data/ADECal_IDU3.json',
        'data/ADECal_IDU4.json',
        'data/ADECal_IDU5.json'
    ]
    maquette_path = 'data/MAQUETTE_IDU.json'

    print("Chargement et nettoyage des données ADE...")
    df_ade_clean = load_and_clean_ade_data(ade_files, maquette_path)

    print(f"Extraction terminée. {len(df_ade_clean)} séances trouvées.")
    print("\nAperçu des données :")
    print(df_ade_clean.head())

    # Optional: Save to CSV for next steps
    os.makedirs('data/clean', exist_ok=True)
    df_ade_clean.to_csv('data/clean/ade_clean.csv', index=False)
    print("\nFichier sauvegardé dans 'data/clean/ade_clean.csv'.")
