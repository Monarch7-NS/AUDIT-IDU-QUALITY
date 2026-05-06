import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import numpy as np

st.set_page_config(page_title="Audit Qualité IDU", page_icon="🛡️", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Charger l'ancien JSON (qui contient les 6 dimensions et exactitude/cohérence/unicité)
    with open('data/audit_output.json', 'r', encoding='utf-8') as f:
        general_audit_json = json.load(f)
        
    # Charger le nouveau JSON généré par l'analyse de graphe (Chronologie, Inversions, Orphelines, Structure)
    try:
        with open('data/audit/audit_output.json', 'r', encoding='utf-8') as f:
            sequence_audit_json = json.load(f)
    except FileNotFoundError:
        sequence_audit_json = {}
        
    df_exactitude = pd.read_csv('data/audit/exactitude.csv')
    
    with open('data/dependance_sequence_IDU.json', 'r', encoding='utf-8') as f:
        seq_data = json.load(f)
        seq_list = []
        for item in seq_data:
            if isinstance(item, list):
                for sub in item:
                    if isinstance(sub, dict) and sub.get('name') == 'MAQUETTE_dependance_sequence':
                        seq_list = sub.get('data', [])
                        break
            elif isinstance(item, dict) and item.get('name') == 'MAQUETTE_dependance_sequence':
                seq_list = item.get('data', [])
                break
    df_dependances = pd.DataFrame(seq_list)
    return general_audit_json, sequence_audit_json, df_exactitude, df_dependances

general_audit_json, sequence_audit_json, df_exactitude, df_dependances = load_data()

# Préparation des anomalies combinées
old_anomalies = general_audit_json.get('anomalies', [])
# On retire les anciennes anomalies Chronologie/Structure pour utiliser notre nouveau moteur de graphe plus précis
filtered_old = [a for a in old_anomalies if a.get('type') not in ['Chronologie', 'Structure']]

# Normalisation des clés pour fusionner avec les nouvelles anomalies
for a in filtered_old:
    if 'module' in a: a['module_code'] = a.pop('module')
    if 'type' in a: a['type_anomalie'] = a.pop('type')
    # Normalisation de la criticité
    crit = a.get('criticite', '').upper()
    if crit == 'BLOQUANT': crit = 'BLOQUANTE'
    elif crit == 'MAJEUR': crit = 'ELEVEE'
    elif crit == 'MINEUR': crit = 'MOYENNE'
    a['criticite'] = crit

new_anomalies = sequence_audit_json.get('anomalies_detaillees', [])
all_anomalies = filtered_old + new_anomalies
anomalies = pd.DataFrame(all_anomalies)

# --- HEADER & STORYTELLING ---
st.title("🛡️ Dashboard Audit IDU : Qualité de la Donnée Pédagogique")
st.markdown("""
Bienvenue dans le rapport d'audit interactif. Ce tableau de bord évalue la santé globale de l'emploi du temps (ADE) par rapport au référentiel officiel (Maquette). 
**L'objectif** : Vous guider vers les anomalies critiques nécessitant une correction immédiate pour garantir un cursus fluide aux étudiants.
""")

col1, col2 = st.columns([1, 2])

with col1:
    score = general_audit_json.get('global_score', 0)
    st.metric(label="Score Global de Santé", value=f"{score}/100", delta="-18.8" if score < 100 else "0")
    st.markdown("### L'inventaire des Alertes")
    
    if not anomalies.empty:
        counts = anomalies['criticite'].value_counts()
        st.error(f"🚨 **{counts.get('BLOQUANTE', 0)} Bloquantes** (Structure Invalide, Graphes, Unicité)")
        st.warning(f"⚠️ **{counts.get('ELEVEE', 0)} Élevées** (Inversions Logiques, Exactitude)")
        st.info(f"ℹ️ **{counts.get('MOYENNE', 0)} Mineures** (Cohérence responsable, Orphelines)")
    else:
        st.success("Aucune anomalie détectée.")

with col2:
    st.markdown("### 🕸️ Les 6 Dimensions de Qualité")
    dims = general_audit_json.get('dimensions', {})
    
    if dims:
        r_vals = list(dims.values())
        r_vals.append(r_vals[0])
        theta_vals = list(dims.keys())
        theta_vals.append(theta_vals[0])
        
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=r_vals,
            theta=theta_vals,
            fill='toself',
            line_color='#00b4d8'
        ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig_radar, use_container_width=True)

