import React, { useState } from 'react'
import { generateReportApi } from '../api/client'

export default function ReportModal({ detections = [], fileName = 'scan', onClose }) {
  const [exportFormat, setExportFormat] = useState('html')
  const [isExporting, setIsExporting] = useState(false)
  const [exportStatus, setExportStatus] = useState('')

  async function handleDownload() {
    setIsExporting(true)
    const baseName = fileName.replace(/\.[^/.]+$/, '')

    // 1. Try B1's backend report generation endpoint if requesting csv/geojson
    if (exportFormat === 'csv' || exportFormat === 'geojson') {
      try {
        setExportStatus('Requesting report from backend API (POST /api/v1/reports/generate)...')
        const blob = await generateReportApi(exportFormat, detections)
        const ext = exportFormat === 'csv' ? 'csv' : 'geojson'
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `synora_report_${baseName}_${new Date().toISOString().slice(0, 10)}.${ext}`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        onClose()
        return
      } catch (err) {
        console.warn('Backend report generation unavailable, falling back to client-side generation:', err)
        setExportStatus('Backend unreachable, generating client-side export...')
      }
    }

    // 2. Client-side generation (Executive HTML, CSV, GeoJSON, JSON)
    let content = ''
    let mimeType = 'text/plain'
    let extension = 'txt'

    if (exportFormat === 'html') {
      const confirmedCount = detections.filter(
        d => d.status === 'Operator accepted' || d.status === 'Confirmed'
      ).length
      const pendingCount = detections.filter(
        d => d.status === 'Pending Review' || d.status === 'Flagged'
      ).length
      const fpCount = detections.filter(d => d.status === 'False Positive').length
      const avgConf = detections.length
        ? (detections.reduce((acc, d) => acc + Number(d.confidence ?? d.modelScore ?? 0), 0) / detections.length * 100).toFixed(1)
        : '0.0'

      content = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sonar Survey Acoustic Inspection Report - ${baseName}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 40px;
      color: #1e293b;
      background: #ffffff;
      line-height: 1.5;
    }
    .header {
      border-bottom: 2px solid #0f172a;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }
    .header h1 {
      margin: 0 0 6px 0;
      font-size: 22px;
      color: #0f172a;
      letter-spacing: 0.5px;
    }
    .header-meta {
      font-size: 12px;
      color: #64748b;
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-bottom: 28px;
    }
    .summary-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 12px 16px;
    }
    .summary-card .label {
      font-size: 11px;
      color: #64748b;
      text-transform: uppercase;
      font-weight: 600;
    }
    .summary-card .val {
      font-size: 22px;
      font-weight: 700;
      color: #0f172a;
      margin-top: 4px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 16px;
    }
    th {
      background: #f1f5f9;
      color: #334155;
      text-align: left;
      padding: 8px 10px;
      border-bottom: 2px solid #cbd5e1;
      font-weight: 600;
    }
    td {
      padding: 8px 10px;
      border-bottom: 1px solid #e2e8f0;
      color: #1e293b;
    }
    tr:nth-child(even) {
      background: #f8fafc;
    }
    .badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge--confirmed { background: #dcfce7; color: #15803d; }
    .badge--review { background: #fef3c7; color: #b45309; }
    .badge--fp { background: #fee2e2; color: #b91c1c; }
    .badge--detected { background: #e0f2fe; color: #0369a1; }
    @media print {
      body { margin: 20px; }
      .no-print { display: none; }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>SIDE-SCAN SONAR ACOUSTIC TARGET INSPECTION REPORT</h1>
    <div class="header-meta">
      <div><strong>Survey Source:</strong> ${fileName}</div>
      <div><strong>Generated:</strong> ${new Date().toISOString().replace('T', ' ').slice(0, 19)} UTC</div>
      <div><strong>Inference Architecture:</strong> YOLOv11s Sonar AI</div>
      <div><strong>Acoustic Swath:</strong> 200m Calibrated Swath</div>
    </div>
  </div>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="label">Total Detections</div>
      <div class="val">${detections.length}</div>
    </div>
    <div class="summary-card">
      <div class="label">Confirmed Valid</div>
      <div class="val">${confirmedCount}</div>
    </div>
    <div class="summary-card">
      <div class="label">Pending Review</div>
      <div class="val">${pendingCount}</div>
    </div>
    <div class="summary-card">
      <div class="label">Mean Confidence</div>
      <div class="val">${avgConf}%</div>
    </div>
  </div>

  <h2>Target Contact Ledger (${detections.length} Records)</h2>
  <table>
    <thead>
      <tr>
        <th>Detection ID</th>
        <th>Classification</th>
        <th>Confidence</th>
        <th>Swath Channel</th>
        <th>Status</th>
        <th>Normalized Coordinates</th>
        <th>Operator Notes</th>
      </tr>
    </thead>
    <tbody>
      ${detections.map(d => {
        const detId = d.detection_id || d.id || 'N/A'
        const clsName = (d.class_name || d.type || d.class || 'anomaly').toUpperCase().replace(/_/g, ' ')
        const conf = (Number(d.confidence ?? d.modelScore ?? 0) * 100).toFixed(1)
        const channel = (d.roi || d.side || (d.bbox?.x < 0.5 ? 'port' : 'starboard')).toUpperCase()
        const status = d.status || d.review_status || 'Detected'
        const notes = d.operatorNotes || d.notes || '—'
        const bx = d.bbox?.x != null ? (d.bbox.x * 100).toFixed(1) : '—'
        const by = d.bbox?.y != null ? (d.bbox.y * 100).toFixed(1) : '—'
        const bw = d.bbox?.w != null ? (d.bbox.w * 100).toFixed(1) : '—'
        const bh = d.bbox?.h != null ? (d.bbox.h * 100).toFixed(1) : '—'
        
        let badgeClass = 'badge--detected'
        if (status === 'Operator accepted' || status === 'Confirmed') badgeClass = 'badge--confirmed'
        else if (status === 'Pending Review' || status === 'Flagged') badgeClass = 'badge--review'
        else if (status === 'False Positive') badgeClass = 'badge--fp'

        return `<tr>
          <td><strong>${detId}</strong></td>
          <td>${clsName}</td>
          <td>${conf}%</td>
          <td>${channel} CH</td>
          <td><span class="badge ${badgeClass}">${status}</span></td>
          <td>${bx}%, ${by}% (${bw}% &times; ${bh}%)</td>
          <td>${notes}</td>
        </tr>`
      }).join('\n')}
    </tbody>
  </table>
</body>
</html>`
      mimeType = 'text/html;charset=utf-8;'
      extension = 'html'
    } else if (exportFormat === 'csv') {
      const headers = [
        'detection_id',
        'class_name',
        'confidence',
        'channel',
        'status',
        'operator_notes',
        'latitude',
        'longitude',
        'depth_meters',
        'bbox_x_min',
        'bbox_y_min',
        'bbox_x_max',
        'bbox_y_max',
      ]
      const rows = detections.map((d) => [
        d.detection_id || d.id || '',
        d.class_name || d.type || d.class || '',
        (Number(d.confidence ?? d.modelScore ?? 0)).toFixed(4),
        (d.roi || d.side || (d.bbox?.x < 0.5 ? 'port' : 'starboard')).toUpperCase(),
        d.status || d.review_status || 'Detected',
        `"${(d.operatorNotes || d.notes || '').replace(/"/g, '""')}"`,
        d.geotag?.latitude ?? '',
        d.geotag?.longitude ?? '',
        d.geotag?.depth_meters ?? '',
        d.bbox?.x_min ?? d.bbox?.x ?? '',
        d.bbox?.y_min ?? d.bbox?.y ?? '',
        d.bbox?.x_max ?? (d.bbox?.x != null && d.bbox?.w != null ? +(d.bbox.x + d.bbox.w).toFixed(4) : ''),
        d.bbox?.y_max ?? (d.bbox?.y != null && d.bbox?.h != null ? +(d.bbox.y + d.bbox.h).toFixed(4) : ''),
      ])
      content = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
      mimeType = 'text/csv;charset=utf-8;'
      extension = 'csv'
    } else if (exportFormat === 'geojson') {
      const features = detections.map((d) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [d.geotag?.longitude ?? 0, d.geotag?.latitude ?? 0],
        },
        properties: {
          detection_id: d.detection_id || d.id,
          class_name: d.class_name || d.type || d.class,
          confidence: Number(d.confidence ?? d.modelScore ?? 0),
          status: d.status || d.review_status || 'Detected',
          operator_notes: d.operatorNotes || d.notes || null,
          depth_meters: d.geotag?.depth_meters ?? null,
          bbox: d.bbox,
        },
      }))
      const geojson = {
        type: 'FeatureCollection',
        crs: {
          type: 'name',
          properties: { name: 'urn:ogc:def:crs:OGC:1.3:CRS84' },
        },
        features,
      }
      content = JSON.stringify(geojson, null, 2)
      mimeType = 'application/geo+json;charset=utf-8;'
      extension = 'geojson'
    } else {
      content = JSON.stringify(detections, null, 2)
      mimeType = 'application/json;charset=utf-8;'
      extension = 'json'
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `synora_report_${baseName}_${new Date().toISOString().slice(0, 10)}.${extension}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    setIsExporting(false)
    onClose()
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Export Inspection Report</h3>
          <button type="button" className="btn-close" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-body">
          <p className="modal-text">
            Export {detections.length} anomaly detections for executive briefing, hydrographic analysis, GIS archival, or audit records.
          </p>

          <div className="format-options">
            <label className={`format-option ${exportFormat === 'html' ? 'format-option--selected' : ''}`}>
              <input
                type="radio"
                name="format"
                value="html"
                checked={exportFormat === 'html'}
                onChange={() => setExportFormat('html')}
                disabled={isExporting}
              />
              <div className="format-option__content">
                <strong>Executive Survey Report (.html)</strong>
                <span>Formatted printable document with survey metrics and complete target contact ledger.</span>
              </div>
            </label>

            <label className={`format-option ${exportFormat === 'csv' ? 'format-option--selected' : ''}`}>
              <input
                type="radio"
                name="format"
                value="csv"
                checked={exportFormat === 'csv'}
                onChange={() => setExportFormat('csv')}
                disabled={isExporting}
              />
              <div className="format-option__content">
                <strong>CSV Spreadsheet (.csv)</strong>
                <span>Tabular dataset with normalized bounding boxes, confidence values, and notes.</span>
              </div>
            </label>

            <label className={`format-option ${exportFormat === 'geojson' ? 'format-option--selected' : ''}`}>
              <input
                type="radio"
                name="format"
                value="geojson"
                checked={exportFormat === 'geojson'}
                onChange={() => setExportFormat('geojson')}
                disabled={isExporting}
              />
              <div className="format-option__content">
                <strong>GeoJSON Spatial Layer (.geojson)</strong>
                <span>WGS84 spatial points and metadata for GIS mapping software.</span>
              </div>
            </label>

            <label className={`format-option ${exportFormat === 'json' ? 'format-option--selected' : ''}`}>
              <input
                type="radio"
                name="format"
                value="json"
                checked={exportFormat === 'json'}
                onChange={() => setExportFormat('json')}
                disabled={isExporting}
              />
              <div className="format-option__content">
                <strong>Raw JSON Summary (.json)</strong>
                <span>Complete detection payload snapshot.</span>
              </div>
            </label>
          </div>

          {exportStatus && (
            <p className="modal-status-text" style={{ marginTop: '12px', fontSize: '0.8rem', color: '#58a6ff' }}>
              {exportStatus}
            </p>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn--secondary btn--sm" onClick={onClose} disabled={isExporting}>
            Cancel
          </button>
          <button type="button" className="btn btn--primary btn--sm" onClick={handleDownload} disabled={isExporting}>
            {isExporting ? 'Generating...' : 'Download Report'}
          </button>
        </div>
      </div>
    </div>
  )
}