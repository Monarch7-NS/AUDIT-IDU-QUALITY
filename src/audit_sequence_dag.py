import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import json
import os


def load_json_data(filepath, table_name):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
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


def build_dags_and_nodes(df_seq):
    graphs = {}
    nodes_in_rules = {}
    df_seq = df_seq.dropna(
        subset=[
            'module_precedent',
            'type_precedent',
            'numero_precedent',
            'module_suivant',
            'type_suivant',
            'numero_suivant'])

    for module, group in df_seq.groupby('module_precedent'):
        G = nx.DiGraph()
        module_nodes = set()
        for _, row in group.iterrows():
            if row['module_precedent'] != row['module_suivant']:
                continue

            node_A = f"{row['type_precedent'].strip()}_{row['numero_precedent']}"
            node_B = f"{row['type_suivant'].strip()}_{row['numero_suivant']}"
            G.add_edge(node_A, node_B)
            module_nodes.add(node_A)
            module_nodes.add(node_B)

        graphs[module] = G
        nodes_in_rules[module] = module_nodes
    return graphs, nodes_in_rules


def detect_logical_inversions(module, type_A, type_B):
    # Règle empirique: CM -> TD -> TP
    # Inversions: TP -> CM, TP -> TD, TD -> CM
    if (type_A == 'TP' and type_B in ['CM', 'TD']) or (type_A == 'TD' and type_B == 'CM'):
        return True
    return False


def audit_theoretical_dags(graphs):
    module_status = {}
    anomalies = []

    for module, G in graphs.items():
        if len(G.nodes) == 0:
            continue

        is_dag = nx.is_directed_acyclic_graph(G)
        n_components = nx.number_weakly_connected_components(G)
        start_nodes = [n for n, d in G.in_degree() if d == 0]

        # Check inversions
        for u, v in G.edges():
            type_A = u.split('_')[0]
            type_B = v.split('_')[0]
            if detect_logical_inversions(module, type_A, type_B):
                anomalies.append({
                    'module_code': module,
                    'type_anomalie': 'Inversion Logique',
                    'description': f'Règle illogique dans la maquette: {u} doit précéder {v}',
                    'criticite': 'ELEVEE'
                })

        status = "Sain"
        conclusion = "Graphe connexe et acyclique, séquence saine."
        if not is_dag:
            status = "Incomplète / Invalide"
            conclusion = "Boucle infinie détectée dans le graphe (pas un DAG)."
            anomalies.append({'module_code': module, 'type_anomalie': 'Structure',
                             'description': conclusion, 'criticite': 'BLOQUANTE'})
        elif n_components > 1:
            status = "Cassé"
            conclusion = (
                f"Graphe morcelé en {n_components} composantes"
                " déconnectées (chaîne brisée)."
            )
            anomalies.append({'module_code': module, 'type_anomalie': 'Structure',
                             'description': conclusion, 'criticite': 'BLOQUANTE'})
        elif len(start_nodes) == 0:
            status = "Incomplète / Invalide"
            conclusion = "Aucun point de départ (in_degree 0) dans le graphe."
            anomalies.append({'module_code': module, 'type_anomalie': 'Structure',
                             'description': conclusion, 'criticite': 'BLOQUANTE'})

        module_status[module] = {
            'status': status,
            'n_components': n_components,
            'conclusion': conclusion
        }

    return module_status, anomalies


def validate_and_find_orphans(graphs, nodes_in_rules, module_status, df_ade):
    anomalies = []
    orphelines = []
    conformite_stats = {}

    df = df_ade.copy()
    df['debut'] = pd.to_datetime(df['debut'], utc=True).dt.tz_convert('Europe/Paris')
    df['numero_infere'] = df.groupby(['module_code', 'type_seance'])[
        'debut'].rank(method='dense').astype(int)

    for module, G in graphs.items():
        df_mod = df[df['module_code'] == module].copy()
        if df_mod.empty:
            continue

        # Identifier les sessions orphelines (dans ADE mais pas dans le graphe des dépendances)
        df_mod['node_name'] = df_mod['type_seance'] + "_" + df_mod['numero_infere'].astype(str)
        nodes_ade = set(df_mod['node_name'].unique())
        nodes_theoriques = nodes_in_rules.get(module, set())

        orphelins_mod = nodes_ade - nodes_theoriques
        for o in orphelins_mod:
            orphelines.append({'module_code': module, 'session_orpheline': o})
            anomalies.append({
                'module_code': module,
                'type_anomalie': 'Session Orpheline',
                'description': (
                    f'Session {o} planifiée dans ADE'
                    ' mais absente du graphe de dépendance.'
                ),
                'criticite': 'MOYENNE'
            })

        # Validation de conformité (seulement pour Sains, ou pour tous pour voir les violations)
        # On calcule le Taux de Violation de Conformité
        total_edges = G.number_of_edges()
        violations = 0

        for u, v in G.edges():
            type_A, num_A = u.split('_')
            type_B, num_B = v.split('_')

            seances_A = df_mod[df_mod['node_name'] == u]
            seances_B = df_mod[df_mod['node_name'] == v]

            if seances_A.empty or seances_B.empty:
                continue

            max_debut_A = seances_A['debut'].max()
            min_debut_B = seances_B['debut'].min()

            if max_debut_A > min_debut_B:
                violations += 1
                anomalies.append({
                    'module_code': module,
                    'type_anomalie': 'Chronologie',
                    'description': f'Violation de précédence: {u} a lieu APRES {v}',
                    'criticite': 'BLOQUANTE'
                })

        taux_violation = (violations / total_edges * 100) if total_edges > 0 else 0
        conformite_stats[module] = {
            'total_relations': total_edges,
            'violations': violations,
            'taux_violation': taux_violation
        }

    return anomalies, orphelines, conformite_stats


