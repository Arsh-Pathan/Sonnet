import React from 'react'
import './AnalyticsPanel.css'

export default function AnalyticsPanel({ detections = [] }) {
  // Compute class summary
  const summaryMap = detections.reduce((acc, det) => {
    const rawName = det.class_name || det.type || det.class || 'unknown'
    const formattedName = rawName.replace(/_/g, ' ').toUpperCase()
    acc[formattedName] = (acc[formattedName] || 0) + 1
    return acc
  }, {})

  // Compute verification breakdown
  const confirmedCount = detections.filter(
    d => d.status === 'Operator accepted' || d.status === 'Confirmed'
  ).length
  const pendingCount = detections.filter(d => d.status === 'Pending Review').length
  const fpCount = detections.filter(d => d.status === 'False Positive').length
  const unreviewedCount = detections.length - confirmedCount - pendingCount - fpCount

  // Compute average confidence
  const avgConfidence = detections.length
    ? detections.reduce((sum, det) => sum + (det.confidence ?? det.modelScore ?? 0), 0) / detections.length
    : 0

  const confidencePercent = (avgConfidence * 100).toFixed(1)

  return (
    <div className="analytics-view">
      <div className="analytics-header">
        <h2 className="analytics-header__title">DETECTION ANALYTICS &amp; SURVEY METRICS</h2>
        <span className="analytics-header__badge">{detections.length} Total Detections</span>
      </div>

      <div className="analytics-grid">
        {/* KPI Cards */}
        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">TOTAL DETECTIONS</span>
          <span className="analytics-kpi-val analytics-kpi-val--blue">{detections.length}</span>
          <span className="analytics-kpi-sub">Across active survey scan</span>
        </div>

        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">OPERATOR CONFIRMED</span>
          <span className="analytics-kpi-val analytics-kpi-val--green">{confirmedCount}</span>
          <span className="analytics-kpi-sub">
            {detections.length ? `${Math.round((confirmedCount / detections.length) * 100)}% verified` : '0%'}
          </span>
        </div>

        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">FLAGGED FOR REVIEW</span>
          <span className="analytics-kpi-val analytics-kpi-val--amber">{pendingCount}</span>
          <span className="analytics-kpi-sub">Requires secondary audit</span>
        </div>

        <div className="analytics-kpi-card">
          <span className="analytics-kpi-lbl">AVG MODEL CONFIDENCE</span>
          <span className="analytics-kpi-val">{confidencePercent}%</span>
          <span className="analytics-kpi-sub">YOLOv11s inference mean</span>
        </div>
      </div>

      {/* Class Breakdown Section */}
      <div className="analytics-card">
        <h3 className="analytics-card__title">OBJECT CLASSIFICATION BREAKDOWN</h3>
        <div className="analytics-class-list">
          {Object.entries(summaryMap).map(([name, count]) => {
            const pct = detections.length ? Math.round((count / detections.length) * 100) : 0
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
          {detections.length === 0 && (
            <p className="analytics-empty">No objects detected. Run YOLO inference on a sonar scan to view metrics.</p>
          )}
        </div>
      </div>

      {/* Verification State Breakdown */}
      <div className="analytics-card">
        <h3 className="analytics-card__title">OPERATOR REVIEW STATUS AUDIT</h3>
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
            <span className="analytics-audit-val">{Math.max(0, unreviewedCount)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
