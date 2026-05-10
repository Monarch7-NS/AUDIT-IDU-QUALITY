"""
Streamlit dashboard for the IDU data quality audit.

Run with:
    streamlit run app/dashboard.py
Or via Makefile:
    make run
"""

import json
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from source_code.src.parsers import (
    parse_maquette,
    parse_ade,
    parse_responsables,
    parse_dependances,
    parse_moodle,
)
from source_code.src.rules.engine import run_audit

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Audit IDU — Qualité des données",
    page_icon="🔍",
    layout="wide",
)

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
REPORT_PATH = OUTPUT_DIR / "audit_report.json"


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Chargement des données…")
def load_report() -> dict:
    """Load or regenerate the audit report."""
    if REPORT_PATH.exists():
        with open(REPORT_PATH, encoding="utf-8") as f:
            return json.load(f)
    # Generate on the fly if not cached
    return run_audit(DATA_DIR, OUTPUT_DIR)


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

def main() -> None:
    st.title("🔍 Audit Qualité — Données Pédagogiques IDU")
    st.caption("Polytech Annecy-Chambéry · Filière IDU")

    # Sidebar — regenerate button
    with st.sidebar:
        st.header("Contrôles")
        if st.button("♻️ Relancer l'audit"):
            st.cache_data.clear()
            run_audit(DATA_DIR, OUTPUT_DIR)
            st.rerun()
        st.markdown("---")
        st.markdown("**Données sources**")
        for fname in [
            "MAQUETTE_IDU.json",
            "ADECal_IDU3.json",
            "ADECal_IDU4.json",
            "ADECal_IDU5.json",
            "Responsables_modules_IDU.json",
            "dependance_sequence_IDU.json",
        ]:
            status = "✅" if (DATA_DIR / fname).exists() else "❌"
            st.write(f"{status} {fname}")

    # ------------------------------------------------------------------ #
    # Check data availability
    # ------------------------------------------------------------------ #
    if not DATA_DIR.exists() or not any(DATA_DIR.iterdir()):
        st.error(
            f"Dossier `{DATA_DIR}` introuvable ou vide. "
            "Placez-y les fichiers JSON et relancez."
        )
        return

    report = load_report()
    summary = report["summary"]
    scores = report["scores"]
    anomalies = report["anomalies"]
    df = pd.DataFrame(anomalies)

    # ------------------------------------------------------------------ #
    # KPI row
    # ------------------------------------------------------------------ #
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Score global", f"{scores['global']:.0f}/100")
    col2.metric("🔴 Bloquantes", summary["bloquant"])
    col3.metric("🟠 Majeures", summary["majeur"])
    col4.metric("🟢 Mineures", summary["mineur"])
    col5.metric("Total anomalies", summary["total_anomalies"])

    st.markdown("---")

    # ------------------------------------------------------------------ #
    # Scores radar
    # ------------------------------------------------------------------ #
    tab1, tab2, tab3 = st.tabs(
        ["📊 Vue générale", "📋 Anomalies détaillées", "📈 Analyse horaire"]
    )

    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            _render_radar(scores)
        with c2:
            _render_criticite_donut(df)

    with tab2:
        _render_anomaly_table(df)

    with tab3:
        _render_hours_chart(DATA_DIR)


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _render_radar(scores: dict) -> None:
    dimensions = ["Complétude", "Exactitude", "Conformité", "Unicité", "Cohérence"]
    values = [
        scores["completude"],
        scores["exactitude"],
        scores["conformite"],
        scores["unicite"],
        scores["coherence"],
    ]
    fig = go.Figure(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=dimensions + [dimensions[0]],
            fill="toself",
            fillcolor="rgba(83,74,183,0.2)",
            line=dict(color="#534AB7"),
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        showlegend=False,
        title="Scores par dimension qualité",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_criticite_donut(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Aucune anomalie détectée.")
        return
    counts = df["criticite"].value_counts().reset_index()
    counts.columns = ["criticite", "count"]
    color_map = {"bloquant": "#E24B4A", "majeur": "#EF9F27", "mineur": "#639922"}
    fig = px.pie(
        counts,
        names="criticite",
        values="count",
        hole=0.5,
        color="criticite",
        color_discrete_map=color_map,
        title="Répartition par criticité",
    )
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)


def _render_anomaly_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.success("Aucune anomalie détectée — données impeccables !")
        return

    col1, col2 = st.columns(2)
    with col1:
        dimension_filter = st.multiselect(
            "Filtrer par dimension",
            options=df["dimension"].unique().tolist(),
            default=df["dimension"].unique().tolist(),
        )
    with col2:
        crit_filter = st.multiselect(
            "Filtrer par criticité",
            options=["bloquant", "majeur", "mineur"],
            default=["bloquant", "majeur", "mineur"],
        )

    filtered = df[
        df["dimension"].isin(dimension_filter)
        & df["criticite"].isin(crit_filter)
    ]

    def _color_criticite(val: str) -> str:
        colors = {"bloquant": "color: #A32D2D", "majeur": "color: #854F0B"}
        return colors.get(val, "color: #3B6D11")

    st.dataframe(
        filtered[["dimension", "code_module", "description", "criticite"]]
        .rename(columns={
            "dimension": "Dimension",
            "code_module": "Module",
            "description": "Description",
            "criticite": "Criticité",
        })
        .style.applymap(_color_criticite, subset=["Criticité"]),
        use_container_width=True,
        height=450,
    )
    st.caption(f"{len(filtered)} anomalie(s) affichée(s) sur {len(df)} au total")


def _render_hours_chart(data_dir: Path) -> None:
    """Bar chart comparing maquette vs ADE hours per module."""
    try:
        maquette = parse_maquette(data_dir / "MAQUETTE_IDU.json")
    except FileNotFoundError:
        st.warning("MAQUETTE_IDU.json introuvable.")
        return

    known_codes = {m["code_module"] for m in maquette}

    all_events = []
    for promo in ("IDU3", "IDU4", "IDU5"):
        path = data_dir / f"ADECal_{promo}.json"
        if path.exists():
            all_events.extend(parse_ade(path, promo, known_codes))

    # Build hours table
    from collections import defaultdict
    seen: set = set()
    ade_hours: dict = defaultdict(lambda: defaultdict(float))
    for evt in all_events:
        if evt["code"] and evt["session_type"] != "UNKNOWN":
            key = (evt["code"], evt["session_type"], evt["start"], evt["end"])
            if key not in seen:
                seen.add(key)
                ade_hours[evt["code"]][evt["session_type"]] += evt["duration_h"]

    rows = []
    for mod in maquette:
        code = mod["code_module"]
        for stype in ("CM", "TD", "TP"):
            planned = mod[stype.lower()]
            actual = ade_hours[code].get(stype, 0.0)
            if planned > 0 or actual > 0:
                rows.append({
                    "Module": code,
                    "Type": stype,
                    "Maquette (h)": planned,
                    "ADE (h)": round(actual, 1),
                    "Écart (%)": round(
                        abs(actual - planned) / planned * 100 if planned else 100, 1
                    ),
                })

    df_hours = pd.DataFrame(rows)
    stype_filter = st.selectbox("Type de séance", ["Tous", "CM", "TD", "TP"])
    if stype_filter != "Tous":
        df_hours = df_hours[df_hours["Type"] == stype_filter]

    df_display = df_hours[df_hours["Écart (%)"] > 0].nlargest(20, "Écart (%)")

    fig = go.Figure()
    fig.add_bar(
        name="Maquette",
        x=df_display["Module"] + " " + df_display["Type"],
        y=df_display["Maquette (h)"],
        marker_color="#B5D4F4",
    )
    fig.add_bar(
        name="ADE",
        x=df_display["Module"] + " " + df_display["Type"],
        y=df_display["ADE (h)"],
        marker_color="#F5C4B3",
    )
    fig.update_layout(
        barmode="group",
        title="Top 20 écarts horaires — Maquette vs ADE",
        xaxis_tickangle=-45,
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
