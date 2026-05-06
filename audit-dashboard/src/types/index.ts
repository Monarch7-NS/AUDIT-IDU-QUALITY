export interface Anomaly {
  dimension: string;
  code_module: string;
  description: string;
  criticite: 'bloquant' | 'majeur' | 'mineur';
}

export interface Event {
  title: string;
  code: string;
  session_type: string;
  start: string;
  end: string;
  duration_h: number;
  location: string;
  teachers: string[];
  groups: string[];
  promo: string;
  description: string;
}

export interface Scores {
  global: number;
  completude: number;
  exactitude: number;
  conformite: number;
  unicite: number;
  coherence: number;
}

export interface Summary {
  total_anomalies: number;
  bloquant: number;
  majeur: number;
  mineur: number;
  global_score: number;
}

export interface AuditReport {
  generated_at: string;
  summary: Summary;
  scores: Scores;
  anomalies: Anomaly[];
  events: Event[];
}

export interface HoursRow {
  module: string;
  type: string;
  maquette: number;
  ade: number;
  ecart: number;
}

export interface Dependance {
  module_precedent: string;
  type_precedent: string;
  numero_precedent: string;
  module_suivant: string;
  type_suivant: string;
  numero_suivant: string;
}
