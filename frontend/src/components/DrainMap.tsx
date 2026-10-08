import { useMemo } from 'react'
import L from 'leaflet'
import { CircleMarker, MapContainer, Polygon, Polyline, Tooltip, ZoomControl } from 'react-leaflet'
import type { RiskArea } from '../lib/api'

interface DrainMapProps {
  areas: RiskArea[]
  selectedId: string | null
  onSelect: (areaId: string) => void
}

const riskColors = {
  LOW: '#3d8567',
  MODERATE: '#bd9a37',
  HIGH: '#d87542',
  CRITICAL: '#bf4c49',
}

function polygonFor(area: RiskArea, index: number): [number, number][] {
  const radius = 19 + (index % 4) * 2
  const points = [[-1, -0.7], [-0.12, -1], [0.9, -0.68], [1, 0.22], [0.42, 1], [-0.72, 0.78]]
  return points.map(([x, y]) => [area.y + y * radius, area.x + x * radius])
}

export default function DrainMap({ areas, selectedId, onSelect }: DrainMapProps) {
  const bounds = useMemo(() => L.latLngBounds([[-40, -40], [930, 930]]), [])
  const roads = [
    [[70, 90], [245, 265], [380, 300], [550, 475], [760, 510], [920, 800]],
    [[80, 795], [250, 710], [420, 620], [590, 490], [760, 300], [900, 185]],
    [[180, 40], [190, 300], [405, 450], [590, 660], [850, 820]],
  ] as [number, number][][]
  const river = [[70, 560], [210, 500], [330, 520], [435, 455], [570, 475], [680, 400], [900, 430]] as [number, number][]

  return (
    <MapContainer
      className="city-map"
      crs={L.CRS.Simple}
      bounds={bounds}
      maxBounds={bounds.pad(0.05)}
      maxBoundsViscosity={0.85}
      minZoom={-0.85}
      maxZoom={1.2}
      zoomControl={false}
      attributionControl={false}
      scrollWheelZoom
    >
      <ZoomControl position="bottomright" />
      <Polyline positions={river} pathOptions={{ color: '#90b8ae', weight: 34, opacity: 0.5, lineCap: 'round' }} />
      <Polyline positions={river} pathOptions={{ color: '#b7d0c5', weight: 2, opacity: 0.85, dashArray: '5 8' }} />
      {roads.map((road, index) => <Polyline key={index} positions={road} pathOptions={{ color: '#d5d0bc', weight: 7, opacity: 0.72, lineCap: 'round' }} />)}
      {areas.map((area, index) => {
        const color = riskColors[area.risk_level]
        const selected = area.area_id === selectedId
        return (
          <Polygon
            key={area.area_id}
            positions={polygonFor(area, index)}
            pathOptions={{ color, fillColor: color, fillOpacity: selected ? 0.36 : area.risk_level === 'LOW' ? 0.12 : 0.22, weight: selected ? 2.5 : 1.4 }}
            eventHandlers={{ click: () => onSelect(area.area_id) }}
          >
            <Tooltip permanent direction="center" className={`map-label ${selected ? 'map-label-selected' : ''}`}>
              <span>{area.name}</span>
              <b>{area.risk_score}</b>
            </Tooltip>
          </Polygon>
        )
      })}
      {areas.map(area => (
        <CircleMarker
          key={`${area.area_id}-point`}
          center={[area.y, area.x]}
          radius={area.area_id === selectedId ? 5 : 3.5}
          pathOptions={{ color: '#fffdf7', weight: 1.5, fillColor: riskColors[area.risk_level], fillOpacity: 1 }}
          eventHandlers={{ click: () => onSelect(area.area_id) }}
        />
      ))}
    </MapContainer>
  )
}