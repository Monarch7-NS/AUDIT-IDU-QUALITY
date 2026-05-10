"""
Générateur de rapport LaTeX pour l'Audit IDU.
"""
import json
from pathlib import Path
from datetime import datetime

def generate_latex_report(json_path: Path, output_path: Path) -> None:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    summary = data['summary']
    scores = data['scores']
    anomalies = data['anomalies']

    bloquantes = [a for a in anomalies if a['criticite'] == 'bloquant'][:15]
    majeures = [a for a in anomalies if a['criticite'] == 'majeur'][:15]

    now_str = datetime.now().strftime("%d %B %Y")
    
    score_completude = scores.get('completude', 'N/A')
    score_exactitude = scores.get('exactitude', 'N/A')
    score_conformite = scores.get('conformite', 'N/A')
    score_unicite = scores.get('unicite', 'N/A')
    score_coherence = scores.get('coherence', 'N/A')
    
    anom_bloquant = summary.get('bloquant', 0)
    anom_majeur = summary.get('majeur', 0)
    anom_mineur = summary.get('mineur', 0)
    
    latex_content = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage[margin=2.5cm]{geometry}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{tcolorbox}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{mathpazo} % Police élégante

% Couleurs
\definecolor{primary}{RGB}{44, 62, 80}
\definecolor{secondary}{RGB}{52, 152, 219}
\definecolor{danger}{RGB}{231, 76, 60}
\definecolor{warning}{RGB}{241, 196, 15}
\definecolor{success}{RGB}{46, 204, 113}

\hypersetup{
    colorlinks=true,
    linkcolor=primary,
    urlcolor=secondary
}

\begin{document}

\begin{titlepage}
    \centering
    \vspace*{3cm}
    
    {\Huge \bfseries \color{primary} Rapport d'Audit Qualité \\[0.5cm] Données Pédagogiques IDU }\\[2cm]
    
    {\Large Hackathon Qualité de la Donnée - Polytech Annecy-Chambéry}\\[3cm]
    
    \begin{tcolorbox}[colback=gray!10, colframe=primary, width=10cm, arc=5mm, auto outer arc]
        \centering
        \vspace{0.5cm}
        {\huge \bfseries Score Global : """ + str(scores['global']) + r"""/100}\\[0.5cm]
        {\Large Total Anomalies : """ + str(summary['total_anomalies']) + r"""}
        \vspace{0.5cm}
    \end{tcolorbox}
    
    \vfill
    {\large Généré le """ + now_str + r"""}\\[1cm]
\end{titlepage}

\tableofcontents
\newpage

\section{Résumé Exécutif}

Ce rapport présente les résultats de l'audit automatisé de la qualité des données pédagogiques pour la filière IDU. L'audit a analysé les écarts entre la maquette théorique, les emplois du temps ADE et les responsabilités affectées, assurant ainsi la conformité et l'exactitude de la planification.

\subsection{Aperçu des Scores par Dimension}
\begin{center}
\begin{tabularx}{0.8\textwidth}{X r}
\toprule
\textbf{Dimension Qualité} & \textbf{Score} \\
\midrule
Complétude (présence des modules) & \textbf{""" + str(score_completude) + r"""/100} \\
Exactitude (volumes horaires) & \textbf{""" + str(score_exactitude) + r"""/100} \\
Conformité (séquencement logique) & \textbf{""" + str(score_conformite) + r"""/100} \\
Unicité (chevauchements) & \textbf{""" + str(score_unicite) + r"""/100} \\
Cohérence (responsabilités) & \textbf{""" + str(score_coherence) + r"""/100} \\
\bottomrule
\end{tabularx}
\end{center}

\section{Analyse des Anomalies}
L'audit a révélé un total de \textbf{""" + str(summary['total_anomalies']) + r"""} anomalies, réparties de la manière suivante :
\begin{itemize}
    \item \textcolor{danger}{\textbf{""" + str(anom_bloquant) + r""" anomalies bloquantes}} (Nécessitant une action immédiate)
    \item \textcolor{warning}{\textbf{""" + str(anom_majeur) + r""" anomalies majeures}} (Impactant la qualité de l'organisation)
    \item \textcolor{primary}{\textbf{""" + str(anom_mineur) + r""" anomalies mineures}} (Optimisations recommandées)
\end{itemize}

\newpage
\section{Détail des Anomalies Bloquantes (Échantillon)}

Les anomalies bloquantes empêchent le bon déroulement pédagogique ou constituent des erreurs majeures dans la base de données.

\begin{itemize}
"""
    for a in bloquantes:
        desc = str(a.get('description', '')).replace('&', '\\&').replace('%', '\\%').replace('#', '\\#')
        mod = str(a.get('code_module', '')).replace('_', '\\_')
        latex_content += rf"    \item \textbf{{[{a['dimension'].upper()}]}} Module {mod} : {desc}" + "\n"

    latex_content += r"""\end{itemize}

\section{Recommandations}

Suite à cet audit, il est recommandé de :
\begin{enumerate}
    \item \textbf{Corriger en priorité les erreurs de séquencement} (les cours de TP placés avant les CM correspondants).
    \item \textbf{Ajuster les volumes horaires ADE} pour correspondre strictement aux ECTS alloués dans la maquette officielle.
    \item \textbf{Normaliser les noms des enseignants} dans ADE pour éviter les faux doublons ou conflits de salles.
\end{enumerate}

\vspace{2cm}
\begin{center}
\textit{Ce rapport a été généré automatiquement par le moteur d'audit IDU.}
\end{center}

\end{document}
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    print(f"Rapport LaTeX généré avec succès dans : {output_path}")

if __name__ == "__main__":
    import sys
    data_dir = Path("output")
    json_path = data_dir / "audit_report.json"
    out_path = data_dir / "rapport_humain.tex"
    if not json_path.exists():
        print("Erreur : Le fichier audit_report.json n'existe pas.")
        sys.exit(1)
    generate_latex_report(json_path, out_path)
