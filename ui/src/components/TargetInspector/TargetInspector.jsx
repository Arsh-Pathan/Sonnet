import React, { useState, useEffect } from 'react'
import { CLASS_META } from '../../constants'
import './TargetInspector.css'

export default function TargetInspector({
  selectedTarget,
  targets = [],
  onUpdateTargetStatus,
  onUpdateTargetNotes,
  onSelectTarget,
  onOpenExport,
  onOpenUpload,
  onFileSelected,
}) {
  const fileInputRef = React.useRef(null)

  // Local state for operator notes
  const [notes, setNotes] = useState('')
  const [isSaved, setIsSaved] = useState(false)

  // Interactive shadow calculation inputs
  const [towfishAlt, setTowfishAlt] = useState(15.0)
  const [shadowLen, setShadowLen] = useState(4.5)

  // Sync notes when active target changes
  useEffect(() => {
    if (selectedTarget) {
      setNotes(selectedTarget.operatorNotes || selectedTarget.notes || '')
      setIsSaved(false)

      // Estimate initial shadow length from bounding box extent if available
      const bboxW = selectedTarget.bbox?.w ?? 0.05
      setShadowLen(Number((bboxW * 200 * 0.4).toFixed(1)) || 4.5)
    }
  }, [selectedTarget?.id])

  const confirmedCount = targets.filter(
    t => t.status === 'Operator accepted' || t.status === 'Confirmed'
  ).length
  const pendingCount = targets.filter(t => t.status === 'Pending Review').length
  const fpCount = targets.filter(t => t.status === 'False Positive').length

  const currentIndex = selectedTarget ? targets.findIndex(t => t.id === selectedTarget.id) : -1
  const prevTarget = currentIndex > 0 ? targets[currentIndex - 1] : null
  const nextTarget = currentIndex >= 0 && currentIndex < targets.length - 1 ? targets[currentIndex + 1] : null

  const handleSaveNotes = () => {
    if (!selectedTarget) return
    if (onUpdateTargetNotes) {
      onUpdateTargetNotes(selectedTarget.id, notes)
    } else if (onUpdateTargetStatus) {
      onUpdateTargetStatus(selectedTarget.id, selectedTarget.status || 'Detected', notes)
    }
    setIsSaved(true)
    setTimeout(() => setIsSaved(false), 2000)
  }

  const handleDownloadCrop = () => {
    if (!selectedTarget?.thumbnailUrl) return
    const link = document.createElement('a')
    link.href = selectedTarget.thumbnailUrl
    link.download = `${selectedTarget.id}_${selectedTarget.type || 'acoustic_contact'}.jpg`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Calculate shadow height: H = (ShadowLength * TowfishAltitude) / SlantRange
  const bbox = selectedTarget?.bbox || {}
  const normX = bbox.x ?? 0.5
  const slantRangeM = Math.max(10, Math.abs(normX - 0.5) * 200)
  const estReliefHeightM = ((shadowLen * towfishAlt) / slantRangeM).toFixed(2)

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
            <p>Select any detection on the acoustic workspace or bottom detection log to inspect acoustic signatures, review YOLO model scores, calculate acoustic shadow relief, and confirm classifications.</p>
          </div>
        </div>
      </aside>
    )
  }

  const scorePct = Math.round((selectedTarget.confidence ?? selectedTarget.modelScore ?? 0.0) * 100)
  const meta = CLASS_META[selectedTarget.type] || { label: selectedTarget.type || 'Anomaly', color: '#f59e0b' }
  const channel = (selectedTarget.roi || selectedTarget.side || (selectedTarget.bbox?.x < 0.5 ? 'port' : 'starboard')).toUpperCase()
  const hasGeotag = selectedTarget.geotag && selectedTarget.geotag.latitude != null

  const bx = bbox.x != null ? (bbox.x * 100).toFixed(1) : '—'
  const by = bbox.y != null ? (bbox.y * 100).toFixed(1) : '—'
  const bw = bbox.w != null ? (bbox.w * 100).toFixed(1) : '—'
  const bh = bbox.h != null ? (bbox.h * 100).toFixed(1) : '—'

  return (
    <aside className="target-inspector">
      {/* Header with Target Navigation */}
      <div className="ti-header">
        <div className="ti-header-left">
          <span className="ti-status-dot" style={{ background: meta.color }} />
          <span className="ti-title">{selectedTarget.id}</span>
          <span className="ti-counter">({currentIndex + 1} of {targets.length})</span>
        </div>
        <div className="ti-header-right">
          <div className="ti-nav-group">
            <button
              type="button"
              className="ti-nav-btn"
              disabled={!prevTarget}
              onClick={() => prevTarget && onSelectTarget?.(prevTarget.id)}
              title="Previous target"
            >
              &lt;
            </button>
            <button
              type="button"
              className="ti-nav-btn"
              disabled={!nextTarget}
              onClick={() => nextTarget && onSelectTarget?.(nextTarget.id)}
              title="Next target"
            >
              &gt;
            </button>
          </div>
          <span className={`ti-badge ti-badge--${(selectedTarget.status || 'detected').replace(/\s+/g, '-').toLowerCase()}`}>
            {(selectedTarget.status || 'DETECTED').toUpperCase()}
          </span>
        </div>
      </div>

      <div className="ti-body">
        {/* High-Resolution Acoustic Crop Viewport with Download Option */}
        <div className="ti-viewport">
          <img
            src={selectedTarget.thumbnailUrl || '/assets/sonar_shipwreck_scan.jpg'}
            alt={selectedTarget.id}
            className="ti-viewport-img"
          />
          <div className="ti-viewport-tag">{channel} CH</div>
          <button
            type="button"
            className="ti-download-crop-btn"
            onClick={handleDownloadCrop}
            title="Download target acoustic crop (JPEG)"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Save Crop
          </button>
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

        {/* Acoustic Shadow Relief Calculator */}
        <div className="ti-card">
          <div className="ti-card-header-sm">ACOUSTIC SHADOW RELIEF ESTIMATION</div>
          <div className="ti-calc-grid">
            <div className="ti-calc-field">
              <label className="ti-calc-lbl">Shadow Length (m)</label>
              <input
                type="number"
                step="0.5"
                min="0.1"
                className="ti-calc-input"
                value={shadowLen}
                onChange={e => setShadowLen(parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="ti-calc-field">
              <label className="ti-calc-lbl">Towfish Altitude (m)</label>
              <input
                type="number"
                step="0.5"
                min="1.0"
                className="ti-calc-input"
                value={towfishAlt}
                onChange={e => setTowfishAlt(parseFloat(e.target.value) || 0)}
              />
            </div>
          </div>
          <div className="ti-calc-result">
            <span className="ti-calc-result-lbl">Calculated Contact Height:</span>
            <strong className="ti-calc-result-val">~{estReliefHeightM} m</strong>
          </div>
        </div>

        {/* Navigation & Telemetry */}
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

        {/* Operator Audit Notes (Persistent to SQLite) */}
        <div className="ti-card">
          <div className="ti-card-header-sm">OPERATOR AUDIT NOTES</div>
          <textarea
            className="ti-notes-input"
            rows={3}
            placeholder="Add hydrographic observations, seafloor contact dimensions, or debris classification notes..."
            value={notes}
            onChange={e => setNotes(e.target.value)}
            onBlur={handleSaveNotes}
          />
          <div className="ti-notes-footer">
            <button
              type="button"
              className="ti-notes-save-btn"
              onClick={handleSaveNotes}
            >
              {isSaved ? 'Notes Saved!' : 'Save Notes'}
            </button>
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
              onClick={() => onUpdateTargetStatus(selectedTarget.id, 'Confirmed', notes)}
            >
              Confirm Detection (C)
            </button>
            <button
              type="button"
              className={`ti-btn ti-btn--review ${selectedTarget.status === 'Pending Review' ? 'ti-btn--active' : ''}`}
              onClick={() => onUpdateTargetStatus(selectedTarget.id, 'Pending Review', notes)}
            >
              Flag for Review (F)
            </button>
            <button
              type="button"
              className={`ti-btn ti-btn--reject ${selectedTarget.status === 'False Positive' ? 'ti-btn--active' : ''}`}
              onClick={() => onUpdateTargetStatus(selectedTarget.id, 'False Positive', notes)}
            >
              Mark False Positive (X)
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}
