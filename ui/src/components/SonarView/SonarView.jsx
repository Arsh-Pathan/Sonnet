import React, { useRef, useEffect, useState, useCallback } from 'react'
import { DEFAULT_SONAR_IMAGE } from '../../mock/mockData'
import './SonarView.css'

/**
 * Returns canvas filter string for display settings (brightness, contrast, colormap)
 */
function getCanvasFilter(displaySettings) {
  const brightness = displaySettings?.brightness ?? 0
  const contrast = displaySettings?.contrast ?? 0
  const bVal = Math.max(0.2, 1 + brightness / 100)
  const cVal = Math.max(0.2, 1 + contrast / 100)
  const cm = displaySettings?.colorMap || 'MytisBronze'

  switch (cm) {
    case 'Greyscale':
      return `grayscale(100%) brightness(${bVal}) contrast(${cVal})`
    case 'Hot':
      return `sepia(100%) saturate(300%) hue-rotate(330deg) brightness(${bVal * 1.05}) contrast(${cVal * 1.15})`
    case 'Copper':
      return `sepia(80%) saturate(200%) hue-rotate(345deg) brightness(${bVal}) contrast(${cVal})`
    case 'MultiBronze':
      return `sepia(90%) saturate(240%) hue-rotate(355deg) brightness(${bVal * 1.05}) contrast(${cVal * 1.1})`
    case 'MytisBronze':
    default:
      return `sepia(80%) saturate(180%) hue-rotate(350deg) brightness(${bVal}) contrast(${cVal})`
  }
}

