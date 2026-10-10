import React, { useState, useEffect, useCallback, useMemo } from 'react'
import TopBar from './components/TopBar/TopBar'
import Sidebar from './components/Sidebar/Sidebar'
import SonarView from './components/SonarView/SonarView'
import TargetInspector from './components/TargetInspector/TargetInspector'
import TargetLog from './components/TargetLog/TargetLog'
import HistoryPanel from './components/HistoryPanel'
import AnalyticsPanel from './components/AnalyticsPanel'
import ReportModal from './components/ReportModal'
import UploadDropzone from './components/UploadDropzone'
import ProcessingStatus from './components/ProcessingStatus'
import ErrorBoundary from './components/ErrorBoundary'
import ErrorBanner from './components/ErrorBanner'
import {
  checkHealth,
  getModelStatus,
  detectFileAsync,
  detectReferenceScanAsync,
  updateDetectionReview,
  renderSonarImageBlob,
} from './api/client'
import { useWebSocket } from './hooks/useWebSocket'
import { DEFAULT_SONAR_IMAGE } from './mock/mockData'

/**
 * Normalizes raw inference results from YOLOv11s backend into typed application detections
 */
function normalizeDetections(rawDetections, defaultImage) {
  if (!rawDetections || !Array.isArray(rawDetections)) return []
  return rawDetections.map((d, i) => {
    const detId = d.detection_id || `det_${String(i + 1).padStart(3, '0')}`
    const className = d.class_name || d.type || 'anomaly'
    const prettyClass = className.replace(/_/g, ' ').toUpperCase()
    const conf = Number(d.confidence != null ? d.confidence : d.modelScore ?? 0.0)

    let bboxNorm = { x: 0.2, y: 0.2, w: 0.08, h: 0.12 }
    if (d.bbox) {
      const xmin = d.bbox.x_min ?? d.bbox.x ?? 0.2
      const ymin = d.bbox.y_min ?? d.bbox.y ?? 0.2
      const xmax = d.bbox.x_max != null ? d.bbox.x_max : xmin + (d.bbox.w ?? 0.08)
      const ymax = d.bbox.y_max != null ? d.bbox.y_max : ymin + (d.bbox.h ?? 0.12)
      bboxNorm = {
        x: Math.max(0, Math.min(1, xmin)),
        y: Math.max(0, Math.min(1, ymin)),
        w: Math.max(0.01, Math.min(1, xmax - xmin)),
        h: Math.max(0.01, Math.min(1, ymax - ymin)),
      }
    }

    const channel = d.geotag?.channel || (bboxNorm.x < 0.5 ? 'port' : 'starboard')

    return {
      id: detId,
      type: className,
      class: prettyClass,
      confidence: conf,
      modelScore: conf,
      roi: channel,
      side: channel,
      status: d.review_status || d.status || 'Detected',
      bbox: bboxNorm,
      geotag: d.geotag || null,
      thumbnailUrl: d.thumbnailUrl || defaultImage,
    }
  })
}

