"""
Générateur de dashboard HTML autonome.
Design épuré, professionnel, type SaaS.
"""
import json
from pathlib import Path
from datetime import datetime

def generate_html_dashboard(json_path: Path, output_path: Path) -> None:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    summary = data['summary']
    scores = data['scores']
    anomalies = data['anomalies']
    events = data.get('events', [])
    generated_at = data.get('generated_at', datetime.now().isoformat())[:10]
    
    score_completude = scores.get('completude', 0)
    score_exactitude = scores.get('exactitude', 0)
    score_conformite = scores.get('conformite', 0)
    score_unicite = scores.get('unicite', 0)
    score_coherence = scores.get('coherence', 0)
    
    anom_bloquant = summary.get('bloquant', 0)
    anom_majeur = summary.get('majeur', 0)
    anom_mineur = summary.get('mineur', 0)

    # Préparation des événements pour le calendrier
    anomalies_by_module = {}
    for a in anomalies:
        mod = a.get('code_module')
        if mod:
            if mod not in anomalies_by_module:
                anomalies_by_module[mod] = a['criticite']
            else:
                current = anomalies_by_module[mod]
                new_c = a['criticite']
                if new_c == 'bloquant' or (new_c == 'majeur' and current == 'mineur'):
                    anomalies_by_module[mod] = new_c
                
    fc_events = []
    first_date = None
    for e in events:
        mod = e.get('code', '')
        criticite = anomalies_by_module.get(mod, 'normal')
        
        # Couleurs professionnelles, douces
        if criticite == 'bloquant':
            bg_color = '#fee2e2'
            border_color = '#ef4444'
            text_color = '#991b1b'
        elif criticite == 'majeur':
            bg_color = '#fef3c7'
            border_color = '#f59e0b'
            text_color = '#92400e'
        elif criticite == 'mineur':
            bg_color = '#e0f2fe'
            border_color = '#38bdf8'
            text_color = '#075985'
        else:
            bg_color = '#d1fae5'
            border_color = '#10b981'
            text_color = '#065f46'
            
        start_str = e.get('start', '')
        if start_str and not first_date:
            first_date = start_str[:10]
            
        fc_events.append({
            'title': e.get('title', ''),
            'start': start_str,
            'end': e.get('end', ''),
            'backgroundColor': bg_color,
            'borderColor': border_color,
            'textColor': text_color,
            'extendedProps': {
                'location': e.get('location', ''),
                'teachers': ', '.join(e.get('teachers', [])),
                'session_type': e.get('session_type', ''),
                'criticite': criticite,
                'promo': e.get('promo', 'IDU')
            }
        })
    
    fc_events_json = json.dumps(fc_events)
    initial_date = first_date if first_date else '2025-09-01'

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polytech | Qualité Pédagogique</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js'></script>
    <script src="https://cdn.jsdelivr.net/npm/@fullcalendar/core@6.1.15/locales/fr.global.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-body: #f3f4f6;
            --bg-card: #ffffff;
            --text-main: #111827;
            --text-muted: #6b7280;
            --border: #e5e7eb;
            --primary: #2563eb;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
            --sidebar-width: 250px;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            display: flex;
            min-height: 100vh;
        }}

        /* Sidebar Layout */
        .sidebar {{
            width: var(--sidebar-width);
            background-color: #ffffff;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            position: fixed;
            height: 100vh;
            z-index: 10;
        }}
        
        .logo-area {{
            padding: 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .logo-icon {{
            width: 32px; height: 32px; background: var(--primary); color: white;
            border-radius: 6px; display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 1.2rem;
        }}
        
        .logo-text {{ font-weight: 700; font-size: 1.1rem; color: #111827; }}
        
        .nav-links {{ padding: 1.5rem 1rem; display: flex; flex-direction: column; gap: 0.5rem; }}
        .nav-link {{
            padding: 0.75rem 1rem; border-radius: 6px; color: var(--text-muted);
            text-decoration: none; font-weight: 500; font-size: 0.95rem;
            display: flex; align-items: center; gap: 0.75rem;
        }}
        .nav-link.active {{ background-color: #eff6ff; color: var(--primary); }}
        
        /* Main Content */
        .main-content {{
            flex: 1;
            margin-left: var(--sidebar-width);
            display: flex;
            flex-direction: column;
        }}
        
        .topbar {{
            height: 70px; background: #ffffff; border-bottom: 1px solid var(--border);
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 2rem;
        }}
        
        .page-title {{ font-size: 1.25rem; font-weight: 600; }}
        .user-info {{ display: flex; align-items: center; gap: 1rem; color: var(--text-muted); font-size: 0.9rem; }}
        
        .content-wrapper {{ padding: 2rem; max-width: 1400px; margin: 0 auto; width: 100%; }}
        
        /* Dashboard Grid */
        .grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1.5rem;
        }}
        
        .col-3 {{ grid-column: span 3; }}
        .col-4 {{ grid-column: span 4; }}
        .col-8 {{ grid-column: span 8; }}
        .col-12 {{ grid-column: span 12; }}
        
        @media (max-width: 1200px) {{
            .col-3 {{ grid-column: span 6; }}
            .col-4, .col-8 {{ grid-column: span 12; }}
        }}
        @media (max-width: 768px) {{
            .col-3 {{ grid-column: span 12; }}
            .sidebar {{ display: none; }}
            .main-content {{ margin-left: 0; }}
        }}
        
        /* Cards */
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 1rem; }}
        .card-title {{ font-size: 1rem; font-weight: 600; color: var(--text-main); display: flex; align-items: center; gap: 0.5rem; }}
        
        /* KPIs */
        .kpi-label {{ font-size: 0.875rem; color: var(--text-muted); font-weight: 500; margin-bottom: 0.5rem; }}
        .kpi-value {{ font-size: 2.25rem; font-weight: 700; color: var(--text-main); line-height: 1.2; }}
        .kpi-subtext {{ font-size: 0.875rem; margin-top: 0.5rem; display: flex; align-items: center; gap: 0.25rem; }}
        
        .text-success {{ color: var(--success); }}
        .text-danger {{ color: var(--danger); }}
        .text-warning {{ color: var(--warning); }}
        
        /* Table */
        .table-container {{ overflow-x: auto; max-height: 400px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ position: sticky; top: 0; background: #f9fafb; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }}
        td {{ padding: 1rem; font-size: 0.875rem; color: var(--text-main); border-bottom: 1px solid var(--border); }}
        tr:last-child td {{ border-bottom: none; }}
        
        .badge {{ display: inline-flex; align-items: center; padding: 0.125rem 0.625rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; }}
        .bg-red {{ background: #fee2e2; color: #991b1b; }}
        .bg-yellow {{ background: #fef3c7; color: #92400e; }}
        .bg-blue {{ background: #e0f2fe; color: #075985; }}
        .bg-green {{ background: #d1fae5; color: #065f46; }}
        
        /* FullCalendar styling */
        .fc {{ font-size: 0.85rem; }}
        .fc-theme-standard .fc-scrollgrid {{ border-color: var(--border); }}
        .fc-theme-standard th, .fc-theme-standard td {{ border-color: var(--border); }}
        .fc-col-header-cell-cushion {{ color: var(--text-main); font-weight: 600; padding: 8px 0; }}
        .fc-daygrid-day-number {{ color: var(--text-main); }}
        .fc-event {{ padding: 4px; border-radius: 4px; cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border-left-width: 4px !important; transition: transform 0.1s ease; }}
        .fc-event:hover {{ transform: scale(1.02); z-index: 10; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .fc-event-main {{ font-weight: 500; }}
        .fc-button-primary {{ background-color: #ffffff !important; border-color: var(--border) !important; color: var(--text-main) !important; font-weight: 500 !important; text-transform: capitalize !important; }}
        .fc-button-primary:hover {{ background-color: #f9fafb !important; }}
        .fc-button-active {{ background-color: #f3f4f6 !important; }}
        .fc-toolbar-title {{ font-size: 1.1rem !important; font-weight: 600 !important; color: var(--text-main); text-transform: capitalize; }}

        /* Legend & Filters */
        .filters-area {{ display: flex; align-items: center; gap: 1.5rem; }}
        .filter-group {{ display: flex; align-items: center; gap: 0.5rem; }}
        .filter-label {{ font-size: 0.85rem; font-weight: 600; color: var(--text-muted); }}
        .filter-select {{ padding: 0.35rem 2rem 0.35rem 0.75rem; border: 1px solid var(--border); border-radius: 6px; font-size: 0.85rem; color: var(--text-main); background-color: #fff; cursor: pointer; }}
        .legend-item {{ display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text-muted); }}
        .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
        
        /* SweetAlert Customization */
        div:where(.swal2-container) div:where(.swal2-popup) {{ font-family: 'Inter', sans-serif; border-radius: 12px; }}
        .swal2-html-container {{ text-align: left !important; font-size: 0.95rem !important; color: var(--text-main) !important; }}
        .event-detail-row {{ display: flex; border-bottom: 1px solid var(--border); padding: 0.75rem 0; }}
        .event-detail-row:last-child {{ border-bottom: none; }}
        .event-detail-label {{ width: 120px; font-weight: 600; color: var(--text-muted); }}
        .event-detail-value {{ flex: 1; }}
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div class="sidebar">
        <div class="logo-area">
            <div class="logo-icon">P</div>
            <div class="logo-text">Polytech IDU</div>
        </div>
        <div class="nav-links">
            <a href="#" class="nav-link active">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>
                Tableau de bord
            </a>
            <a href="#" class="nav-link">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                Calendrier (Agenda)
            </a>
            <a href="#" class="nav-link">
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
                Rapport LaTeX
            </a>
        </div>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div class="topbar">
            <div class="page-title">Rapport d'Audit des Données Pédagogiques</div>
            <div class="user-info">
                <span>Dernière mise à jour : {generated_at}</span>
                <div style="width:32px; height:32px; background:#e5e7eb; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#6b7280; font-weight:600;">AD</div>
            </div>
        </div>
        
        <div class="content-wrapper">
            <div class="grid">
                
                <!-- KPIs -->
                <div class="card col-3">
                    <div class="kpi-label">Score d'Audit Global</div>
                    <div class="kpi-value">{scores['global']}<span style="font-size:1.25rem; color:var(--text-muted);">/100</span></div>
                    <div class="kpi-subtext text-success">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                        Qualité satisfaisante
                    </div>
                </div>
                
                <div class="card col-3">
                    <div class="kpi-label">Anomalies Bloquantes</div>
                    <div class="kpi-value">{anom_bloquant}</div>
                    <div class="kpi-subtext text-danger">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                        Nécessitent une action immédiate
                    </div>
                </div>
                
                <div class="card col-3">
                    <div class="kpi-label">Anomalies Majeures</div>
                    <div class="kpi-value">{anom_majeur}</div>
                    <div class="kpi-subtext text-warning">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        Revue recommandée
                    </div>
                </div>
                
                <div class="card col-3">
                    <div class="kpi-label">Séances Analysées</div>
                    <div class="kpi-value">{len(events)}</div>
                    <div class="kpi-subtext" style="color:var(--text-muted)">
                        Tiré de ADE (Promos IDU 3, 4, 5)
                    </div>
                </div>

                <!-- Calendar -->
                <div class="card col-12">
                    <div class="card-header">
                        <div class="card-title">
                            <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                            Agenda Pédagogique Interactif
                        </div>
                        <div class="filters-area">
                            <div class="filter-group">
                                <label class="filter-label" for="promoFilter">Promotion :</label>
                                <select id="promoFilter" class="filter-select">
                                    <option value="ALL">Toutes les promos</option>
                                    <option value="IDU3">IDU 3</option>
                                    <option value="IDU4">IDU 4</option>
                                    <option value="IDU5">IDU 5</option>
                                </select>
                            </div>
                            <div class="filter-group">
                                <label class="filter-label" for="statusFilter">Affichage :</label>
                                <select id="statusFilter" class="filter-select">
                                    <option value="ALL">Tous les cours</option>
                                    <option value="ANOMALIES">Anomalies uniquement (Rouge/Orange)</option>
                                </select>
                            </div>
                            <div style="width: 1px; height: 24px; background: var(--border); margin: 0 0.5rem;"></div>
                            <div class="legend-item"><div class="legend-dot" style="background:#10b981;"></div>Sain</div>
                            <div class="legend-item"><div class="legend-dot" style="background:#38bdf8;"></div>Mineur</div>
                            <div class="legend-item"><div class="legend-dot" style="background:#f59e0b;"></div>Majeur</div>
                            <div class="legend-item"><div class="legend-dot" style="background:#ef4444;"></div>Bloquant</div>
                        </div>
                    </div>
                    <div id="calendar" style="height: 650px;"></div>
                </div>

                <!-- Charts -->
                <div class="card col-4">
                    <div class="card-header"><div class="card-title">Répartition par Criticité</div></div>
                    <div id="chart-severity" style="height: 280px;"></div>
                </div>
                
                <div class="card col-8">
                    <div class="card-header"><div class="card-title">Scores par Dimension Qualité</div></div>
                    <div id="chart-radar" style="height: 280px;"></div>
                </div>

                <!-- Table -->
                <div class="card col-12">
                    <div class="card-header"><div class="card-title">Journal des Anomalies</div></div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th style="width: 120px;">Criticité</th>
                                    <th style="width: 150px;">Dimension</th>
                                    <th style="width: 150px;">Module</th>
                                    <th>Description</th>
                                </tr>
                            </thead>
                            <tbody>
"""
    
    count = 0
    for a in anomalies:
        if count > 50: break
        
        c = a['criticite']
        if c == 'bloquant': badge_class = 'bg-red'
        elif c == 'majeur': badge_class = 'bg-yellow'
        else: badge_class = 'bg-blue'
            
        html_content += f"""
                                <tr>
                                    <td><span class="badge {badge_class}">{c.capitalize()}</span></td>
                                    <td>{a['dimension'].capitalize()}</td>
                                    <td style="font-family: monospace; font-size: 0.8rem; color: var(--text-muted);">{a['code_module']}</td>
                                    <td>{a['description']}</td>
                                </tr>
"""
        count += 1

    html_content += f"""
                            </tbody>
                        </table>
                    </div>
                </div>
                
            </div>
        </div>
    </div>

    <script>
        // Setup Charts
        const plotlyLayout = {{
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {{ color: '#6b7280', family: 'Inter, sans-serif' }},
            margin: {{ t: 10, r: 10, b: 10, l: 10 }}
        }};

        const traceSeverity = {{
            values: [{anom_bloquant}, {anom_majeur}, {anom_mineur}],
            labels: ['Bloquant', 'Majeur', 'Mineur'],
            type: 'pie',
            hole: .7,
            marker: {{ colors: ['#ef4444', '#f59e0b', '#38bdf8'] }},
            textinfo: 'none',
            hoverinfo: 'label+value+percent'
        }};
        Plotly.newPlot('chart-severity', [traceSeverity], {{...plotlyLayout, showlegend: true, legend: {{orientation: 'h', y: -0.1}}}});

        const traceRadar = {{
            type: 'scatterpolar',
            r: [
                {score_completude}, 
                {score_exactitude}, 
                {score_conformite}, 
                {score_unicite}, 
                {score_coherence}
            ],
            theta: ['Complétude', 'Exactitude', 'Séquencement', 'Unicité', 'Cohérence'],
            fill: 'toself',
            fillcolor: 'rgba(37, 99, 235, 0.2)',
            line: {{ color: '#2563eb', width: 2 }},
            marker: {{ color: '#2563eb', size: 6 }}
        }};
        const layoutRadar = {{
            ...plotlyLayout,
            polar: {{
                radialaxis: {{ visible: true, range: [0, 100], color: '#e5e7eb', tickfont: {{color: '#9ca3af'}}, gridcolor: '#f3f4f6' }},
                angularaxis: {{ color: '#e5e7eb', tickfont: {{color: '#4b5563', size: 11}}, gridcolor: '#f3f4f6' }}
            }}
        }};
        Plotly.newPlot('chart-radar', [traceRadar], layoutRadar);

        // Setup FullCalendar
        document.addEventListener('DOMContentLoaded', function() {{
            const allEvents = {fc_events_json};
            
            var calendarEl = document.getElementById('calendar');
            var calendar = new FullCalendar.Calendar(calendarEl, {{
                locale: 'fr',
                initialView: 'timeGridWeek',
                headerToolbar: {{
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,timeGridDay'
                }},
                buttonText: {{
                    today: "Aujourd'hui",
                    month: 'Mois',
                    week: 'Semaine',
                    day: 'Jour'
                }},
                initialDate: '{initial_date}',
                slotMinTime: '07:00:00',
                slotMaxTime: '20:00:00',
                allDaySlot: false,
                hiddenDays: [ 0 ], // Hide Sunday
                events: allEvents,
                eventContent: function(arg) {{
                    // Render custom HTML inside the event block
                    return {{
                        html: `
                            <div style="display: flex; flex-direction: column; gap: 2px;">
                                <div style="font-weight: 600; font-size: 0.9em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                    ${{arg.event.title}}
                                </div>
                                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.8em; opacity: 0.9;">
                                    <div style="display: flex; align-items: center; gap: 4px;">
                                        <span style="background: rgba(0,0,0,0.1); padding: 1px 4px; border-radius: 4px; font-weight: bold;">${{arg.event.extendedProps.session_type}}</span>
                                        <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${{arg.event.extendedProps.location}}</span>
                                    </div>
                                    <span style="font-weight: bold;">${{arg.event.extendedProps.promo}}</span>
                                </div>
                            </div>
                        `
                    }};
                }},
                eventClick: function(info) {{
                    // SweetAlert Beautiful Popup
                    const props = info.event.extendedProps;
                    
                    let badgeClass = 'bg-green';
                    let statusText = 'Sain';
                    if (props.criticite === 'bloquant') {{ badgeClass = 'bg-red'; statusText = 'Anomalie Bloquante'; }}
                    else if (props.criticite === 'majeur') {{ badgeClass = 'bg-yellow'; statusText = 'Anomalie Majeure'; }}
                    else if (props.criticite === 'mineur') {{ badgeClass = 'bg-blue'; statusText = 'Anomalie Mineure'; }}

                    Swal.fire({{
                        title: info.event.title,
                        html: `
                            <div style="margin-top: 1rem;">
                                <div class="event-detail-row">
                                    <div class="event-detail-label">Promo</div>
                                    <div class="event-detail-value"><b>${{props.promo}}</b></div>
                                </div>
                                <div class="event-detail-row">
                                    <div class="event-detail-label">Type de séance</div>
                                    <div class="event-detail-value"><b>${{props.session_type}}</b></div>
                                </div>
                                <div class="event-detail-row">
                                    <div class="event-detail-label">Enseignant(s)</div>
                                    <div class="event-detail-value">${{props.teachers || '<span style="color:#9ca3af;font-style:italic">Non défini</span>'}}</div>
                                </div>
                                <div class="event-detail-row">
                                    <div class="event-detail-label">Salle</div>
                                    <div class="event-detail-value">${{props.location || '<span style="color:#9ca3af;font-style:italic">Non définie</span>'}}</div>
                                </div>
                                <div class="event-detail-row">
                                    <div class="event-detail-label">État de l'audit</div>
                                    <div class="event-detail-value"><span class="badge ${{badgeClass}}">${{statusText}}</span></div>
                                </div>
                                <div class="event-detail-row">
                                    <div class="event-detail-label">Horaire</div>
                                    <div class="event-detail-value">${{info.event.start.toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}})}} - ${{info.event.end.toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}})}}</div>
                                </div>
                            </div>
                        `,
                        confirmButtonText: 'Fermer',
                        confirmButtonColor: '#2563eb',
                        width: 500,
                        padding: '2rem'
                    }});
                }}
            }});
            calendar.render();
            
            // Filter Logic
            function applyFilters() {{
                const promo = document.getElementById('promoFilter').value;
                const status = document.getElementById('statusFilter').value;
                
                const filtered = allEvents.filter(e => {{
                    // Filter by Promo
                    if (promo !== 'ALL' && e.extendedProps.promo !== promo) return false;
                    
                    // Filter by Status (Anomalies only = bloquant or majeur)
                    if (status === 'ANOMALIES') {{
                        if (e.extendedProps.criticite === 'normal' || e.extendedProps.criticite === 'mineur') return false;
                    }}
                    
                    return true;
                }});
                
                calendar.removeAllEventSources();
                calendar.addEventSource(filtered);
            }}
            
            document.getElementById('promoFilter').addEventListener('change', applyFilters);
            document.getElementById('statusFilter').addEventListener('change', applyFilters);
        }});
    </script>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Dashboard HTML généré avec succès dans : {output_path}")

if __name__ == "__main__":
    import sys
    data_dir = Path("output")
    json_path = data_dir / "audit_report.json"
    out_path = data_dir / "dashboard_premium.html"
    if not json_path.exists():
        print("Erreur : Le fichier audit_report.json n'existe pas.")
        sys.exit(1)
    generate_html_dashboard(json_path, out_path)