export default function SonarView({
  targets = [],
  selectedTargetId,
  onSelectTarget,
  displaySettings,
  imageUrl,
  onFileSelected,
  onResetDemo,
  isProcessing,
  stageMessage,
  hasUploadedScan,
  sourceFileName,
}) {
  const canvasRef = useRef(null)
  const imgRef = useRef(null)
  const fileInputRef = useRef(null)
  const [zoom, setZoom] = useState(1)
  const [showOverlays, setShowOverlays] = useState(true)
  const [hoveredTargetId, setHoveredTargetId] = useState(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [imageDims, setImageDims] = useState({ width: 1376, height: 768 })

  const activeImageSrc = imageUrl || DEFAULT_SONAR_IMAGE

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file && onFileSelected) {
      onFileSelected(file)
    }
  }

  const handleFileInputChange = (e) => {
    const file = e.target.files?.[0]
    if (file && onFileSelected) {
      onFileSelected(file)
    }
    e.target.value = ''
  }

  // Draw acoustic sonar frame to canvas whenever image or display settings change
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let isMounted = true

    const img = new Image()
    if (!activeImageSrc.startsWith('blob:') && !activeImageSrc.startsWith('data:')) {
      img.crossOrigin = 'anonymous'
    }
    img.onerror = () => {
      console.warn('Failed to load sonar image:', activeImageSrc)
    }
    img.src = activeImageSrc

    img.onload = () => {
      if (!isMounted) return
      imgRef.current = img
      setImageDims({ width: img.naturalWidth || 1376, height: img.naturalHeight || 768 })

      const w = canvas.width
      const h = canvas.height
      ctx.clearRect(0, 0, w, h)
      ctx.filter = getCanvasFilter(displaySettings)
      ctx.drawImage(img, 0, 0, w, h)
      ctx.filter = 'none'
    }

    return () => {
      isMounted = false
    }
  }, [activeImageSrc, displaySettings])

  // Normalize targets for bounding box rendering with real detection IDs and coordinates
  const normalizedTargets = (targets || []).map((t, idx) => {
    let bx = 0, by = 0, bw = 0, bh = 0
    if (t.bbox) {
      if (t.bbox.x_min != null && t.bbox.x_max != null) {
        bx = t.bbox.x_min
        by = t.bbox.y_min
        bw = Math.max(0.012, t.bbox.x_max - t.bbox.x_min)
        bh = Math.max(0.015, t.bbox.y_max - t.bbox.y_min)
      } else {
        bx = t.bbox.x ?? 0.3
        by = t.bbox.y ?? 0.3
        bw = t.bbox.w ?? 0.05
        bh = t.bbox.h ?? 0.12
      }
    }
    return {
      ...t,
      id: t.id || t.detection_id || `det_${String(idx + 1).padStart(3, '0')}`,
      bbox: { x: bx, y: by, w: bw, h: bh },
      type: t.type || t.class_name || 'anomaly',
      class: t.class || (t.class_name ? t.class_name.replace(/_/g, ' ').toUpperCase() : 'ANOMALY'),
      confidence: Number(t.confidence ?? t.modelScore ?? 0.0),
      status: t.status || 'Detected',
    }
  })

  const confirmedCount = normalizedTargets.filter(
    t => t.status === 'Operator accepted' || t.status === 'Confirmed'
  ).length

  const displayName = sourceFileName || (hasUploadedScan ? 'Uploaded Sonar Scan' : 'Reference Shipwreck Scan (780 kHz)')

  return (
    <div
      className="sonar-view"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* 1. Header Toolbar */}
      <div className="sonar-view__titlebar">
        <div className="sonar-view__title-left">
          <span className="sonar-view__source-tag">SOURCE</span>
          <span className="sonar-view__title">{displayName}</span>
          <span className="sonar-view__dims">{imageDims.width} &times; {imageDims.height} px</span>
        </div>

        <div className="sonar-view__toolbar">
          <input
            ref={fileInputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.tiff,.xtf,.jsf"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
          />
          <button
            type="button"
            className="sonar-tb-btn sonar-tb-btn--primary"
            onClick={() => fileInputRef.current?.click()}
            title="Upload your own side-scan sonar image (.png, .jpg, .tiff) or raw survey log"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 4 }}>
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            UPLOAD SCAN
          </button>

          {hasUploadedScan && (
            <button
              type="button"
              className="sonar-tb-btn"
              onClick={onResetDemo}
              title="Reset to reference shipwreck scan"
            >
              REFERENCE SCAN
            </button>
          )}

          <span className="sonar-tb-sep" />

          <button
            type="button"
            className="sonar-tb-icon-btn"
            title="Zoom In"
            onClick={() => setZoom(z => Math.min(2.5, +(z + 0.2).toFixed(1)))}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="11" y1="8" x2="11" y2="14" /><line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </button>
          <button
            type="button"
            className="sonar-tb-icon-btn"
            title="Zoom Out"
            onClick={() => setZoom(z => Math.max(0.6, +(z - 0.2).toFixed(1)))}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </button>
          <button
            type="button"
            className="sonar-tb-icon-btn"
            title="Reset Zoom / Fit"
            onClick={() => setZoom(1)}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18" /><path d="M15 3v18" />
            </svg>
          </button>

          <span className="sonar-tb-sep" />

          <button
            type="button"
            className={`sonar-tb-btn ${showOverlays ? 'sonar-tb-btn--active' : ''}`}
            onClick={() => setShowOverlays(o => !o)}
            title="Toggle Target Bounding Boxes and Labels"
          >
            {showOverlays ? 'OVERLAYS: VISIBLE' : 'OVERLAYS: HIDDEN'}
          </button>
        </div>
      </div>

      {/* Drag & Drop Visual Indicator */}
      {isDragOver && (
        <div className="sonar-dropzone-overlay">
          <div className="sonar-dropzone-modal">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="sonar-dropzone-title">DROP SONAR IMAGE OR SURVEY LOG</span>
            <span className="sonar-dropzone-sub">YOLOv11s will process detections immediately</span>
          </div>
        </div>
      )}

      {/* Inference Progress Card */}
      {isProcessing && (
        <div className="sonar-analyzing-overlay">
          <div className="sonar-analyzing-card">
            <div className="sonar-analyzing-spinner" />
            <span className="sonar-analyzing-title">INFERENCE IN PROGRESS</span>
            <span className="sonar-analyzing-stage">{stageMessage || 'Running YOLOv11s inference pipeline...'}</span>
          </div>
        </div>
      )}

      {/* Zero Detections Notification */}
      {!isProcessing && normalizedTargets.length === 0 && (
        <div className="sonar-no-targets-badge">
          0 ANOMALIES DETECTED &bull; ADJUST CONFIDENCE THRESHOLD IN SIDEBAR OR LOAD SCAN
        </div>
      )}

      {/* 2. Hydrographic Ruler */}
      <div className="sonar-ruler">
        <span className="sonar-ruler__edge">PORT 100m</span>
        <span className="sonar-ruler__mark">-75m</span>
        <span className="sonar-ruler__mark">-50m</span>
        <span className="sonar-ruler__mark">-25m</span>
        <span className="sonar-ruler__nadir">NADIR 0m</span>
        <span className="sonar-ruler__mark">+25m</span>
        <span className="sonar-ruler__mark">+50m</span>
        <span className="sonar-ruler__mark">+75m</span>
        <span className="sonar-ruler__edge">100m STBD</span>
      </div>

      {/* 3. Stage: Canvas + Overlays */}
      <div className="sonar-view__stage" style={{ transform: `scale(${zoom})` }}>
        <canvas
          ref={canvasRef}
          className="sonar-view__canvas"
          width={1376}
          height={768}
        />

        {/* Channel Badges */}
        <div className="sonar-ch-badge sonar-ch-badge--port">PORT CHANNEL [CH 1]</div>
        <div className="sonar-ch-badge sonar-ch-badge--starboard">STARBOARD CHANNEL [CH 2]</div>

        {/* Confirmed Targets Badge */}
        <div className="sonar-confirmed-badge">
          DETECTIONS: {normalizedTargets.length} | CONFIRMED: {confirmedCount}
        </div>

        {/* Clean Detection Bounding Boxes & Reticles */}
        {showOverlays && (
          <>
            <svg className="sonar-view__overlay" viewBox="0 0 1 1" preserveAspectRatio="none">
              {normalizedTargets.map(t => {
                const { bbox, id } = t
                const isSelected = id === selectedTargetId
                const isHovered = id === hoveredTargetId

                const strokeColor = isSelected ? '#3b82f6' : isHovered ? '#60a5fa' : '#f59e0b'
                const strokeWidth = isSelected ? 0.0035 : 0.002
                const fillColor = isSelected ? 'rgba(59, 130, 246, 0.12)' : 'rgba(245, 158, 11, 0.04)'

                const cornerLenX = Math.min(0.02, bbox.w * 0.3)
                const cornerLenY = Math.min(0.025, bbox.h * 0.3)

                return (
                  <g
                    key={id}
                    className="sonar-det-reticle"
                    onClick={() => onSelectTarget?.(id)}
                    onMouseEnter={() => setHoveredTargetId(id)}
                    onMouseLeave={() => setHoveredTargetId(null)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Primary Bounding Box */}
                    <rect
                      x={bbox.x}
                      y={bbox.y}
                      width={bbox.w}
                      height={bbox.h}
                      fill={fillColor}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      vectorEffect="non-scaling-stroke"
                    />

                    {/* Corner Reinforcements for Selected Box */}
                    {isSelected && (
                      <>
                        <path
                          d={`M ${bbox.x + cornerLenX} ${bbox.y} L ${bbox.x} ${bbox.y} L ${bbox.x} ${bbox.y + cornerLenY}`}
                          fill="none"
                          stroke="#ffffff"
                          strokeWidth={0.004}
                          vectorEffect="non-scaling-stroke"
                        />
                        <path
                          d={`M ${bbox.x + bbox.w - cornerLenX} ${bbox.y} L ${bbox.x + bbox.w} ${bbox.y} L ${bbox.x + bbox.w} ${bbox.y + cornerLenY}`}
                          fill="none"
                          stroke="#ffffff"
                          strokeWidth={0.004}
                          vectorEffect="non-scaling-stroke"
                        />
                        <path
                          d={`M ${bbox.x} ${bbox.y + bbox.h - cornerLenY} L ${bbox.x} ${bbox.y + bbox.h} L ${bbox.x + cornerLenX} ${bbox.y + bbox.h}`}
                          fill="none"
                          stroke="#ffffff"
                          strokeWidth={0.004}
                          vectorEffect="non-scaling-stroke"
                        />
                        <path
                          d={`M ${bbox.x + bbox.w} ${bbox.y + bbox.h - cornerLenY} L ${bbox.x + bbox.w} ${bbox.y + bbox.h} L ${bbox.x + bbox.w - cornerLenX} ${bbox.y + bbox.h}`}
                          fill="none"
                          stroke="#ffffff"
                          strokeWidth={0.004}
                          vectorEffect="non-scaling-stroke"
                        />
                      </>
                    )}
                  </g>
                )
              })}
            </svg>

            {/* Clean Detection Labels */}
            {normalizedTargets.map(t => {
              const { bbox, id } = t
              const isSelected = id === selectedTargetId
              const isHovered = id === hoveredTargetId
              const labelType = t.class || (t.type ? t.type.toUpperCase().replace(/_/g, ' ') : 'ANOMALY')
              const confText = `${(t.confidence * 100).toFixed(1)}%`
              const sideText = t.side || (bbox.x < 0.5 ? 'PORT' : 'STBD')

              return (
                <div
                  key={id}
                  className={`sonar-label-chip ${isSelected ? 'sonar-label-chip--selected' : ''} ${isHovered ? 'sonar-label-chip--hovered' : ''}`}
                  style={{
                    left: `${Math.min(92, Math.max(1, bbox.x * 100))}%`,
                    top: `${Math.min(94, Math.max(1, bbox.y * 100))}%`,
                  }}
                  onClick={() => onSelectTarget?.(id)}
                  onMouseEnter={() => setHoveredTargetId(id)}
                  onMouseLeave={() => setHoveredTargetId(null)}
                >
                  <div className="sonar-chip-header">
                    <span className="sonar-chip-dot" />
                    <span className="sonar-chip-id">{id}</span>
                    <span className="sonar-chip-type">{labelType}</span>
                    <span className="sonar-chip-conf">{confText}</span>
                  </div>
                  {isSelected && (
                    <div className="sonar-chip-sub">
                      <span>{sideText} CH</span>
                      <span>&bull;</span>
                      <span>{t.status.toUpperCase()}</span>
                    </div>
                  )}
                </div>
              )
            })}
          </>
        )}

        {/* Bottom Status Ribbon */}
        <div className="sonar-bottom-status">
          ACOUSTIC SIDESCAN CHIRP | SLANT RANGE: 100m PORT / 100m STBD | PROCESSED VIA YOLOV11S
        </div>
      </div>
    </div>
  )
}
