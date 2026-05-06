"use client";

import { useRef, useState, useMemo } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin from "@fullcalendar/interaction";
import { EventClickArg } from "@fullcalendar/core";
import { Event, Anomaly } from "@/types";
import { Card, CardContent } from "@/components/ui/card";

interface Props { events: Event[]; anomalies: Anomaly[]; }

const CRIT_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  bloquant: { bg: "#fee2e2", border: "#ef4444", text: "#991b1b" },
  majeur:   { bg: "#fef3c7", border: "#f59e0b", text: "#92400e" },
  mineur:   { bg: "#e0f2fe", border: "#38bdf8", text: "#075985" },
  normal:   { bg: "#d1fae5", border: "#10b981", text: "#065f46" },
};

interface EventDetail {
  title: string;
  promo: string;
  session_type: string;
  teachers: string[];
  location: string;
  criticite: string;
  start: string;
  end: string;
}

export default function AgendaView({ events, anomalies }: Props) {
  const calRef = useRef<FullCalendar>(null);
  const [promoFilter, setPromoFilter]   = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [detail, setDetail]             = useState<EventDetail | null>(null);

  // Build module → criticite map
  const modCrit = useMemo(() => {
    const m: Record<string, string> = {};
    anomalies.forEach(a => {
      if (!a.code_module) return;
      const cur = m[a.code_module];
      const order = ["bloquant", "majeur", "mineur"];
      if (!cur || order.indexOf(a.criticite) < order.indexOf(cur)) {
        m[a.code_module] = a.criticite;
      }
    });
    return m;
  }, [anomalies]);

  const fcEvents = useMemo(() =>
    events
      .filter(e => promoFilter === "ALL" || e.promo === promoFilter)
      .map(e => {
        const crit = modCrit[e.code] || "normal";
        if (statusFilter === "ANOMALIES" && (crit === "normal" || crit === "mineur")) return null;
        const s = CRIT_STYLES[crit];
        return {
          title: e.title,
          start: e.start,
          end: e.end,
          backgroundColor: s.bg,
          borderColor: s.border,
          textColor: s.text,
          extendedProps: {
            promo: e.promo,
            session_type: e.session_type,
            teachers: e.teachers,
            location: e.location,
            criticite: crit,
          },
        };
      })
      .filter(Boolean),
    [events, modCrit, promoFilter, statusFilter]
  );

  const handleEventClick = (info: EventClickArg) => {
    const p = info.event.extendedProps;
    setDetail({
      title: info.event.title,
      promo: p.promo,
      session_type: p.session_type,
      teachers: p.teachers,
      location: p.location,
      criticite: p.criticite,
      start: info.event.start?.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) || "",
      end: info.event.end?.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) || "",
    });
  };

  const BADGE: Record<string, string> = {
    bloquant: "bg-red-100 text-red-700",
    majeur:   "bg-amber-100 text-amber-700",
    mineur:   "bg-sky-100 text-sky-700",
    normal:   "bg-emerald-100 text-emerald-700",
  };
  const LABEL: Record<string, string> = { bloquant: "Bloquant", majeur: "Majeur", mineur: "Mineur", normal: "Sain" };

  return (
    <div className="space-y-5">
      {/* Controls */}
      <Card className="border-slate-100 shadow-none">
      <CardContent className="p-4">
        <div className="flex flex-wrap items-center gap-5">
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-500">Promotion :</label>
            <select
              value={promoFilter}
              onChange={e => setPromoFilter(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">Toutes les promos</option>
              <option value="IDU3">IDU 3</option>
              <option value="IDU4">IDU 4</option>
              <option value="IDU5">IDU 5</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-500">Afficher :</label>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">Tous les cours</option>
              <option value="ANOMALIES">Anomalies uniquement</option>
            </select>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {[
              { key: "normal",   label: "Sain",    color: "#10b981" },
              { key: "mineur",   label: "Mineur",  color: "#38bdf8" },
              { key: "majeur",   label: "Majeur",  color: "#f59e0b" },
              { key: "bloquant", label: "Bloquant",color: "#ef4444" },
            ].map(l => (
              <div key={l.key} className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full" style={{ background: l.color }} />
                <span className="text-xs text-slate-500">{l.label}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
      </Card>

      <div className="grid grid-cols-3 gap-5">
        {/* Calendar */}
        <div className="col-span-2 bg-white rounded-xl border border-slate-100 p-5">
          <FullCalendar
            ref={calRef}
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
            locale="fr"
            initialView="timeGridWeek"
            headerToolbar={{
              left: "prev,next today",
              center: "title",
              right: "dayGridMonth,timeGridWeek,timeGridDay",
            }}
            buttonText={{ today: "Aujourd'hui", month: "Mois", week: "Semaine", day: "Jour" }}
            initialDate="2025-09-01"
            slotMinTime="07:30:00"
            slotMaxTime="20:00:00"
            allDaySlot={false}
            hiddenDays={[0]}
            height={580}
            events={fcEvents as []}
            eventClick={handleEventClick}
            eventContent={arg => ({
              html: `
                <div style="padding:2px 4px;overflow:hidden;height:100%">
                  <div style="font-weight:600;font-size:0.78em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${arg.event.title}</div>
                  <div style="font-size:0.72em;opacity:0.8">${arg.event.extendedProps.session_type} · ${arg.event.extendedProps.location || "—"}</div>
                </div>
              `,
            })}
          />
        </div>

        {/* Detail panel */}
        <div className="col-span-1">
          {detail ? (
            <div className="bg-white rounded-xl border border-slate-100 p-5 space-y-4 sticky top-4">
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-slate-900 text-sm leading-snug flex-1 pr-2">{detail.title}</h3>
                <button onClick={() => setDetail(null)} className="text-slate-400 hover:text-slate-600 text-lg leading-none">×</button>
              </div>
              <div className="space-y-3">
                {[
                  { label: "Promotion",     value: detail.promo },
                  { label: "Type de séance",value: detail.session_type },
                  { label: "Horaire",       value: `${detail.start} – ${detail.end}` },
                  { label: "Salle",         value: detail.location || "Non définie" },
                  { label: "Enseignant(s)", value: detail.teachers?.join(", ") || "Non défini" },
                ].map(row => (
                  <div key={row.label} className="flex gap-3 py-2.5 border-b border-slate-50 last:border-0">
                    <span className="text-xs text-slate-400 w-28 shrink-0">{row.label}</span>
                    <span className="text-xs font-medium text-slate-700">{row.value}</span>
                  </div>
                ))}
                <div className="flex gap-3 py-2.5">
                  <span className="text-xs text-slate-400 w-28 shrink-0">État audit</span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${BADGE[detail.criticite]}`}>
                    {LABEL[detail.criticite]}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-dashed border-slate-200 p-8 text-center h-full flex flex-col items-center justify-center gap-2">
              <div className="h-10 w-10 rounded-full bg-slate-50 flex items-center justify-center text-slate-300 mb-1">
                <svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="1" y="2" width="14" height="13" rx="2"/><path d="M5 1v2M11 1v2M1 6h14"/>
                </svg>
              </div>
              <p className="text-sm text-slate-400">Cliquez sur un cours dans le calendrier pour voir ses détails.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
