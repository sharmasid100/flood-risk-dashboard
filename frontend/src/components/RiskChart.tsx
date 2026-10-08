import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ForecastPoint } from '../lib/api'

export default function RiskChart({ points }: { points: ForecastPoint[] }) {
  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
          <defs>
            <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#d87542" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#d87542" stopOpacity={0.015} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e5e8dd" vertical={false} strokeDasharray="3 5" />
          <XAxis dataKey="minute" tickFormatter={value => value === 0 ? 'NOW' : `+${value}m`} tickLine={false} axisLine={false} tick={{ fill: '#7b8275', fontSize: 10 }} />
          <YAxis domain={[0, 100]} ticks={[0, 50, 100]} tickLine={false} axisLine={false} tick={{ fill: '#7b8275', fontSize: 10 }} />
          <Tooltip formatter={(value: number) => [`${value} / 100`, 'Risk score']} labelFormatter={value => value === 0 ? 'Current' : `In ${value} minutes`} />
          <Area type="monotone" dataKey="risk_score" stroke="#c96838" strokeWidth={2.5} fill="url(#riskFill)" activeDot={{ r: 4, fill: '#c96838' }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}