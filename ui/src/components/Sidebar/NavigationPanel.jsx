import React from 'react'

export default function NavigationPanel({ navData = null }) {
  if (!navData || (navData.latitude == null && navData.depth == null)) {
    return (
      <div className="sb-controls sb-nav-controls">
        <div style={{ padding: '8px 4px', color: '#64748b', fontSize: '9.5px', fontFamily: 'var(--font-mono)' }}>
          <div style={{ color: '#94a3b8', fontWeight: 700, marginBottom: '4px' }}>TELEMETRY UNAVAILABLE</div>
          <div>Image formats do not carry NMEA GPS or towfish altitude pings. Load raw .XTF or .JSF logs for georeferencing.</div>
        </div>
      </div>
    )
  }

  const fields = [
    { label: 'Latitude:',  value: navData.latitude != null ? `${Number(navData.latitude).toFixed(5)}° N` : 'Not provided' },
    { label: 'Longitude:', value: navData.longitude != null ? `${Math.abs(Number(navData.longitude)).toFixed(5)}° W` : 'Not provided' },
    { label: 'Heading:',   value: navData.heading != null ? `${Number(navData.heading).toFixed(1)}°` : 'Not provided' },
    { label: 'Depth:',     value: navData.depth != null ? `${Number(navData.depth).toFixed(1)} m` : 'Not provided' },
    { label: 'Altitude:',  value: navData.altitude != null ? `${Number(navData.altitude).toFixed(1)} m` : 'Not provided' },
  ]

  return (
    <div className="sb-controls sb-nav-controls">
      {fields.map(({ label, value }) => (
        <div key={label} className="sb-row sb-row--between sb-nav-row">
          <span className="sb-label sb-label--nav">{label}</span>
          <span className="sb-value sb-value--mono">{value}</span>
        </div>
      ))}
    </div>
  )
}