def plot_worst_modules(graphs, module_status):
    os.makedirs('data/audit/plots', exist_ok=True)

    # Selectionner les 3 pires (ceux qui ne sont pas Sains)
    pires = [(mod, stats) for mod, stats in module_status.items() if stats['status'] != 'Sain']
    pires_sorted = sorted(pires, key=lambda x: x[1]['n_components'], reverse=True)
    top_3 = [x[0] for x in pires_sorted[:3]]

    for mod in top_3:
        G = graphs[mod]
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)
        nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=2000,
                font_size=10, font_weight='bold', edge_color='gray', arrows=True)
        plt.title(f"Graphe Déconnecté : {mod}\n{module_status[mod]['conclusion']}")
        plt.savefig(f'data/audit/plots/graph_{mod}.png', bbox_inches='tight')
        plt.close()
        print(f"Graphe généré pour {mod} : data/audit/plots/graph_{mod}.png")


if __name__ == "__main__":
    print("Chargement des données pour l'audit...")
    df_seq = load_json_data('data/dependance_sequence_IDU.json', 'MAQUETTE_dependance_sequence')
    df_ade = pd.read_csv('data/clean/ade_clean.csv')

    print("1. Construction des DAGs et analyse structurelle...")
    graphs, nodes_in_rules = build_dags_and_nodes(df_seq)
    module_status, structure_anomalies = audit_theoretical_dags(graphs)

    print("2. Confrontation ADE : Connectivité et Chronologie...")
    ade_anomalies, orphelines, conformite_stats = validate_and_find_orphans(
        graphs, nodes_in_rules, module_status, df_ade)

    all_anomalies = structure_anomalies + ade_anomalies

    # 3. Statistiques Globales
    total_modules = len(graphs)
    status_counts = {'Sain': 0, 'Cassé': 0, 'Incomplète / Invalide': 0}
    for stats in module_status.values():
        status_counts[stats['status']] += 1

    sain_pct = (status_counts['Sain'] / total_modules * 100) if total_modules > 0 else 0
    casse_pct = (status_counts['Cassé'] / total_modules * 100) if total_modules > 0 else 0
    incomplet_pct = (
        status_counts['Incomplète / Invalide'] /
        total_modules *
        100) if total_modules > 0 else 0

    taux_moyens_violation = sum([stats['taux_violation'] for stats in conformite_stats.values(
    )]) / len(conformite_stats) if conformite_stats else 0

    global_audit_stats = {
        'total_modules_audites': total_modules,
        'modules_sains': {
            'count': status_counts['Sain'],
            'pourcentage': round(
                sain_pct,
                2)},
        'modules_casses': {
            'count': status_counts['Cassé'],
            'pourcentage': round(
                casse_pct,
                2)},
        'modules_incomplets': {
            'count': status_counts['Incomplète / Invalide'],
            'pourcentage': round(
                incomplet_pct,
                2)},
        'taux_moyen_violation_conformite': round(
            taux_moyens_violation,
            2),
        'sessions_orphelines_count': len(orphelines),
        'sessions_orphelines': orphelines}

    # 4. Export JSON
    os.makedirs('data/audit', exist_ok=True)
    audit_output = {
        'statistiques_globales': global_audit_stats,
        'module_details': module_status,
        'conformite_details': conformite_stats,
        'anomalies_detaillees': all_anomalies
    }

    with open('data/audit/audit_output.json', 'w', encoding='utf-8') as f:
        json.dump(audit_output, f, indent=4, ensure_ascii=False)

    pd.DataFrame(all_anomalies).to_csv('data/audit/sequence_anomalies.csv', index=False)

    print("\n--- STATISTIQUES GLOBALES ---")
    print(f"Total modules audités: {total_modules}")
    print(f"Sains: {status_counts['Sain']} ({sain_pct:.2f}%)")
    print(f"Cassés: {status_counts['Cassé']} ({casse_pct:.2f}%)")
    print(f"Incomplets: {status_counts['Incomplète / Invalide']} ({incomplet_pct:.2f}%)")
    print(f"Sessions Orphelines (ADE sans graphe) : {len(orphelines)}")
    print(f"Taux moyen de violation chronologique : {taux_moyens_violation:.2f}%")

    print("\n4. Génération des graphiques pour les 3 pires modules...")
    plot_worst_modules(graphs, module_status)
    print("\nAudit complété avec succès ! Fichiers dans data/audit/")