st.divider()

# --- HEATMAP EXACTITUDE ---
st.markdown("### 🔥 Heatmap des Écarts d'Heures (Modules Problématiques)")
st.markdown("Ce graphe cible immédiatement les modules où le volume horaire planifié diffère drastiquement de la maquette.")
df_heatmap = df_exactitude.copy()
df_heatmap['ecart_pourcentage'] = df_heatmap['ecart_pourcentage'].replace([np.inf, -np.inf], 100)
df_heatmap = df_heatmap[df_heatmap['ecart_pourcentage'] > 0]

if not df_heatmap.empty:
    pivot = df_heatmap.pivot_table(index='code_module', columns='type_seance', values='ecart_pourcentage', fill_value=0)
    fig_heat = px.imshow(pivot, labels=dict(x="Type Séance", y="Module", color="Écart (%)"), color_continuous_scale='Reds', aspect='auto')
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.success("Aucun écart significatif.")

st.divider()

# --- GRAPHE DE DEPENDANCES ---
st.markdown("### 🕵️ Graphe Interactif des Dépendances (Théorie des Graphes)")
st.markdown("La maquette prévoit un ordre strict. Voici le DAG (Directed Acyclic Graph) des modules. Les liens en **rouge** indiquent les règles du référentiel.")

def plot_network(module_code):
    df_mod = df_dependances[df_dependances['module_precedent'] == module_code]
    G = nx.DiGraph()
    for _, row in df_mod.iterrows():
        n1 = f"{row['type_precedent']}_{row['numero_precedent']}"
        n2 = f"{row['type_suivant']}_{row['numero_suivant']}"
        G.add_edge(n1, n2)
        
    pos = nx.spring_layout(G, seed=42)
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=2, color='red'), hoverinfo='none', mode='lines', name='Dépendances')
    
    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="top center",
                            marker=dict(showscale=False, color='lightblue', size=20, line_width=2))
    
    fig = go.Figure(data=[edge_trace, node_trace],
             layout=go.Layout(
                showlegend=False, hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                )
    return fig

colA, colB = st.columns([1, 2])
with colA:
    mod_list = df_dependances['module_precedent'].dropna().unique()
    default_idx = list(mod_list).index("MATH531_IDU") if "MATH531_IDU" in mod_list else 0
    selected_mod = st.selectbox("Sélectionner un module pour visualiser son graphe", mod_list, index=default_idx)
    
    # Nouveaux diagnostics (Depuis le nouveau fichier JSON)
    details = sequence_audit_json.get("module_details", {}).get(selected_mod, {})
    st.markdown(f"**Diagnostic pour {selected_mod} :**")
    if details.get('status') == 'Sain':
        st.success(details.get('conclusion', 'Séquence saine.'))
    else:
        st.error(details.get('conclusion', 'Problème détecté.'))
        
    conformite = sequence_audit_json.get("conformite_details", {}).get(selected_mod, {})
    if conformite:
        st.markdown(f"- **Relations testées :** {conformite.get('total_relations')}")
        st.markdown(f"- **Violations chronologiques :** {conformite.get('violations')}")
        st.markdown(f"- **Taux de violation :** {round(conformite.get('taux_violation', 0), 2)}%")

with colB:
    fig_net = plot_network(selected_mod)
    st.plotly_chart(fig_net, use_container_width=True)

# --- INVENTAIRE FINAL ---
st.markdown("### 📋 Liste des Anomalies (Top 50 Pires)")
if not anomalies.empty:
    # Trier par criticité
    priority = {'BLOQUANTE': 1, 'ELEVEE': 2, 'MOYENNE': 3}
    anomalies['priorite'] = anomalies['criticite'].map(priority).fillna(4)
    anomalies = anomalies.sort_values('priorite').drop('priorite', axis=1)
    
    anomalies_disp = anomalies.head(50)
    
    def color_criticite(val):
        if val == 'BLOQUANTE': return 'background-color: #ff4b4b; color: white; font-weight: bold'
        elif val == 'ELEVEE': return 'background-color: #ffa421; color: white'
        elif val == 'MOYENNE': return 'background-color: #1c83e1; color: white'
        return ''
        
    styled_df = anomalies_disp.style.map(color_criticite, subset=['criticite'])
    st.dataframe(styled_df, use_container_width=True)
else:
    st.success("Aucune anomalie à afficher.")