export default function App() {
  // ── Navigation tabs ────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('LIVE')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [logCollapsed, setLogCollapsed] = useState(false)
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [isExportOpen, setIsExportOpen] = useState(false)
  const [isUploadOpen, setIsUploadOpen] = useState(false)

  // ── File upload & real-time detection state ─────────────────────
  const [selectedFile, setSelectedFile] = useState(null)
  const [imageUrl, setImageUrl] = useState(DEFAULT_SONAR_IMAGE)
  const [isProcessing, setIsProcessing] = useState(false)
  const [stageMessage, setStageMessage] = useState('')
  const [hasUploadedScan, setHasUploadedScan] = useState(false)
  const [hasInitializedScan, setHasInitializedScan] = useState(false)

  // ── Backend health & model status ───────────────────────────────
  const [backendStatus, setBackendStatus] = useState('checking')
  const [modelReady, setModelReady] = useState(false)
  const [apiError, setApiError] = useState(null)

  // ── Display settings (applied dynamically on canvas) ──────────
  const [displaySettings, setDisplaySettings] = useState({
    colorMap: 'MytisBronze',
    brightness: 0,
    contrast: 0,
  })

  // ── Functional AI detection filters ─────────────────────────────
  const [minConfidence, setMinConfidence] = useState(0.20)
  const [selectedClasses, setSelectedClasses] = useState([])

  // ── Navigation telemetry (starts honest null for static imagery) ─
  const [navData, setNavData] = useState(null)
  const [dgpsFix, setDgpsFix] = useState(false)

  // ── Targets / detections (starts empty until real inference runs) 
  const [targets, setTargets] = useState([])
  const [selectedTargetId, setSelectedTargetId] = useState(null)
  const [activeJobId, setActiveJobId] = useState(null)

  // ── Crop acoustic region around detected bounding box ───────────
  const generateDetectionCrops = useCallback(async (rawDetections, imageSrc) => {
    if (!imageSrc || !rawDetections?.length || typeof document === 'undefined') return rawDetections

    return new Promise((resolve) => {
      const img = new Image()
      if (!imageSrc.startsWith('blob:') && !imageSrc.startsWith('data:')) {
        img.crossOrigin = 'anonymous'
      }
      img.onload = () => {
        const iw = img.naturalWidth || img.width
        const ih = img.naturalHeight || img.height

        const enriched = rawDetections.map((d) => {
          try {
            const bbox = d.bbox || {}
            const xmin = bbox.x ?? 0.2
            const ymin = bbox.y ?? 0.2
            const wFrac = bbox.w ?? 0.08
            const hFrac = bbox.h ?? 0.12

            const x = Math.max(0, xmin * iw)
            const y = Math.max(0, ymin * ih)
            const w = Math.max(10, wFrac * iw)
            const h = Math.max(10, hFrac * ih)

            const padX = w * 0.25
            const padY = h * 0.25
            const sx = Math.max(0, x - padX)
            const sy = Math.max(0, y - padY)
            const sw = Math.min(iw - sx, w + padX * 2)
            const sh = Math.min(ih - sy, h + padY * 2)

            const canvas = document.createElement('canvas')
            canvas.width = 180
            canvas.height = 130
            const ctx = canvas.getContext('2d')
            ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height)
            return {
              ...d,
              thumbnailUrl: canvas.toDataURL('image/jpeg', 0.85),
            }
          } catch {
            return d
          }
        })
        resolve(enriched)
      }
      img.onerror = () => resolve(rawDetections)
      img.src = imageSrc
    })
  }, [])

  // ── WebSocket for active job status & live updates ─────────────
  useWebSocket(activeJobId, {
    onMessage: async (msg) => {
      if (msg.status === 'completed' && msg.detections?.length) {
        const mapped = normalizeDetections(msg.detections, imageUrl || DEFAULT_SONAR_IMAGE)
        const enriched = await generateDetectionCrops(mapped, imageUrl || DEFAULT_SONAR_IMAGE)
        setTargets(enriched)
        if (enriched[0]) setSelectedTargetId(enriched[0].id)
      }
    },
    onNav: (nav) => {
      if (nav && (nav.latitude != null || nav.depth != null)) {
        setNavData(nav)
        setDgpsFix(!!nav.dgpsFix)
      }
    },
    onStage: (stage) => setStageMessage(stage),
  })

  // ── Run real YOLO inference pipeline on an image or file ─────────
  const runInference = useCallback(async (imageSrc, fileObj = null) => {
    setIsProcessing(true)
    setStageMessage(fileObj ? 'Uploading sonar scan to YOLOv11s inference pipeline...' : 'Analyzing reference sonar scan with YOLOv11s...')
    setApiError(null)

    try {
      let result
      if (fileObj) {
        result = await detectFileAsync(fileObj, {
          onStageChange: (stage) => setStageMessage(stage),
          onJobRegistered: (jobId) => setActiveJobId(jobId),
        })
      } else {
        result = await detectReferenceScanAsync({
          onStageChange: (stage) => setStageMessage(stage),
          onJobRegistered: (jobId) => setActiveJobId(jobId),
        })
      }

      if (result?.detections && result.detections.length > 0) {
        const mapped = normalizeDetections(result.detections, imageSrc)
        const enriched = await generateDetectionCrops(mapped, imageSrc)
        setTargets(enriched)
        if (enriched[0]) setSelectedTargetId(enriched[0].id)
      } else {
        setTargets([])
        setSelectedTargetId(null)
      }
      setIsUploadOpen(false)
    } catch (err) {
      console.error('Inference error:', err)
      setApiError({
        code: err.code || 'API_ERROR',
        message: err.message === 'Failed to fetch'
          ? 'Cannot connect to backend server at http://127.0.0.1:8000. Ensure the backend is running.'
          : err.message || 'Detection failed.',
        details: err.details,
      })
    } finally {
      setIsProcessing(false)
    }
  }, [generateDetectionCrops])

  // ── Backend health & model probe (fast startup polling) ────────
  useEffect(() => {
    let mounted = true
    async function probe() {
      try {
        const health = await checkHealth()
        if (mounted) {
          setBackendStatus(health.status === 'ok' ? 'online' : 'degraded')
          setApiError((prev) => (prev?.code === 'API_ERROR' ? null : prev))
        }
        try {
          const mStatus = await getModelStatus()
          if (mounted) setModelReady(!!mStatus.model_ready)
        } catch {
          if (mounted) setModelReady(false)
        }
      } catch {
        if (mounted) {
          if (window.electronAPI?.checkBackend) {
            const isAlive = await window.electronAPI.checkBackend().catch(() => false)
            if (isAlive) {
              setBackendStatus('online')
              setApiError((prev) => (prev?.code === 'API_ERROR' ? null : prev))
              return
            }
          }
          setBackendStatus('offline')
          setModelReady(false)
        }
      }
    }
    probe()
    const t = setInterval(probe, 2500)
    return () => { mounted = false; clearInterval(t) }
  }, [])

  // ── Auto-run real YOLO inference on default scan on boot ────────
  useEffect(() => {
    if (backendStatus === 'online' && !hasInitializedScan && !hasUploadedScan) {
      setHasInitializedScan(true)
      runInference(DEFAULT_SONAR_IMAGE, null)
    }
  }, [backendStatus, hasInitializedScan, hasUploadedScan, runInference])

  // ── Filtered targets based on confidence & class ────────────────
  const filteredTargets = useMemo(() => {
    return targets.filter(t => {
      const score = t.confidence ?? t.modelScore ?? 0.0
      if (score < minConfidence) return false
      if (selectedClasses.length > 0 && !selectedClasses.includes(t.type)) return false
      return true
    })
  }, [targets, minConfidence, selectedClasses])

  // Count by class for filter badges
  const classCounts = useMemo(() => {
    return targets.reduce((acc, t) => {
      const k = t.type || 'unknown'
      acc[k] = (acc[k] || 0) + 1
      return acc
    }, {})
  }, [targets])

  // Currently selected target object
  const selectedTarget = useMemo(() => {
    return targets.find(t => t.id === selectedTargetId) || filteredTargets[0] || null
  }, [targets, selectedTargetId, filteredTargets])

  // ── Handlers ───────────────────────────────────────────────────
  const handleToggleClass = useCallback((classKey) => {
    setSelectedClasses(prev => {
      if (prev.includes(classKey)) return prev.filter(c => c !== classKey)
      return [...prev, classKey]
    })
  }, [])

  // Real persistence of operator verification decisions to backend SQLite
  const handleUpdateTargetStatus = useCallback(async (targetId, newStatus) => {
    setTargets(prev => prev.map(t => (t.id === targetId ? { ...t, status: newStatus } : t)))

    if (activeJobId) {
      try {
        await updateDetectionReview(activeJobId, targetId, newStatus)
      } catch (err) {
        console.warn('Could not persist operator review to database:', err)
      }
    }
  }, [activeJobId])

  const handleHistoryJob = useCallback((jobData) => {
    if (!jobData) return
    setActiveJobId(jobData.job_id)
    if (jobData.detections?.length) {
      const mapped = normalizeDetections(jobData.detections, DEFAULT_SONAR_IMAGE)
      setTargets(mapped)
      if (mapped[0]) setSelectedTargetId(mapped[0].id)
    } else {
      setTargets([])
      setSelectedTargetId(null)
    }
    setIsHistoryOpen(false)
  }, [])

  // Process user uploaded file: load image and run YOLO detection pipeline
  const handleFileSelected = useCallback(async (file) => {
    if (!file) return
    setSelectedFile(file)
    setHasUploadedScan(true)

    const isImage = /\.(png|jpe?g|webp|bmp|tiff?)$/i.test(file.name)
    if (isImage) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const previewUrl = e.target.result
        setImageUrl(previewUrl)
        runInference(previewUrl, file)
      }
      reader.onerror = () => {
        const fallbackUrl = URL.createObjectURL(file)
        setImageUrl(fallbackUrl)
        runInference(fallbackUrl, file)
      }
      reader.readAsDataURL(file)
    } else {
      try {
        const waterfallBlob = await renderSonarImageBlob(file)
        const waterfallUrl = URL.createObjectURL(waterfallBlob)
        setImageUrl(waterfallUrl)
        runInference(waterfallUrl, file)
      } catch (err) {
        console.warn('Could not generate waterfall from sonar log, using default scan preview:', err)
        runInference(DEFAULT_SONAR_IMAGE, file)
      }
    }
  }, [runInference])

  // Reset back to sample reference scan with real model inference
  const handleResetDemo = useCallback(() => {
    setSelectedFile(null)
    setHasUploadedScan(false)
    setImageUrl(DEFAULT_SONAR_IMAGE)
    runInference(DEFAULT_SONAR_IMAGE, null)
  }, [runInference])

  const isConnected = backendStatus === 'online'

  return (
    <ErrorBoundary>
      <div className="tarang-shell">
        {/* 1. TOP BAR */}
        <TopBar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          isConnected={isConnected}
          modelReady={modelReady}
          isProcessing={isProcessing}
          onOpenUpload={() => setIsUploadOpen(true)}
          onFileSelected={handleFileSelected}
          onOpenExport={() => setIsExportOpen(true)}
          onOpenHistory={() => setIsHistoryOpen(true)}
        />

        {/* 2. MAIN WORKSPACE */}
        {activeTab === 'ANALYSIS' ? (
          <div className="tarang-body tarang-body--analytics">
            <AnalyticsPanel detections={targets} />
          </div>
        ) : (
          <div className="tarang-body">
            {/* Left: Controls & Telemetry */}
            <Sidebar
              collapsed={sidebarCollapsed}
              onToggleCollapse={() => setSidebarCollapsed(c => !c)}
              displaySettings={displaySettings}
              onDisplayChange={s => setDisplaySettings(p => ({ ...p, ...s }))}
              minConfidence={minConfidence}
              onConfidenceChange={setMinConfidence}
              selectedClasses={selectedClasses}
              onToggleClass={handleToggleClass}
              classCounts={classCounts}
              navData={navData}
              dgpsFix={dgpsFix}
            />

            {/* Center: Sonar Display (Dominant workspace) */}
            <SonarView
              targets={filteredTargets}
              selectedTargetId={selectedTargetId}
              onSelectTarget={setSelectedTargetId}
              displaySettings={displaySettings}
              imageUrl={imageUrl}
              onFileSelected={handleFileSelected}
              onResetDemo={handleResetDemo}
              isProcessing={isProcessing}
              stageMessage={stageMessage}
              hasUploadedScan={hasUploadedScan}
              sourceFileName={selectedFile?.name}
            />

            {/* Right: Anomaly Details & Verification */}
            <TargetInspector
              selectedTarget={selectedTarget}
              targets={targets}
              onUpdateTargetStatus={handleUpdateTargetStatus}
              onOpenExport={() => setIsExportOpen(true)}
              onOpenUpload={() => setIsUploadOpen(true)}
              onFileSelected={handleFileSelected}
            />
          </div>
        )}

        {/* 3. BOTTOM TARGET DETECTION LOG */}
        <TargetLog
          targets={filteredTargets}
          selectedTargetId={selectedTargetId}
          onSelectTarget={setSelectedTargetId}
          onUpdateTargetStatus={handleUpdateTargetStatus}
          collapsed={logCollapsed}
          onToggleCollapse={() => setLogCollapsed(c => !c)}
        />

        {/* 4. MODALS */}
        {apiError && (
          <div style={{ position: 'fixed', bottom: 80, right: 16, zIndex: 9999, width: 340 }}>
            <ErrorBanner error={apiError} onDismiss={() => setApiError(null)} />
          </div>
        )}

        <HistoryPanel
          isOpen={isHistoryOpen}
          onClose={() => setIsHistoryOpen(false)}
          onSelectJob={handleHistoryJob}
          currentJobId={activeJobId}
        />

        {isExportOpen && (
          <ReportModal
            detections={targets}
            fileName={selectedFile?.name || 'SONNET_SURVEY_01'}
            onClose={() => setIsExportOpen(false)}
          />
        )}

        {isUploadOpen && (
          <div className="modal-overlay" onClick={() => setIsUploadOpen(false)}>
            <div className="portal-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 540 }}>
              <div className="portal-modal__header">
                <div className="modal-title-group">
                  <span className="modal-badge">YOLOv11 DETECTION PIPELINE</span>
                  <h3>Process Sonar Survey File (.xtf, .jsf, image)</h3>
                </div>
                <button type="button" className="modal-close-btn" onClick={() => setIsUploadOpen(false)}>
                  &times;
                </button>
              </div>
              <div className="portal-modal__body">
                <UploadDropzone
                  onFileSelected={handleFileSelected}
                  selectedFile={selectedFile}
                  isProcessing={isProcessing}
                  onStartDetection={() => {
                    if (selectedFile) handleFileSelected(selectedFile)
                  }}
                />
                {isProcessing && (
                  <ProcessingStatus
                    stageMessage={stageMessage}
                    onCancel={() => setIsProcessing(false)}
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  )
}