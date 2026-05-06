import pandas as pd
import numpy as np
import json
import os
import unicodedata


def remove_accents(input_str):
    if pd.isna(input_str) or not isinstance(input_str, str):
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()


def load_json_data(filepath, table_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Extract the correct table
    target_data = []
    for item in data:
        if isinstance(item, list):
            for sub_item in item:
                if isinstance(sub_item, dict) and sub_item.get('name') == table_name:
                    target_data = sub_item.get('data', [])
                    break
        elif isinstance(item, dict) and item.get('name') == table_name:
            target_data = item.get('data', [])
            break
    return pd.DataFrame(target_data)


def audit_completude(df_ade, df_maquette):
    ade_modules = df_ade['module_code'].dropna().unique()
    maquette_modules = df_maquette['code_module'].unique()

    missing_in_ade = [m for m in maquette_modules if m not in ade_modules]
    taux = (len(maquette_modules) - len(missing_in_ade)) / \
        len(maquette_modules) * 100 if len(maquette_modules) > 0 else 0

    df_missing = pd.DataFrame({'module_absent_ade': missing_in_ade})
    return taux, df_missing


def audit_exactitude(df_ade, df_maquette):
    # Prepare Maquette hours
    df_maq = df_maquette[['code_module', 'cm', 'td', 'tp']].copy()
    for col in ['cm', 'td', 'tp']:
        df_maq[col] = pd.to_numeric(df_maq[col], errors='coerce').fillna(0)
    df_maq = df_maq.melt(
        id_vars=['code_module'],
        var_name='type_seance',
        value_name='heures_maquette')
    df_maq['type_seance'] = df_maq['type_seance'].str.upper()

    # Prepare ADE hours
    df_ade_agg = df_ade.groupby(['module_code', 'type_seance'])['duree_h'].sum().reset_index()
    df_ade_agg.rename(columns={'module_code': 'code_module', 'duree_h': 'heures_ade'}, inplace=True)

    # Merge
    df_merged = pd.merge(df_maq, df_ade_agg, on=['code_module', 'type_seance'], how='outer').fillna(
        {'heures_maquette': 0, 'heures_ade': 0})

    # Calculate Ecart
    # Ecart = |ADE - Maquette| / Maquette * 100
    def calc_ecart(row):
        maq = row['heures_maquette']
        ade = row['heures_ade']
        if maq == 0:
            if ade == 0:
                return 0.0
            else:
                return np.inf  # or 100.0, using inf to denote unpredicted hours
        return abs(ade - maq) / maq * 100.0

    df_merged['ecart_pourcentage'] = df_merged.apply(calc_ecart, axis=1)
    return df_merged


def audit_coherence_responsables(df_ade, df_responsables):
    # Mapping of responsible per module
    resp_dict = {}
    for _, row in df_responsables.iterrows():
        nom = remove_accents(row['nom'])
        resp_dict[row['code_module']] = nom

    anomalies = []
    for idx, row in df_ade.iterrows():
        mod = row['module_code']
        enseignants = remove_accents(row['enseignant'])
        if pd.isna(mod) or mod not in resp_dict:
            continue

        resp_officiel = resp_dict[mod]
        # Check if the responsible is mentioned in the ADE teachers string
        if resp_officiel not in enseignants:
            anomalies.append({
                'module_code': mod,
                'type_seance': row['type_seance'],
                'debut': row['debut'],
                'enseignant_ade': row['enseignant'],
                'responsable_officiel': resp_officiel
            })

    return pd.DataFrame(anomalies)


def audit_unicite(df_ade):
    # Convert 'debut' and 'fin' to datetime if not already
    df = df_ade.copy()
    df['debut'] = pd.to_datetime(df['debut'], utc=True).dt.tz_convert('Europe/Paris')
    df['fin'] = pd.to_datetime(df['fin'], utc=True).dt.tz_convert('Europe/Paris')

    # Explode multiple teachers to check overlap per teacher individual
    df['enseignant_list'] = df['enseignant'].astype(str).str.split(', ')
    df_exp = df.explode('enseignant_list')
    df_exp = df_exp[df_exp['enseignant_list'].str.strip() != '']
    df_exp = df_exp.dropna(subset=['enseignant_list', 'debut', 'fin'])

    df_exp = df_exp.sort_values(by=['enseignant_list', 'debut'])

    chevauchements = []

    # Group by teacher
    for prof, group in df_exp.groupby('enseignant_list'):
        group = group.reset_index()
        for i in range(len(group) - 1):
            curr_fin = group.loc[i, 'fin']
            next_debut = group.loc[i + 1, 'debut']

            # Condition de chevauchement strict
            if next_debut < curr_fin:
                chevauchements.append({
                    'enseignant': prof,
                    'module_A': group.loc[i, 'module_code'],
                    'debut_A': group.loc[i, 'debut'],
                    'fin_A': curr_fin,
                    'module_B': group.loc[i + 1, 'module_code'],
                    'debut_B': next_debut,
                    'fin_B': group.loc[i + 1, 'fin']
                })

    return pd.DataFrame(chevauchements)


if __name__ == "__main__":
    print("Chargement des données pour l'audit...")
    df_ade = pd.read_csv('data/clean/ade_clean.csv')
    df_maquette = load_json_data('data/MAQUETTE_IDU.json', 'MAQUETTE_module')
    df_responsables = load_json_data('data/Responsables_modules_IDU.json', 'LNM_enseignant')

    os.makedirs('data/audit', exist_ok=True)

    # 1. Complétude
    taux_completude, df_missing = audit_completude(df_ade, df_maquette)
    print(f"\n[Complétude] Taux de modules planifiés: {taux_completude:.2f}%")
    df_missing.to_csv('data/audit/completude_manquants.csv', index=False)

    # 2. Exactitude
    df_exactitude = audit_exactitude(df_ade, df_maquette)
    print("\n[Exactitude] Calcul des écarts terminé (voir data/audit/exactitude.csv)")
    df_exactitude.to_csv('data/audit/exactitude.csv', index=False)

    # 3. Cohérence
    df_coherence = audit_coherence_responsables(df_ade, df_responsables)
    print(
        f"\n[Cohérence] {len(df_coherence)}"
        " séances où l'enseignant ADE n'est pas le responsable officiel."
    )

    df_coherence.to_csv('data/audit/coherence_responsables.csv', index=False)

    # 4. Unicité
    df_unicite = audit_unicite(df_ade)
    print(f"\n[Unicité] {len(df_unicite)} chevauchements détectés pour un même enseignant.")
    df_unicite.to_csv('data/audit/unicite_chevauchements.csv', index=False)

    print("\nAudit terminé. Fichiers sauvegardés dans data/audit/.")
