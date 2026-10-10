import React, { useState } from 'react'
import './TargetLog.css'

const REVIEW_OPTIONS = ['Detected', 'Confirmed', 'Pending Review', 'False Positive']

export default function TargetLog({
  targets = [],
  selectedTargetId,
  onSelectTarget,
  onUpdateTargetStatus,
  collapsed,
  onToggleCollapse,
}) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [channelFilter, setChannelFilter] = useState('ALL')

  const filtered = targets.filter(t => {
    // 1. Search filter
    const matchesSearch = !search ||
      (t.id && t.id.toLowerCase().includes(search.toLowerCase())) ||
      (t.class && t.class.toLowerCase().includes(search.toLowerCase())) ||
      (t.type && t.type.toLowerCase().includes(search.toLowerCase()))

    // 2. Status filter
    const matchesStatus = statusFilter === 'ALL' ||
      (statusFilter === 'CONFIRMED' && (t.status === 'Operator accepted' || t.status === 'Confirmed')) ||
      (statusFilter === 'DETECTED' && (!t.status || t.status === 'Detected')) ||
      (statusFilter === 'REVIEW' && t.status === 'Pending Review') ||
      (statusFilter === 'FALSE_POSITIVE' && t.status === 'False Positive')

    // 3. Channel filter
    const ch = (t.roi || t.side || (t.bbox?.x < 0.5 ? 'port' : 'starboard')).toLowerCase()
    const matchesChannel = channelFilter === 'ALL' || ch === channelFilter.toLowerCase()

    return matchesSearch && matchesStatus && matchesChannel
  })

  return (
    <div className={`target-log ${collapsed ? 'target-log--collapsed' : ''}`}>
      {/* Header Bar */}
      <div className="tl-header">
        <div className="tl-header__left">
          <span className="tl-indicator" />
          <span className="tl-title">DETECTION LOG &amp; AUDIT</span>
          <span className="tl-count">{filtered.length} of {targets.length} Records</span>
        </div>

        <div className="tl-header__right">
          {/* Quick Status Filter Pills */}
          <div className="tl-filter-pills">
            {['ALL', 'CONFIRMED', 'DETECTED', 'REVIEW'].map(s => (
              <button
                key={s}
                type="button"
                className={`tl-pill-btn ${statusFilter === s ? 'tl-pill-btn--active' : ''}`}
                onClick={() => setStatusFilter(s)}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="tl-search">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              className="tl-search__input"
              placeholder="Filter by ID, class..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button type="button" className="tl-clear-btn" onClick={() => setSearch('')}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>

          <button
            type="button"
            className="tl-collapse-btn"
            onClick={onToggleCollapse}
            title={collapsed ? 'Expand Log' : 'Collapse Log'}
          >
            {collapsed ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* Table Body */}
      {!collapsed && (
        <div className="tl-body">
          <table className="tl-table">
            <thead>
              <tr>
                <th>DETECTION ID</th>
                <th>ACOUSTIC RETURN</th>
                <th>PREDICTED CLASS</th>
                <th>YOLO CONFIDENCE</th>
                <th>SWATH / CHANNEL</th>
                <th>BOUNDING BOX (X, Y, W, H)</th>
                <th>OPERATOR VERIFICATION</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(t => {
                const isSelected = selectedTargetId === t.id
                const score = Number(t.confidence ?? t.modelScore ?? 0.0)
                const channel = (t.roi || t.side || (t.bbox?.x < 0.5 ? 'port' : 'starboard')).toUpperCase()
                const bx = t.bbox?.x != null ? (t.bbox.x * 100).toFixed(1) : '—'
                const by = t.bbox?.y != null ? (t.bbox.y * 100).toFixed(1) : '—'
                const bw = t.bbox?.w != null ? (t.bbox.w * 100).toFixed(1) : '—'
                const bh = t.bbox?.h != null ? (t.bbox.h * 100).toFixed(1) : '—'

                return (
                  <tr
                    key={t.id}
                    className={`tl-row ${isSelected ? 'tl-row--selected' : ''}`}
                    onClick={() => onSelectTarget?.(t.id)}
                  >
                    <td className="tl-cell tl-cell--id">{t.id}</td>
                    <td className="tl-cell">
                      <div className={`tl-thumb-wrap ${isSelected ? 'tl-thumb-wrap--selected' : ''}`}>
                        <img
                          src={t.thumbnailUrl || '/assets/sonar_shipwreck_scan.jpg'}
                          alt={t.id}
                          className="tl-thumb-img"
                          loading="lazy"
                        />
                      </div>
                    </td>
                    <td className="tl-cell">
                      <span className="tl-class">{t.class || (t.type && t.type.toUpperCase().replace(/_/g, ' '))}</span>
                      <span className="tl-type-sub">{t.type ? t.type.replace(/_/g, ' ') : 'acoustic anomaly'}</span>
                    </td>
                    <td className="tl-cell tl-cell--score">
                      <span className={`tl-score ${score >= 0.7 ? 'tl-score--high' : score >= 0.4 ? 'tl-score--mid' : 'tl-score--low'}`}>
                        {(score * 100).toFixed(1)}% ({score.toFixed(3)})
                      </span>
                    </td>
                    <td className="tl-cell tl-cell--roi">{channel} CH</td>
                    <td className="tl-cell tl-cell--mono">{bx}%, {by}%, {bw}% &times; {bh}%</td>
                    <td className="tl-cell">
                      <select
                        className={`tl-status-select tl-status--${(t.status || 'detected').replace(/\s+/g, '-').toLowerCase()}`}
                        value={t.status === 'Operator accepted' ? 'Confirmed' : t.status || 'Detected'}
                        onClick={e => e.stopPropagation()}
                        onChange={e => {
                          e.stopPropagation()
                          onUpdateTargetStatus?.(t.id, e.target.value)
                        }}
                      >
                        {REVIEW_OPTIONS.map(s => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan="7" className="tl-empty">
                    {targets.length === 0
                      ? 'No detections loaded. Click "UPLOAD & ANALYZE" to process sonar imagery.'
                      : 'No target detections match the active filter criteria.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
