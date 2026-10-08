import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, BellRing, CloudRain, Droplets, Info, LoaderCircle, MapPin, Radio, ShieldCheck, Waves, Wind } from 'lucide-react'
import DrainMap from './components/DrainMap'
import RiskChart from './components/RiskChart'
import { api } from './lib/api'
import type { DashboardSummary, ForecastPoint, InterventionId, Recommendation, RiskArea, Simulation } from './lib/api'

const interventions: { id: InterventionId; label: string; icon: typeof Droplets }[] = [
  { id: 'clear_drain', label: 'Clear drain', icon: Droplets },
  { id: 'deploy_pump', label: 'Deploy pump', icon: Waves },
  { id: 'restrict_traffic', label: 'Restrict traffic', icon: Wind },
  { id: 'open_water_storage', label: 'Open storage', icon: Activity },
  { id: 'emergency_warning', label: 'Issue warning', icon: BellRing },
]

const factorLabels: Record<string, string> = {
  rainfall: 'Rainfall intensity',
  drainage: 'Drainage stress',
  elevation: 'Low elevation',
  impervious: 'Urban surface',
  historical: 'Flood history',
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('en-US').format(value)
}

export default function App() {
  const [areas, setAreas] = useState<RiskArea[]>([])
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [rainfall, setRainfall] = useState(25)
  const [forecast, setForecast] = useState<ForecastPoint[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [simulation, setSimulation] = useState<Simulation | null>(null)
  const [pending, setPending] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const rainfallRequestId = useRef(0)

  useEffect(() => {
    let active = true
    Promise.all([api.risk(), api.summary()])
      .then(([risk, dashboard]) => {
        if (!active) return
        setAreas(risk.areas)
        setRainfall(risk.rainfall_mm_hr)
        setSummary(dashboard)
        const priority = [...risk.areas].sort((a, b) => b.risk_score - a.risk_score)[0]
        setSelectedId(priority?.area_id ?? null)
        setLoading(false)
      })
      .catch(() => {
        if (!active) return
        setError('The prediction service is unavailable. Start the FastAPI backend to load the synthetic city.')
        setLoading(false)
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!selectedId) return
    let active = true
    Promise.all([api.forecast(selectedId), api.recommendations(selectedId)])
      .then(([forecastResult, recommendationResult]) => {
        if (!active) return
        setForecast(forecastResult.forecast)
        setRecommendations(recommendationResult.recommendations)
      })
      .catch(() => active && setError('Could not refresh area forecast.'))
    setSimulation(null)
    return () => { active = false }
  }, [selectedId])

  useEffect(() => {
    if (loading) return
    const requestId = ++rainfallRequestId.current
    const timer = window.setTimeout(() => {
      api.setRainfall(rainfall)
        .then(async response => {
          if (requestId !== rainfallRequestId.current) return
          setAreas(response.areas)
          const dashboard = await api.summary()
          if (requestId !== rainfallRequestId.current) return
          setSummary(dashboard)
          if (selectedId) {
            const [forecastResult, recommendationResult] = await Promise.all([
              api.forecast(selectedId),
              api.recommendations(selectedId),
            ])
            if (requestId !== rainfallRequestId.current) return
            setForecast(forecastResult.forecast)
            setRecommendations(recommendationResult.recommendations)
          }
          setError('')
        })
        .catch(() => {
          if (requestId === rainfallRequestId.current) setError('Rainfall update failed. Check the API connection.')
        })
    }, 120)
    return () => window.clearTimeout(timer)
  }, [rainfall, loading, selectedId])

  const selected = areas.find(area => area.area_id === selectedId) ?? null
  const critical = areas.filter(area => area.risk_level === 'CRITICAL').length
  const urgent = selected?.risk_level === 'CRITICAL'

  async function runIntervention(intervention: InterventionId) {
    if (!selectedId) return
    setPending(true)
    setError('')
    try {
      setSimulation(await api.simulate(selectedId, intervention))
    } catch {
      setError('The intervention simulation could not be completed.')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="DrainMind home">
          <span className="brand-mark"><Waves size={20} strokeWidth={2.2} /></span>
          <span className="brand-type"><strong>DRAINMIND</strong><small>URBAN FLOOD INTELLIGENCE</small></span>
        </a>
        <div className="header-meta">
          <span className="cloud-status"><span className="status-dot" /> DEMO SYSTEM ONLINE</span>
          <span className="header-divider" />
          <span className="data-tag"><Info size={13} /> SYNTHETIC MODEL</span>
        </div>
      </header>

      <section className="intro-row" id="top">
        <div>
          <p className="eyebrow"><MapPin size={13} /> FICTIONAL DEMO CITY <span>/</span> {summary?.city ?? 'VERDANTIA'}</p>
          <h1>Read the rain <em>before the street.</em></h1>
        </div>
        <p className="intro-note">A transparent flood-risk simulation for earlier, better-informed city response.</p>
      </section>

      {error && <div className="error-banner" role="alert"><AlertTriangle size={16} /> {error}</div>}

      {urgent && selected && (
        <div className="alert-strip" role="status">
          <span className="alert-icon"><AlertTriangle size={17} /></span>
          <span><strong>Critical risk predicted</strong> {selected.name} may experience severe waterlogging in ~{selected.time_to_flood_minutes} min.</span>
          <button onClick={() => runIntervention('emergency_warning')} disabled={pending}><BellRing size={15} /> Issue local warning</button>
        </div>
      )}

      <section className="stat-row" aria-label="City overview">
        <article className="stat-block"><div className="stat-label"><span className="stat-dot dot-orange" /> HIGH-RISK AREAS</div><strong>{summary?.high_risk_areas ?? '—'}<small> / {summary?.area_count ?? 30}</small></strong><span className="stat-foot">High + critical, modeled</span></article>
        <article className="stat-block"><div className="stat-label"><span className="stat-dot dot-red" /> CRITICAL AREAS</div><strong>{critical}<small> locations</small></strong><span className="stat-foot">Immediate attention threshold</span></article>
        <article className="stat-block"><div className="stat-label"><span className="stat-dot dot-blue" /> NEXT FLOOD EVENT</div><strong>{summary?.next_event?.minutes ?? '—'}<small>{summary?.next_event ? ' min' : ''}</small></strong><span className="stat-foot">{summary?.next_event?.area_name ?? 'No high-risk event'}</span></article>
        <article className="stat-block"><div className="stat-label"><span className="stat-dot dot-green" /> PEOPLE POTENTIALLY AFFECTED</div><strong>{summary ? formatNumber(summary.population_at_risk) : '—'}</strong><span className="stat-foot">Population within high-risk zones</span></article>
      </section>

      <section className="workspace-grid">
        <div className="map-column">
          <div className="section-heading map-heading">
            <div><p className="eyebrow">LIVE RISK SURFACE</p><h2>Neighborhood overview</h2></div>
            <div className="map-tools"><span><span className="mini-pulse" /> {areas.length} areas monitored</span><span className="map-north">N <ArrowUpRight size={12} /></span></div>
          </div>
          <div className="map-frame">
            <div className="map-caption"><span>VERDANTIA <i>/</i> DISTRICT GRID</span><span>SCHEMATIC · NOT TO SCALE</span></div>
            {loading ? <div className="map-loading"><LoaderCircle className="spin" size={22} /> Building the city model</div> : (
              <DrainMap areas={areas} selectedId={selectedId} onSelect={setSelectedId} />
            )}
            <div className="map-legend" aria-label="Risk map legend">
              <span><i className="legend-low" /> Low</span><span><i className="legend-moderate" /> Moderate</span><span><i className="legend-high" /> High</span><span><i className="legend-critical" /> Critical</span>
            </div>
            <div className="map-scale"><span /> 1 district unit</div>
          </div>
          <div className="rain-control">
            <div className="rain-control-head"><div><p className="eyebrow"><CloudRain size={13} /> SCENARIO CONTROLS</p><h3>Simulate rainfall</h3></div><strong className="rain-value">{rainfall}<small> mm/hr</small></strong></div>
            <input aria-label="Simulated rainfall in millimeters per hour" type="range" min="0" max="100" step="1" value={rainfall} onChange={event => setRainfall(Number(event.target.value))} style={{ '--range-progress': `${rainfall}%` } as CSSProperties} />
            <div className="range-labels"><span>DRIZZLE <b>0</b></span><span>HEAVY <b>50</b></span><span>EXTREME <b>100 mm/hr</b></span></div>
          </div>
        </div>

        <aside className="detail-column">
          <section className="detail-section area-section">
            <div className="section-heading compact-heading"><div><p className="eyebrow">SELECTED DISTRICT</p><h2>{selected?.name ?? (loading ? 'Loading area…' : 'Select an area')}</h2></div><span className={`risk-chip ${selected?.risk_level.toLowerCase() ?? 'low'}`}>{selected?.risk_level ?? '—'}</span></div>
            <div className="risk-score-row"><div><span className="eyebrow">FLOOD RISK SCORE</span><div className="risk-number">{selected?.risk_score ?? '—'}<small> / 100</small></div></div><div className="time-to-flood"><span className="time-icon"><CloudRain size={17} /></span><span><b>~{selected?.time_to_flood_minutes ?? '—'} min</b><small>time to waterlogging</small></span></div></div>
            <div className="area-metrics"><div><span>RAINFALL</span><b>{selected?.rainfall_mm_hr ?? rainfall}<small> mm/hr</small></b></div><div><span>DRAIN CAPACITY</span><b>{selected?.drain_capacity_mm_hr ?? '—'}<small> mm/hr</small></b></div><div><span>ELEVATION</span><b>{selected?.elevation_m ?? '—'}<small> m</small></b></div></div>
            <div className="factors-block"><div className="eyebrow">RISK DRIVERS <Info size={12} /></div>{selected && Object.entries(selected.factors).map(([key, value]) => <div className="factor-row" key={key}><span>{factorLabels[key] ?? key}</span><span className="factor-track"><i style={{ width: `${Math.round(value * 100)}%` }} /></span><b>{Math.round(value * 100)}</b></div>)}</div>
          </section>

          <section className="detail-section forecast-section">
            <div className="section-heading compact-heading"><div><p className="eyebrow">AREA FORECAST</p><h3>Next 60 minutes</h3></div><span className="chart-unit">RISK / 100</span></div>
            <RiskChart points={forecast} />
            <div className="timeline-list">{forecast.slice(1).map(point => <span key={point.minute}><i className={`timeline-dot ${point.risk_level.toLowerCase()}`} /><b>+{point.minute}m</b><small>{point.risk_level.toLowerCase()}</small></span>)}</div>
          </section>

          <section className="detail-section recommendations-section">
            <div className="section-heading compact-heading"><div><p className="eyebrow">RESPONSE GUIDANCE</p><h3>Act on this forecast</h3></div><ShieldCheck size={17} className="guidance-icon" /></div>
            <div className="recommendation-list">{recommendations.map((item, index) => <div className="recommendation" key={item.id}><span className="rec-index">0{index + 1}</span><span><b>{item.label}</b><small>{item.reason}</small></span><ArrowDownRight size={14} /></div>)}</div>
          </section>
        </aside>
      </section>

      <section className="intervention-section">
        <div className="intervention-top"><div><p className="eyebrow">DECISION SUPPORT <span>/</span> MODELED, NOT OPERATIONAL</p><h2>What could change the outcome?</h2></div><span className="simulation-badge"><Activity size={13} /> SIMULATION ONLY</span></div>
        <div className="intervention-layout">
          <div className="intervention-choice"><p className="choice-label">CHOOSE AN INTERVENTION</p><div className="intervention-buttons">{interventions.map(({ id, label, icon: Icon }) => <button className={simulation?.intervention === id ? 'active' : ''} key={id} onClick={() => runIntervention(id)} disabled={!selected || pending}><Icon size={15} /><span>{label}</span></button>)}</div><p className="intervention-footnote"><Info size={13} /> Modeled effects are illustrative and are not field-validated.</p></div>
          <div className="comparison"><div className="comparison-side"><span className="comparison-label">CURRENT PREDICTED SEVERITY</span><div className="severity-line"><i style={{ width: `${simulation?.before.severity ?? selected?.severity ?? 0}%` }} /><b>{simulation?.before.severity ?? selected?.severity ?? '—'}<small>%</small></b></div><small>Risk score {simulation?.before.risk_score ?? selected?.risk_score ?? '—'} / 100</small></div><div className="comparison-arrow"><ArrowDownRight size={19} /></div><div className="comparison-side after-side"><span className="comparison-label">AFTER SIMULATED ACTION</span><div className="severity-line"><i style={{ width: `${simulation?.after.severity ?? selected?.severity ?? 0}%` }} /><b>{simulation?.after.severity ?? selected?.severity ?? '—'}<small>%</small></b></div><small>{simulation ? `Risk score ${simulation.after.risk_score} / 100` : 'Choose an action to compare'}</small></div><div className="impact-result"><strong>{simulation ? `${simulation.impact.severity_reduction_pct}%` : '—'}</strong><span>severity reduction</span><b>+{simulation?.impact.extra_warning_time_minutes ?? 0} min warning time</b></div></div>
        </div>
        {pending && <div className="simulation-status"><LoaderCircle size={14} className="spin" /> Recalculating scenario…</div>}
        {simulation?.notification && <div className="local-notice"><BellRing size={14} /> {simulation.notification.message}</div>}
      </section>

      <footer className="footer-note"><span><Radio size={13} /> DRAINMIND <b>DEMO MODE</b></span><span>Rule-based model · Synthetic data · No live sensors or alerts</span><span>Rainfall {rainfall} mm/hr</span></footer>
    </main>
  )
}