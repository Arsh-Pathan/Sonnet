import React, { useMemo } from 'react'
import './AnalyticsPanel.css'

export default function AnalyticsPanel({ detections = [] }) {
  const total = detections.length

  // 1. Classification Breakdown
  const summaryMap = useMemo(() => {
    return detections.reduce((acc, det) => {
      const rawName = det.class_name || det.type || det.class || 'unknown'
      const formattedName = rawName.replace(/_/g, ' ').toUpperCase()
      acc[formattedName] = (acc[formattedName] || 0) + 1
      return acc
    }, {})
  }, [detections])

  // 2. Verification breakdown
  const confirmedCount = useMemo(() => detections.filter(
    d => d.status === 'Operator accepted' || d.status === 'Confirmed'
  ).length, [detections])

  const pendingCount = useMemo(() => detections.filter(
    d => d.status === 'Pending Review' || d.status === 'Flagged'
  ).length, [detections])

  const fpCount = useMemo(() => detections.filter(
    d => d.status === 'False Positive'
  ).length, [detections])

  const unreviewedCount = Math.max(0, total - confirmedCount - pendingCount - fpCount)

  // 3. Average & Spectrum of Confidence
  const avgConfidence = total
    ? detections.reduce((sum, det) => sum + (det.confidence ?? det.modelScore ?? 0), 0) / total
    : 0

  const confidencePercent = (avgConfidence * 100).toFixed(1)

  const confidenceBins = useMemo(() => {
    const bins = {
      high: 0,     // 70% - 100%
      modHigh: 0,  // 50% - 70%
      mod: 0,      // 30% - 50%
      low: 0,      // 15% - 30%
    }
    detections.forEach(d => {
      const score = Number(d.confidence ?? d.modelScore ?? 0)
      if (score >= 0.7) bins.high += 1
      else if (score >= 0.5) bins.modHigh += 1
      else if (score >= 0.3) bins.mod += 1
      else bins.low += 1
    })
    return bins
  }, [detections])

  // 4. Swath Distribution (Port vs. Starboard)
  const swathStats = useMemo(() => {
    let port = 0
    let starboard = 0
    detections.forEach(d => {
      const ch = (d.roi || d.side || (d.bbox?.x < 0.5 ? 'port' : 'starboard')).toLowerCase()
      if (ch === 'port') port += 1
      else starboard += 1
    })
    const portPct = total ? Math.round((port / total) * 100) : 50
    const stbdPct = total ? 100 - portPct : 50
    return { port, starboard, portPct, stbdPct }
  }, [detections, total])

  // 5. Acoustic Footprint / Size Profile
  const sizeBins = useMemo(() => {
    const sizes = { small: 0, medium: 0, large: 0 }
    detections.forEach(d => {
      const area = (d.bbox?.w ?? 0.05) * (d.bbox?.h ?? 0.05)
      if (area < 0.005) sizes.small += 1
      else if (area < 0.02) sizes.medium += 1
      else sizes.large += 1
    })
    return sizes
  }, [detections])

  // Review Completion Rate
  const reviewedTotal = confirmedCount + pendingCount + fpCount
  const reviewCompletionPct = total ? Math.round((reviewedTotal / total) * 100) : 0

  return (
    <div className="analytics-view">
      <div className="analytics-header">
        <h2 className="analytics-header__title">HYDROGRAPHIC ACOUSTIC INTELLIGENCE &amp; SURVEY ANALYTICS</h2>
        <span className="analytics-header__badge">{total} Detections In Active Scan</span>
      </div>

      {/* KPI Cards */}
      <div className="analytics-grid">
        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">TOTAL TARGETS</span>
          <span className="analytics-kpi-val analytics-kpi-val--blue">{total}</span>
          <span className="analytics-kpi-sub">Across 200m acoustic swath</span>
        </div>

        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">OPERATOR VERIFIED</span>
          <span className="analytics-kpi-val analytics-kpi-val--green">{confirmedCount}</span>
          <span className="analytics-kpi-sub">
            {total ? `${Math.round((confirmedCount / total) * 100)}% validated contacts` : '0%'}
          </span>
        </div>

        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">FLAGGED FOR AUDIT</span>
          <span className="analytics-kpi-val analytics-kpi-val--amber">{pendingCount}</span>
          <span className="analytics-kpi-sub">Secondary review required</span>
        </div>

        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">AVG MODEL CONFIDENCE</span>
          <span className="analytics-kpi-val">{confidencePercent}%</span>
          <span className="analytics-kpi-sub">YOLOv11s inference score</span>
        </div>
      </div>

      {/* Two Column Layout: Swath Distribution & Operator Audit Progress */}
      <div className="analytics-dual-grid">
        {/* Swath Channel Distribution */}
        <div className="analytics-card">
          <h3 className="analytics-card__title">SWATH CHANNEL DISTRIBUTION (PORT VS. STARBOARD)</h3>
          <div className="analytics-swath-summary">
            <div className="analytics-swath-col">
              <span className="analytics-swath-name">PORT CHANNEL</span>
              <span className="analytics-swath-count">{swathStats.port} targets ({swathStats.portPct}%)</span>
              <span className="analytics-swath-desc">-100m to 0m nadir range</span>
            </div>
            <div className="analytics-swath-col analytics-swath-col--stbd">
              <span className="analytics-swath-name">STARBOARD CHANNEL</span>
              <span className="analytics-swath-count">{swathStats.starboard} targets ({swathStats.stbdPct}%)</span>
              <span className="analytics-swath-desc">0m to +100m nadir range</span>
            </div>
          </div>
          <div className="analytics-swath-bar">
            <div
              className="analytics-swath-bar__port"
              style={{ width: `${swathStats.portPct}%` }}
              title={`Port Channel: ${swathStats.port} contacts (${swathStats.portPct}%)`}
            />
            <div
              className="analytics-swath-bar__stbd"
              style={{ width: `${swathStats.stbdPct}%` }}
              title={`Starboard Channel: ${swathStats.starboard} contacts (${swathStats.stbdPct}%)`}
            />
          </div>
          <div className="analytics-swath-legend">
            <span><span className="analytics-legend-dot analytics-legend-dot--port" /> Port (Left Swath)</span>
            <span><span className="analytics-legend-dot analytics-legend-dot--stbd" /> Starboard (Right Swath)</span>
          </div>
        </div>

        {/* Operator Review Status & Progress */}
        <div className="analytics-card">
          <div className="analytics-card-header">
            <h3 className="analytics-card__title">OPERATOR AUDIT PROGRESS</h3>
            <span className="analytics-card-badge">{reviewCompletionPct}% Audited</span>
          </div>
          {/* Stacked multi-segment bar */}
          <div className="analytics-stacked-bar">
            {total > 0 && (
              <>
                <div
                  className="analytics-stacked-seg analytics-stacked-seg--green"
                  style={{ width: `${(confirmedCount / total) * 100}%` }}
                  title={`Confirmed: ${confirmedCount}`}
                />
                <div
                  className="analytics-stacked-seg analytics-stacked-seg--amber"
                  style={{ width: `${(pendingCount / total) * 100}%` }}
                  title={`Flagged: ${pendingCount}`}
                />
                <div
                  className="analytics-stacked-seg analytics-stacked-seg--red"
                  style={{ width: `${(fpCount / total) * 100}%` }}
                  title={`False Positive: ${fpCount}`}
                />
                <div
                  className="analytics-stacked-seg analytics-stacked-seg--gray"
                  style={{ width: `${(unreviewedCount / total) * 100}%` }}
                  title={`Unreviewed: ${unreviewedCount}`}
                />
              </>
            )}
          </div>
          <div className="analytics-audit-grid">
            <div className="analytics-audit-row">
              <span className="analytics-audit-dot analytics-audit-dot--green" />
              <span className="analytics-audit-name">Confirmed Valid Targets</span>
              <span className="analytics-audit-val">{confirmedCount}</span>
            </div>
            <div className="analytics-audit-row">
              <span className="analytics-audit-dot analytics-audit-dot--amber" />
              <span className="analytics-audit-name">Flagged for Review</span>
              <span className="analytics-audit-val">{pendingCount}</span>
            </div>
            <div className="analytics-audit-row">
              <span className="analytics-audit-dot analytics-audit-dot--red" />
              <span className="analytics-audit-name">False Positives</span>
              <span className="analytics-audit-val">{fpCount}</span>
            </div>
            <div className="analytics-audit-row">
              <span className="analytics-audit-dot analytics-audit-dot--gray" />
              <span className="analytics-audit-name">Unreviewed AI Detections</span>
              <span className="analytics-audit-val">{unreviewedCount}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Class Breakdown & Confidence Spectrum */}
      <div className="analytics-dual-grid">
        {/* Object Classification Breakdown */}
        <div className="analytics-card">
          <h3 className="analytics-card__title">OBJECT CLASSIFICATION BREAKDOWN</h3>
          <div className="analytics-class-list">
            {Object.entries(summaryMap).map(([name, count]) => {
              const pct = total ? Math.round((count / total) * 100) : 0
              return (
                <div key={name} className="analytics-class-row">
                  <div className="analytics-class-info">
                    <span className="analytics-class-name">{name}</span>
                    <span className="analytics-class-count">{count} targets ({pct}%)</span>
                  </div>
                  <div className="analytics-bar-bg">
                    <div className="analytics-bar-fill" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
            {total === 0 && (
              <p className="analytics-empty">No objects detected. Run YOLO inference on a sonar scan to view metrics.</p>
            )}
          </div>
        </div>

        {/* Confidence Spectrum Histogram */}
        <div className="analytics-card">
          <h3 className="analytics-card__title">CONFIDENCE SPECTRUM HISTOGRAM</h3>
          <div className="analytics-class-list">
            {[
              { label: 'High Confidence (70% - 100%)', count: confidenceBins.high, color: '#22c55e' },
              { label: 'Moderate-High (50% - 70%)', count: confidenceBins.modHigh, color: '#3b82f6' },
              { label: 'Moderate (30% - 50%)', count: confidenceBins.mod, color: '#f59e0b' },
              { label: 'Low / Detection Threshold (15% - 30%)', count: confidenceBins.low, color: '#ef4444' },
            ].map((bin, i) => {
              const pct = total ? Math.round((bin.count / total) * 100) : 0
              return (
                <div key={i} className="analytics-class-row">
                  <div className="analytics-class-info">
                    <span className="analytics-class-name">{bin.label}</span>
                    <span className="analytics-class-count">{bin.count} ({pct}%)</span>
                  </div>
                  <div className="analytics-bar-bg">
                    <div
                      className="analytics-bar-fill"
                      style={{ width: `${pct}%`, background: bin.color }}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          {/* Contact Acoustic Footprint Profile */}
          <div className="analytics-footprint-block">
            <span className="analytics-footprint-title">CONTACT FOOTPRINT PROFILE</span>
            <div className="analytics-footprint-row">
              <span className="analytics-footprint-chip">Small Spot (&lt;5%): <strong>{sizeBins.small}</strong></span>
              <span className="analytics-footprint-chip">Medium Footprint (5-15%): <strong>{sizeBins.medium}</strong></span>
              <span className="analytics-footprint-chip">Large Structure (&gt;15%): <strong>{sizeBins.large}</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
