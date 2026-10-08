const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '')
const SIMULATION_ID_KEY = 'drainmind-simulation-id'
const SIMULATION_REVISION_KEY = 'drainmind-simulation-revision'

function simulationId(): string {
  let id = localStorage.getItem(SIMULATION_ID_KEY)
  if (!id) {
    id = globalThis.crypto?.randomUUID?.() ?? `demo-${Math.random().toString(36).slice(2)}`
    localStorage.setItem(SIMULATION_ID_KEY, id)
  }
  return id
}

function nextSimulationRevision(): string {
  const revision = Number(localStorage.getItem(SIMULATION_REVISION_KEY) ?? 0) + 1
  localStorage.setItem(SIMULATION_REVISION_KEY, String(revision))
  return String(revision)
}

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'
export type InterventionId = 'clear_drain' | 'deploy_pump' | 'restrict_traffic' | 'emergency_warning' | 'open_water_storage'

export interface Area {
  area_id: string
  name: string
  x: number
  y: number
  elevation_m: number
  drain_capacity_mm_hr: number
  impervious_surface_pct: number
  drainage_score: number
  historical_flood_frequency: number
  population: number
  near_major_road: boolean
}

export interface RiskArea extends Area {
  risk_score: number
  risk_level: RiskLevel
  rainfall_mm_hr: number
  severity: number
  time_to_flood_minutes: number
  factors: Record<string, number>
}

export interface ForecastPoint {
  minute: number
  rainfall_mm_hr: number
  risk_score: number
  risk_level: RiskLevel
}

export interface Recommendation {
  id: InterventionId
  label: string
  reason: string
}

export interface Simulation {
  intervention: InterventionId
  label: string
  simulation_only: boolean
  before: { risk_score: number; risk_level: RiskLevel; severity: number; time_to_flood_minutes: number }
  after: { risk_score: number; risk_level: RiskLevel; severity: number; time_to_flood_minutes: number }
  impact: { risk_reduction_pct: number; severity_reduction_pct: number; extra_warning_time_minutes: number; exposure_reduction_pct: number }
  notification?: { mode: string; sent: boolean; message: string }
}

export interface DashboardSummary {
  city: string
  data_label: string
  rainfall_mm_hr: number
  area_count: number
  high_risk_areas: number
  critical_areas: number
  next_event: { area_id: string; area_name: string; minutes: number } | null
  population_at_risk: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-Simulation-Id': simulationId(), ...init?.headers },
  })
  if (!response.ok) throw new Error(`DrainMind API error (${response.status})`)
  return response.json() as Promise<T>
}

export const api = {
  risk: () => request<{ city: string; rainfall_mm_hr: number; data_label: string; areas: RiskArea[] }>('/api/risk'),
  summary: () => request<DashboardSummary>('/api/dashboard/summary'),
  forecast: (areaId: string) => request<{ forecast: ForecastPoint[] }>(`/api/forecast/${areaId}`),
  recommendations: (areaId: string) => request<{ recommendations: Recommendation[] }>(`/api/recommendations/${areaId}`),
  setRainfall: (rainfall: number) => {
    const revision = nextSimulationRevision()
    return request<{ areas: RiskArea[] }>('/api/simulate/rainfall', {
      method: 'POST',
      headers: { 'X-Simulation-Revision': revision },
      body: JSON.stringify({ rainfall_mm_hr: rainfall }),
    })
  },
  simulate: (areaId: string, intervention: InterventionId) => request<Simulation>('/api/intervention/simulate', {
    method: 'POST',
    body: JSON.stringify({ area_id: areaId, intervention }),
  }),
}