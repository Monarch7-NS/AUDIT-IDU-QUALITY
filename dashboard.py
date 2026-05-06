"""
Unified Streamlit dashboard — Audit IDU Qualité Pédagogique.

Merges:
- RAR pipeline (src/parsers + src/rules/engine) → structured audit_report.json
- Houssam's sequence DAG analysis (src/audit_sequence_dag) → graph visualizations

Run:
    streamlit run dashboard.py
Or via Makefile:
    make run
"""

import json
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Audit IDU — Qualité des données",
    page_icon="🛡️",
    layout="wide",
)

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
REPORT_PATH = OUTPUT_DIR / "audit_report.json"
SEQ_REPORT_PATH = DATA_DIR / "audit" / "audit_output.json"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Chargement du rapport d'audit…")
def load_report() -> dict:
    if REPORT_PATH.exists():
        with open(REPORT_PATH, encoding="utf-8") as f:
            return json.load(f)
    # Generate on the fly
    from src.rules.engine import run_audit
    return run_audit(DATA_DIR, OUTPUT_DIR)


@st.cache_data(show_spinner="Chargement de l'analyse de séquencement…")
def load_sequence_report() -> dict:
    if SEQ_REPORT_PATH.exists():
        with open(SEQ_REPORT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


@st.cache_data(show_spinner="Chargement des dépendances…")
def load_dependances() -> pd.DataFrame:
    dep_path = DATA_DIR / "dependance_sequence_IDU.json"
    if not dep_path.exists():
        return pd.DataFrame()
    with open(dep_path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for item in data:
        entries = item if isinstance(item, list) else [item]
        for sub in entries:
            if isinstance(sub, dict) and sub.get("name") == "MAQUETTE_dependance_sequence":
                rows = sub.get("data", [])
                break
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    with st.sidebar:
        st.header("Contrôles")
        if st.button("♻️ Relancer l'audit complet"):
            st.cache_data.clear()
            from src.rules.engine import run_audit
            run_audit(DATA_DIR, OUTPUT_DIR)
            st.rerun()

        st.markdown("---")
        st.markdown("**Sources de données**")
        sources = [
            "MAQUETTE_IDU.json",
            "ADECal_IDU3.json",
            "ADECal_IDU4.json",
            "ADECal_IDU5.json",
            "Responsables_modules_IDU.json",
            "dependance_sequence_IDU.json",
            "Résumé Moodle IDU.html",
        ]
        for fname in sources:
            icon = "✅" if (DATA_DIR / fname).exists() else "❌"
            st.write(f"{icon} {fname}")

        st.markdown("---")
        st.markdown("**Dashboards alternatifs**")
        if (OUTPUT_DIR / "dashboard_premium.html").exists():
            with open(OUTPUT_DIR / "dashboard_premium.html", encoding="utf-8") as f:
                html_bytes = f.read().encode()
            st.download_button(
                "⬇️ Télécharger le dashboard HTML",
                data=html_bytes,
                file_name="dashboard_premium.html",
                mime="text/html",
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    render_sidebar()

    st.title("🛡️ Audit Qualité — Données Pédagogiques IDU")
    st.caption("Polytech Annecy-Chambéry · Filière IDU")

    if not DATA_DIR.exists() or not any(DATA_DIR.iterdir()):
        st.error(f"Dossier `{DATA_DIR}` introuvable ou vide. Placez-y les fichiers JSON.")
        return

    report = load_report()
    seq_report = load_sequence_report()

    summary = report["summary"]
    scores = report["scores"]
    anomalies = report["anomalies"]
    events = report.get("events", [])
    df_anom = pd.DataFrame(anomalies)

    # ------------------------------------------------------------------ #
    # KPI row
    # ------------------------------------------------------------------ #
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Score global", f"{scores['global']:.0f}/100")
    col2.metric("🔴 Bloquantes", summary["bloquant"])
    col3.metric("🟠 Majeures", summary["majeur"])
    col4.metric("🟡 Mineures", summary["mineur"])
    col5.metric("Séances analysées", len(events))

    st.markdown("---")

    # ------------------------------------------------------------------ #
    # Tabs
    # ------------------------------------------------------------------ #
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Vue générale",
        "📋 Anomalies détaillées",
        "📈 Écarts horaires",
        "🕸️ Graphe de séquencement",
    ])

    with tab1:
        _render_overview(scores, df_anom)

    with tab2:
        _render_anomaly_table(df_anom)

    with tab3:
        _render_hours_chart(events, report)

    with tab4:
        _render_dag_view(seq_report)


# ---------------------------------------------------------------------------
# Tab 1 — Overview
# ---------------------------------------------------------------------------

def _render_overview(scores: dict, df_anom: pd.DataFrame) -> None:
    c1, c2 = st.columns([1, 1])

    with c1:
        dimensions = ["Complétude", "Exactitude", "Séquencement", "Unicité", "Cohérence"]
        values = [
            scores["completude"],
            scores["exactitude"],
            scores["conformite"],
            scores["unicite"],
            scores["coherence"],
        ]
        fig = go.Figure(go.Scatterpolar(
            r=values + [values[0]],
            theta=dimensions + [dimensions[0]],
            fill="toself",
            fillcolor="rgba(37, 99, 235, 0.2)",
            line=dict(color="#2563eb", width=2),
            marker=dict(color="#2563eb", size=6),
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(range=[0, 100])),
            showlegend=False,
            title="Scores par dimension qualité",
            height=380,
            margin=dict(t=40, b=20, l=40, r=40),
        )
        st.plotly_chart(fig, width="stretch")

    with c2:
        if df_anom.empty:
            st.info("Aucune anomalie détectée.")
        else:
            counts = df_anom["criticite"].value_counts().reset_index()
            counts.columns = ["criticite", "count"]
            color_map = {"bloquant": "#ef4444", "majeur": "#f59e0b", "mineur": "#38bdf8"}
            fig2 = px.pie(
                counts,
                names="criticite",
                values="count",
                hole=0.55,
                color="criticite",
                color_discrete_map=color_map,
                title="Répartition par criticité",
            )
            fig2.update_layout(height=380)
            st.plotly_chart(fig2, width="stretch")


# ---------------------------------------------------------------------------
# Tab 2 — Anomaly table
# ---------------------------------------------------------------------------

def _render_anomaly_table(df_anom: pd.DataFrame) -> None:
    if df_anom.empty:
        st.success("Aucune anomalie détectée — données impeccables !")
        return

    col1, col2 = st.columns(2)
    with col1:
        dim_options = df_anom["dimension"].unique().tolist() if "dimension" in df_anom.columns else []
        dim_filter = st.multiselect("Dimension", dim_options, default=dim_options)
    with col2:
        crit_filter = st.multiselect(
            "Criticité", ["bloquant", "majeur", "mineur"], default=["bloquant", "majeur", "mineur"]
        )

    filtered = df_anom.copy()
    if "dimension" in filtered.columns and dim_filter:
        filtered = filtered[filtered["dimension"].isin(dim_filter)]
    if "criticite" in filtered.columns:
        filtered = filtered[filtered["criticite"].isin(crit_filter)]

    priority_map = {"bloquant": 1, "majeur": 2, "mineur": 3}
    if "criticite" in filtered.columns:
        filtered["_prio"] = filtered["criticite"].map(priority_map).fillna(4)
        filtered = filtered.sort_values("_prio").drop(columns=["_prio"])

    def _color_crit(val: str) -> str:
        return {
            "bloquant": "color: #991b1b; font-weight: bold",
            "majeur": "color: #92400e",
            "mineur": "color: #075985",
        }.get(val, "")

    display_cols = [c for c in ["dimension", "code_module", "description", "criticite"] if c in filtered.columns]
    rename_map = {"dimension": "Dimension", "code_module": "Module", "description": "Description", "criticite": "Criticité"}
    styled = filtered[display_cols].rename(columns=rename_map)
    if "Criticité" in styled.columns:
        styled = styled.style.map(_color_crit, subset=["Criticité"])
    st.dataframe(styled, width="stretch", height=500)
    st.caption(f"{len(filtered)} anomalie(s) affichée(s) sur {len(df_anom)} au total")


# ---------------------------------------------------------------------------
# Tab 3 — Hours comparison
# ---------------------------------------------------------------------------

def _render_hours_chart(events: list, report: dict) -> None:
    st.markdown("**Comparaison Maquette vs ADE — Volume horaire par module**")

    if not events:
        st.warning("Aucune donnée de séances disponible.")
        return

    # Try to load maquette for planned hours
    maquette_path = DATA_DIR / "MAQUETTE_IDU.json"
    if not maquette_path.exists():
        st.warning("MAQUETTE_IDU.json introuvable.")
        return

    try:
        from src.parsers.maquette import parse_maquette
        maquette = parse_maquette(maquette_path)
    except Exception as e:
        st.error(f"Erreur chargement maquette: {e}")
        return

    # Compute actual hours from events (deduplicated)
    seen: set = set()
    ade_hours: dict = defaultdict(lambda: defaultdict(float))
    for evt in events:
        code = evt.get("code", "")
        stype = evt.get("session_type", "UNKNOWN")
        if code and stype != "UNKNOWN":
            key = (code, stype, evt.get("start"), evt.get("end"))
            if key not in seen:
                seen.add(key)
                ade_hours[code][stype] += evt.get("duration_h", 0)

    rows = []
    for mod in maquette:
        code = mod["code_module"]
        for stype, planned_key in [("CM", "cm"), ("TD", "td"), ("TP", "tp")]:
            planned = mod.get(planned_key, 0) or 0
            actual = ade_hours[code].get(stype, 0.0)
            if planned > 0 or actual > 0:
                rows.append({
                    "Module": code,
                    "Type": stype,
                    "Maquette (h)": planned,
                    "ADE (h)": round(actual, 1),
                    "Écart (%)": round(abs(actual - planned) / planned * 100 if planned else 100, 1),
                })

    if not rows:
        st.warning("Impossible de calculer les écarts horaires.")
        return

    df_hours = pd.DataFrame(rows)
    stype_filter = st.selectbox("Type de séance", ["Tous", "CM", "TD", "TP"])
    if stype_filter != "Tous":
        df_hours = df_hours[df_hours["Type"] == stype_filter]

    df_display = df_hours[df_hours["Écart (%)"] > 0].nlargest(25, "Écart (%)")

    fig = go.Figure()
    fig.add_bar(
        name="Maquette",
        x=df_display["Module"] + " " + df_display["Type"],
        y=df_display["Maquette (h)"],
        marker_color="#93c5fd",
    )
    fig.add_bar(
        name="ADE",
        x=df_display["Module"] + " " + df_display["Type"],
        y=df_display["ADE (h)"],
        marker_color="#fca5a5",
    )
    fig.update_layout(
        barmode="group",
        title="Top 25 écarts horaires — Maquette vs ADE",
        xaxis_tickangle=-45,
        height=480,
        legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig, width="stretch")

    with st.expander("📋 Tableau complet des écarts"):
        st.dataframe(df_hours.sort_values("Écart (%)", ascending=False), width="stretch")


# ---------------------------------------------------------------------------
# Tab 4 — Sequence DAG
# ---------------------------------------------------------------------------

def _render_dag_view(seq_report: dict) -> None:
    st.markdown("**Graphe interactif des dépendances de séquencement (DAG)**")
    st.caption("La maquette définit un ordre CM → TD → TP. Les liens rouges signalent les inversions détectées.")

    df_dep = load_dependances()
    if df_dep.empty:
        st.warning("Fichier `dependance_sequence_IDU.json` introuvable ou vide.")
        return

    required_cols = {"module_precedent", "type_precedent", "numero_precedent", "type_suivant", "numero_suivant"}
    if not required_cols.issubset(df_dep.columns):
        st.warning(f"Colonnes manquantes dans le fichier de dépendances. Trouvées: {list(df_dep.columns)}")
        return

    module_list = df_dep["module_precedent"].dropna().unique()
    if len(module_list) == 0:
        st.warning("Aucun module trouvé dans les dépendances.")
        return

    default_idx = list(module_list).index("MATH531_IDU") if "MATH531_IDU" in module_list else 0

    colA, colB = st.columns([1, 2])
    with colA:
        selected_mod = st.selectbox("Sélectionner un module", module_list, index=default_idx)

        # Show sequence audit details if available
        if seq_report:
            details = seq_report.get("module_details", {}).get(selected_mod, {})
            conformite = seq_report.get("conformite_details", {}).get(selected_mod, {})
            if details:
                st.markdown(f"**Diagnostic : {selected_mod}**")
                if details.get("status") == "Sain":
                    st.success(details.get("conclusion", "Séquence saine."))
                else:
                    st.error(details.get("conclusion", "Problème détecté."))
            if conformite:
                st.markdown(f"- Relations testées : **{conformite.get('total_relations', 0)}**")
                st.markdown(f"- Violations chronologiques : **{conformite.get('violations', 0)}**")
                st.markdown(f"- Taux de violation : **{round(conformite.get('taux_violation', 0), 2)}%**")
        else:
            st.info("Lancez `src/audit_sequence_dag.py` pour afficher les diagnostics détaillés.")

    with colB:
        df_mod = df_dep[df_dep["module_precedent"] == selected_mod].copy()
        df_mod = df_mod.dropna(subset=["type_precedent", "numero_precedent", "type_suivant", "numero_suivant"])
        df_mod = df_mod[df_mod["module_precedent"] == df_mod.get("module_suivant", df_mod["module_precedent"])] \
            if "module_suivant" in df_mod.columns else df_mod

        G = nx.DiGraph()
        edge_colors = []
        for _, row in df_mod.iterrows():
            n1 = f"{str(row['type_precedent']).strip()}_{row['numero_precedent']}"
            n2 = f"{str(row['type_suivant']).strip()}_{row['numero_suivant']}"
            G.add_edge(n1, n2)
            # Detect logical inversions: TP→CM, TP→TD, TD→CM are wrong
            t_a = str(row["type_precedent"]).strip()
            t_b = str(row["type_suivant"]).strip()
            is_inversion = (t_a == "TP" and t_b in ["CM", "TD"]) or (t_a == "TD" and t_b == "CM")
            edge_colors.append("#ef4444" if is_inversion else "#6b7280")

        if len(G.nodes) == 0:
            st.info("Aucune dépendance intra-module trouvée pour ce module.")
        else:
            pos = nx.spring_layout(G, seed=42)
            edge_x, edge_y, edge_color_list = [], [], []
            for idx, (u, v) in enumerate(G.edges()):
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                edge_x += [x0, x1, None]
                edge_y += [y0, y1, None]

            fig_net = go.Figure()
            # Draw edges (simple, no per-edge color in plotly without per-segment traces)
            for idx, (u, v) in enumerate(G.edges()):
                x0, y0 = pos[u]
                x1, y1 = pos[v]
                color = edge_colors[idx] if idx < len(edge_colors) else "#6b7280"
                fig_net.add_trace(go.Scatter(
                    x=[x0, x1, None], y=[y0, y1, None],
                    mode="lines",
                    line=dict(width=2, color=color),
                    hoverinfo="none",
                    showlegend=False,
                ))

            node_x = [pos[n][0] for n in G.nodes()]
            node_y = [pos[n][1] for n in G.nodes()]
            node_text = list(G.nodes())
            fig_net.add_trace(go.Scatter(
                x=node_x, y=node_y,
                mode="markers+text",
                text=node_text,
                textposition="top center",
                marker=dict(size=22, color="#93c5fd", line=dict(width=2, color="#2563eb")),
                hoverinfo="text",
                showlegend=False,
            ))
            fig_net.update_layout(
                showlegend=False,
                hovermode="closest",
                height=420,
                margin=dict(b=20, l=5, r=5, t=30),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                title=f"DAG de séquencement — {selected_mod}",
            )
            st.plotly_chart(fig_net, width="stretch")
            st.caption("🔴 Lien rouge = inversion logique (ex: TP avant CM/TD)")

    # Global sequence stats from seq_report
    if seq_report:
        stats = seq_report.get("statistiques_globales", {})
        if stats:
            st.markdown("---")
            st.markdown("**Statistiques globales du séquencement**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Modules audités", stats.get("total_modules_audites", "—"))
            c2.metric("Modules sains", stats.get("modules_sains", {}).get("count", "—"))
            c3.metric("Modules cassés", stats.get("modules_casses", {}).get("count", "—"))
            c4.metric("Sessions orphelines", stats.get("sessions_orphelines_count", "—"))


if __name__ == "__main__":
    main()
