import React from 'react'
import { CLASS_META } from '../../constants'
import './TargetInspector.css'

export default function TargetInspector({
  selectedTarget,
  targets = [],
  onUpdateTargetStatus,
  onOpenExport,
  onOpenUpload,
  onFileSelected,
}) {
  const fileInputRef = React.useRef(null)
  const confirmedCount = targets.filter(
    t => t.status === 'Operator accepted' || t.status === 'Confirmed'
  ).length
  const pendingCount = targets.filter(t => t.status === 'Pending Review').length
  const fpCount = targets.filter(t => t.status === 'False Positive').length

  if (!selectedTarget) {
    return (
      <aside className="target-inspector">
        <div className="ti-header">
          <span className="ti-title">INSPECTION SUMMARY</span>
          <span className="ti-badge">{targets.length} DETECTIONS</span>
        </div>

        <div className="ti-body">
          <div className="ti-stats-grid">
            <div className="ti-stat-card">
              <span className="ti-stat-val ti-stat-val--blue">{targets.length}</span>
              <span className="ti-stat-lbl">Total Detections</span>
            </div>
            <div className="ti-stat-card">
              <span className="ti-stat-val ti-stat-val--green">{confirmedCount}</span>
              <span className="ti-stat-lbl">Confirmed</span>
            </div>
            <div className="ti-stat-card">
              <span className="ti-stat-val ti-stat-val--amber">{pendingCount}</span>
              <span className="ti-stat-lbl">Pending Review</span>
            </div>
            <div className="ti-stat-card">
              <span className="ti-stat-val ti-stat-val--red">{fpCount}</span>
              <span className="ti-stat-lbl">False Positives</span>
            </div>
          </div>

          <div className="ti-quick-actions">
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.tiff,.xtf,.jsf"
              style={{ display: 'none' }}
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f && onFileSelected) onFileSelected(f)
                e.target.value = ''
              }}
            />
            <button
              type="button"
              className="ti-action-btn ti-action-btn--primary"
              onClick={() => {
                if (onFileSelected) fileInputRef.current?.click()
                else onOpenUpload?.()
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Upload Sonar File
            </button>
            <button
              type="button"
              className="ti-action-btn ti-action-btn--secondary"
              onClick={onOpenExport}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Export Survey Report
            </button>
          </div>

          <div className="ti-instructions">
            <span className="ti-instruction-title">OPERATOR WORKSPACE</span>
            <p>Select any detection on the acoustic workspace or bottom detection log to inspect acoustic signatures, review YOLO model scores, and confirm classifications.</p>
          </div>
        </div>
      </aside>
    )
  }

  const scorePct = Math.round((selectedTarget.confidence ?? selectedTarget.modelScore ?? 0.0) * 100)
  const meta = CLASS_META[selectedTarget.type] || { label: selectedTarget.type || 'Anomaly', color: '#f59e0b' }
  const channel = (selectedTarget.roi || selectedTarget.side || (selectedTarget.bbox?.x < 0.5 ? 'port' : 'starboard')).toUpperCase()
  const hasGeotag = selectedTarget.geotag && selectedTarget.geotag.latitude != null

  const bbox = selectedTarget.bbox || {}
  const bx = bbox.x != null ? (bbox.x * 100).toFixed(1) : '—'
  const by = bbox.y != null ? (bbox.y * 100).toFixed(1) : '—'
  const bw = bbox.w != null ? (bbox.w * 100).toFixed(1) : '—'
  const bh = bbox.h != null ? (bbox.h * 100).toFixed(1) : '—'

  return (
    <aside className="target-inspector">
      <div className="ti-header">
        <div className="ti-header-left">
          <span className="ti-status-dot" style={{ background: meta.color }} />
          <span className="ti-title">{selectedTarget.id}</span>
        </div>
        <span className={`ti-badge ti-badge--${(selectedTarget.status || 'detected').replace(/\s+/g, '-').toLowerCase()}`}>
          {(selectedTarget.status || 'DETECTED').toUpperCase()}
        </span>
      </div>

      <div className="ti-body">
        {/* High-Resolution Acoustic Crop Viewport */}
        <div className="ti-viewport">
          <img
            src={selectedTarget.thumbnailUrl || '/assets/sonar_shipwreck_scan.jpg'}
            alt={selectedTarget.id}
            className="ti-viewport-img"
          />
          <div className="ti-viewport-tag">{channel} CH</div>
        </div>

        {/* AI Confidence & Classification */}
        <div className="ti-card">
          <div className="ti-card-row">
            <span className="ti-label">PREDICTED CLASS</span>
            <span className="ti-val ti-val--strong" style={{ color: meta.color }}>
              {selectedTarget.class || meta.label || (selectedTarget.type && selectedTarget.type.toUpperCase().replace(/_/g, ' '))}
            </span>
          </div>
          <div className="ti-conf-bar-wrap">
            <div className="ti-conf-bar">
              <div
                className="ti-conf-fill"
                style={{
                  width: `${scorePct}%`,
                  background: scorePct >= 70 ? '#22c55e' : scorePct >= 40 ? '#facc15' : '#ef4444',
                }}
              />
            </div>
            <span className="ti-conf-pct">{scorePct}% CONFIDENCE</span>
          </div>
        </div>

        {/* Spatial Coordinates & Bounding Box */}
        <div className="ti-card">
          <div className="ti-card-header-sm">DETECTION GEOMETRY</div>
          <div className="ti-card-row">
            <span className="ti-label">CHANNEL / SWATH</span>
            <span className="ti-val ti-val--mono">{channel} [CH {channel === 'PORT' ? '1' : '2'}]</span>
          </div>
          <div className="ti-card-row">
            <span className="ti-label">NORM BOUNDS (X, Y)</span>
            <span className="ti-val ti-val--mono">{bx}%, {by}%</span>
          </div>
          <div className="ti-card-row">
            <span className="ti-label">EXTENT (W &times; H)</span>
            <span className="ti-val ti-val--mono">{bw}% &times; {bh}%</span>
          </div>
        </div>

        {/* Navigation & Telemetry (Honest states) */}
        <div className="ti-card">
          <div className="ti-card-header-sm">GEOSPATIAL TELEMETRY</div>
          <div className="ti-card-row">
            <span className="ti-label">LATITUDE</span>
            <span className="ti-val ti-val--mono">
              {hasGeotag ? `${Number(selectedTarget.geotag.latitude).toFixed(5)}° N` : 'Unavailable (No GPS fix)'}
            </span>
          </div>
          <div className="ti-card-row">
            <span className="ti-label">LONGITUDE</span>
            <span className="ti-val ti-val--mono">
              {hasGeotag ? `${Math.abs(Number(selectedTarget.geotag.longitude)).toFixed(5)}° W` : 'Unavailable'}
            </span>
          </div>
          <div className="ti-card-row">
            <span className="ti-label">SENSOR ALTITUDE</span>
            <span className="ti-val ti-val--mono">
              {selectedTarget.geotag?.depth_meters != null
                ? `${Number(selectedTarget.geotag.depth_meters).toFixed(1)} m`
                : 'Unavailable'}
            </span>
          </div>
        </div>

        {/* Operator Verification Actions */}
        <div className="ti-actions-section">
          <div className="ti-section-header">
            <span className="ti-section-title">OPERATOR VERIFICATION</span>
            <span className="ti-review-status-indicator">
              {selectedTarget.status === 'Operator accepted' || selectedTarget.status === 'Confirmed'
                ? 'Confirmed'
                : selectedTarget.status === 'False Positive'
                ? 'False Positive'
                : selectedTarget.status === 'Pending Review'
                ? 'Flagged'
                : 'Review Pending'}
            </span>
          </div>
          <div className="ti-btn-group">
            <button
              type="button"
              className={`ti-btn ti-btn--accept ${selectedTarget.status === 'Operator accepted' || selectedTarget.status === 'Confirmed' ? 'ti-btn--active' : ''}`}
              onClick={() => onUpdateTargetStatus(selectedTarget.id, 'Confirmed')}
            >
              Confirm Detection
            </button>
            <button
              type="button"
              className={`ti-btn ti-btn--review ${selectedTarget.status === 'Pending Review' ? 'ti-btn--active' : ''}`}
              onClick={() => onUpdateTargetStatus(selectedTarget.id, 'Pending Review')}
            >
              Flag for Review
            </button>
            <button
              type="button"
              className={`ti-btn ti-btn--reject ${selectedTarget.status === 'False Positive' ? 'ti-btn--active' : ''}`}
              onClick={() => onUpdateTargetStatus(selectedTarget.id, 'False Positive')}
            >
              Mark False Positive
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}
