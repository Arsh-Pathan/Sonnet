import React, { useState, useMemo } from 'react'
import './TargetLog.css'

const REVIEW_OPTIONS = ['Detected', 'Confirmed', 'Pending Review', 'False Positive']

export default function TargetLog({
  targets = [],
  selectedTargetId,
  onSelectTarget,
  onUpdateTargetStatus,
  onBatchUpdateStatus,
  collapsed,
  onToggleCollapse,
}) {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [channelFilter, setChannelFilter] = useState('ALL')
  const [sortColumn, setSortColumn] = useState('id') // 'id' | 'class' | 'score' | 'channel' | 'status'
  const [sortAsc, setSortAsc] = useState(true)

  const handleSort = (col) => {
    if (sortColumn === col) {
      setSortAsc(prev => !prev)
    } else {
      setSortColumn(col)
      setSortAsc(true)
    }
  }

  // 1. Filter
  const filtered = useMemo(() => {
    return targets.filter(t => {
      const matchesSearch = !search ||
        (t.id && t.id.toLowerCase().includes(search.toLowerCase())) ||
        (t.class && t.class.toLowerCase().includes(search.toLowerCase())) ||
        (t.type && t.type.toLowerCase().includes(search.toLowerCase()))

      const matchesStatus = statusFilter === 'ALL' ||
        (statusFilter === 'CONFIRMED' && (t.status === 'Operator accepted' || t.status === 'Confirmed')) ||
        (statusFilter === 'DETECTED' && (!t.status || t.status === 'Detected')) ||
        (statusFilter === 'REVIEW' && t.status === 'Pending Review') ||
        (statusFilter === 'FALSE_POSITIVE' && t.status === 'False Positive')

      const ch = (t.roi || t.side || (t.bbox?.x < 0.5 ? 'port' : 'starboard')).toLowerCase()
      const matchesChannel = channelFilter === 'ALL' || ch === channelFilter.toLowerCase()

      return matchesSearch && matchesStatus && matchesChannel
    })
  }, [targets, search, statusFilter, channelFilter])

  // 2. Sort
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let valA
      let valB

      switch (sortColumn) {
        case 'id':
          valA = a.id || ''
          valB = b.id || ''
          return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA)
        case 'class':
          valA = a.class || a.type || ''
          valB = b.class || b.type || ''
          return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA)
        case 'score':
          valA = Number(a.confidence ?? a.modelScore ?? 0)
          valB = Number(b.confidence ?? b.modelScore ?? 0)
          return sortAsc ? valA - valB : valB - valA
        case 'channel':
          valA = (a.roi || a.side || (a.bbox?.x < 0.5 ? 'port' : 'starboard')).toLowerCase()
          valB = (b.roi || b.side || (b.bbox?.x < 0.5 ? 'port' : 'starboard')).toLowerCase()
          return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA)
        case 'status':
          valA = a.status || 'Detected'
          valB = b.status || 'Detected'
          return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA)
        default:
          return 0
      }
    })
  }, [filtered, sortColumn, sortAsc])

  // Batch actions on filtered targets
  const handleBatchConfirm = () => {
    if (!filtered.length) return
    const ids = filtered.map(t => t.id)
    if (onBatchUpdateStatus) {
      onBatchUpdateStatus(ids, 'Confirmed')
    } else if (onUpdateTargetStatus) {
      ids.forEach(id => onUpdateTargetStatus(id, 'Confirmed'))
    }
  }

  const handleBatchFlag = () => {
    if (!filtered.length) return
    const ids = filtered.map(t => t.id)
    if (onBatchUpdateStatus) {
      onBatchUpdateStatus(ids, 'Pending Review')
    } else if (onUpdateTargetStatus) {
      ids.forEach(id => onUpdateTargetStatus(id, 'Pending Review'))
    }
  }

  const handleExportFilteredCsv = () => {
    if (!sorted.length) return
    const headers = [
      'detection_id',
      'class_name',
      'confidence',
      'channel',
      'status',
      'notes',
      'bbox_x',
      'bbox_y',
      'bbox_w',
      'bbox_h'
    ]
    const rows = sorted.map(t => [
      t.id || '',
      t.type || t.class || '',
      (t.confidence ?? t.modelScore ?? 0).toFixed(4),
      (t.roi || t.side || (t.bbox?.x < 0.5 ? 'port' : 'starboard')).toUpperCase(),
      t.status || 'Detected',
      `"${(t.operatorNotes || t.notes || '').replace(/"/g, '""')}"`,
      t.bbox?.x ?? '',
      t.bbox?.y ?? '',
      t.bbox?.w ?? '',
      t.bbox?.h ?? ''
    ])
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `sonar_filtered_targets_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const renderSortIndicator = (col) => {
    if (sortColumn !== col) return null
    return (
      <span className="tl-sort-icon">
        {sortAsc ? (
          <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="18 15 12 9 6 15" />
          </svg>
        ) : (
          <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        )}
      </span>
    )
  }

  return (
    <div className={`target-log ${collapsed ? 'target-log--collapsed' : ''}`}>
      {/* Header Bar */}
      <div className="tl-header">
        <div className="tl-header__left">
          <span className="tl-indicator" />
          <span className="tl-title">DETECTION LOG &amp; AUDIT</span>
          <span className="tl-count">{sorted.length} of {targets.length} Records</span>

          {/* Batch Actions Toolbar */}
          {!collapsed && sorted.length > 0 && (
            <div className="tl-batch-actions">
              <span className="tl-batch-sep">|</span>
              <button
                type="button"
                className="tl-batch-btn tl-batch-btn--green"
                onClick={handleBatchConfirm}
                title="Confirm all currently visible/filtered detections"
              >
                Confirm Filtered ({sorted.length})
              </button>
              <button
                type="button"
                className="tl-batch-btn tl-batch-btn--amber"
                onClick={handleBatchFlag}
                title="Flag all currently visible/filtered detections for review"
              >
                Flag Filtered
              </button>
              <button
                type="button"
                className="tl-batch-btn"
                onClick={handleExportFilteredCsv}
                title="Export currently filtered table to CSV"
              >
                Export CSV
              </button>
            </div>
          )}
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

          {/* Swath Filter Pills */}
          <div className="tl-filter-pills">
            {['ALL', 'PORT', 'STARBOARD'].map(ch => (
              <button
                key={ch}
                type="button"
                className={`tl-pill-btn ${channelFilter === ch ? 'tl-pill-btn--active' : ''}`}
                onClick={() => setChannelFilter(ch)}
              >
                {ch === 'STARBOARD' ? 'STBD' : ch}
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

          {/* Collapse/Expand Toggle (Clean SVG) */}
          <button
            type="button"
            className="tl-collapse-btn"
            onClick={onToggleCollapse}
            title={collapsed ? 'Expand Log' : 'Collapse Log'}
          >
            {collapsed ? (
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="18 15 12 9 6 15" />
              </svg>
            ) : (
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* Table Body */}
      {!collapsed && (
        <div className="tl-body">
          <table className="tl-table">
            <thead>
              <tr>
                <th className="tl-th--sortable" onClick={() => handleSort('id')}>
                  <span className="tl-th-inner">DETECTION ID {renderSortIndicator('id')}</span>
                </th>
                <th>ACOUSTIC RETURN</th>
                <th className="tl-th--sortable" onClick={() => handleSort('class')}>
                  <span className="tl-th-inner">PREDICTED CLASS {renderSortIndicator('class')}</span>
                </th>
                <th className="tl-th--sortable" onClick={() => handleSort('score')}>
                  <span className="tl-th-inner">YOLO CONFIDENCE {renderSortIndicator('score')}</span>
                </th>
                <th className="tl-th--sortable" onClick={() => handleSort('channel')}>
                  <span className="tl-th-inner">SWATH / CHANNEL {renderSortIndicator('channel')}</span>
                </th>
                <th>BOUNDING BOX (X, Y, W, H)</th>
                <th className="tl-th--sortable" onClick={() => handleSort('status')}>
                  <span className="tl-th-inner">OPERATOR VERIFICATION {renderSortIndicator('status')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(t => {
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
              {sorted.length === 0 && (
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
