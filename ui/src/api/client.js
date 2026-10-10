/**
 * Team Synora - Backend API Client
 * Interfaces with FastAPI endpoints conforming to docs/api-contract.md
 */

export const API_BASE_URL = 'http://127.0.0.1:8000'

/**
 * Derives the WebSocket URL for streaming job status updates
 * @param {string} jobId
 * @returns {string}
 */
export function getWebSocketUrl(jobId) {
  const wsBase = API_BASE_URL.replace(/^http:/i, 'ws:').replace(/^https:/i, 'wss:')
  return `${wsBase}/api/v1/jobs/${jobId}/ws`
}

export const getJobWebSocketUrl = getWebSocketUrl

/**
 * Standard error shape parser
 * @param {Response} response
 * @returns {Promise<Error>}
 */
async function parseError(response) {
  let errorData
  try {
    errorData = await response.json()
  } catch {
    errorData = null
  }

  const code = errorData?.error?.code || `HTTP_${response.status}`
  const message = errorData?.error?.message || response.statusText || 'An unexpected error occurred'
  const details = errorData?.error?.details || {}

  const err = new Error(message)
  err.code = code
  err.status = response.status
  err.details = details
  return err
}

/**
 * 1. Health Endpoint: GET /health
 * @param {AbortSignal} [signal]
 * @returns {Promise<{status: string}>}
 */
export async function checkHealth(signal) {
  const response = await fetch(`${API_BASE_URL}/health`, { signal })
  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}

/**
 * GET /api/v1/model/status
 * @param {AbortSignal} [signal]
 * @returns {Promise<{model_name: string, model_ready: boolean, model_loaded: boolean, classes: string[]}>}
 */
export async function getModelStatus(signal) {
  const response = await fetch(`${API_BASE_URL}/api/v1/model/status`, { signal })
  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}

/**
 * 2. Start Detection Endpoint: POST /api/v1/detect
 * Dispatches multipart/form-data upload with 'file'.
 * Returns job_id and status: "processing_async".
 * @param {File} file
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal]
 * @returns {Promise<{job_id: string, status: string, detections: Array}>}
 */
export async function initiateDetection(file, { signal } = {}) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/v1/detect`, {
    method: 'POST',
    body: formData,
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  return response.json()
}

/**
 * 3. Poll Job Status Endpoint (Fallback & Inspection): GET /api/v1/jobs/{job_id}
 * @param {string} jobId
 * @param {AbortSignal} [signal]
 * @returns {Promise<{job_id: string, status: string, detections: Array, error?: any}>}
 */
export async function getJobStatus(jobId, signal) {
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, { signal })
  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}

/**
 * 4. Real-Time Detection with Native WebSocket Push Streaming (Phase 4)
 * Completely eliminates HTTP polling; receives live status events pushed by backend ws_manager.
 * Cleanly closes the WebSocket upon job completion, failure, or user AbortSignal.
 *
 * @param {File} file
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal]
 * @param {(stage: string, meta?: any) => void} [options.onStageChange]
 * @param {(jobId: string) => void} [options.onJobRegistered]
/**
 * Streams job status and detections via WebSocket until completion
 * @param {string} jobId
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal]
 * @param {(stage: string, meta?: any) => void} [options.onStageChange]
 * @returns {Promise<{job_id: string, status: string, detections: Array}>}
 */
export async function streamJobResult(jobId, { signal, onStageChange } = {}) {
  const wsUrl = getWebSocketUrl(jobId)

  return new Promise((resolve, reject) => {
    let ws = null
    let isFinished = false

    const cleanup = () => {
      if (signal) {
        signal.removeEventListener('abort', onAbort)
      }
      if (ws) {
        try {
          if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
            ws.close(1000, 'Job finished or aborted')
          }
        } catch {
          // Ignore close errors
        }
        ws = null
      }
    }

    const onAbort = () => {
      isFinished = true
      cleanup()
      reject(new DOMException('Operation aborted by user', 'AbortError'))
    }

    if (signal?.aborted) {
      onAbort()
      return
    }

    if (signal) {
      signal.addEventListener('abort', onAbort)
    }

    try {
      ws = new WebSocket(wsUrl)
    } catch (err) {
      cleanup()
      reject(err)
      return
    }

    ws.onopen = () => {
      if (isFinished) return
      onStageChange?.('WebSocket stream connected. Awaiting real-time inference...', { jobId })
    }

    ws.onmessage = (event) => {
      if (isFinished) return
      try {
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data

        if (data.status === 'processing' || data.status === 'processing_async') {
          onStageChange?.(data.stage || 'YOLO neural network analyzing side-scan sonar rungs...', {
            jobId,
            status: data.status,
          })
          return
        }

        if (data.status === 'completed') {
          isFinished = true
          onStageChange?.('Inference completed! Rendering detections and geotags...', {
            jobId,
            status: 'completed',
          })
          cleanup()
          resolve(data)
          return
        }

        if (data.status === 'failed') {
          isFinished = true
          cleanup()
          const err = new Error(data.error?.message || 'Detection job failed on backend.')
          err.code = data.error?.code || 'JOB_FAILED'
          err.details = data.error?.details || {}
          reject(err)
          return
        }
      } catch (parseErr) {
        // Ignore non-JSON or ping frames
      }
    }

    ws.onerror = (event) => {
      if (isFinished) return
      console.warn('WebSocket encountered error, preparing fallback check:', event)
    }

    ws.onclose = (event) => {
      if (isFinished) return
      if (signal?.aborted) return

      isFinished = true
      cleanup()

      getJobStatus(jobId, signal)
        .then((fallbackData) => {
          if (fallbackData.status === 'completed') {
            resolve(fallbackData)
          } else {
            reject(new Error(`WebSocket connection closed (code: ${event.code}).`))
          }
        })
        .catch(() => {
          reject(new Error(`WebSocket connection closed (code: ${event.code}).`))
        })
    }
  })
}

/**
 * 4. Real-Time Detection with Native WebSocket Push Streaming (Phase 4)
 * @param {File} file
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal]
 * @param {(stage: string, meta?: any) => void} [options.onStageChange]
 * @param {(jobId: string) => void} [options.onJobRegistered]
 * @returns {Promise<{job_id: string, status: string, detections: Array}>}
 */
export async function detectFileAsync(
  file,
  { signal, onStageChange, onJobRegistered } = {}
) {
  onStageChange?.('Uploading sonar payload and registering async job...')

  const initResult = await initiateDetection(file, { signal })
  const jobId = initResult.job_id

  if (!jobId) {
    return initResult
  }

  onJobRegistered?.(jobId)
  onStageChange?.(`Job registered (${jobId}). Opening real-time WebSocket connection...`, { jobId })

  return await streamJobResult(jobId, { signal, onStageChange })
}

/**
 * Executes inference on the backend reference sonar shipwreck scan asset
 * @param {Object} [options]
 * @param {AbortSignal} [options.signal]
 * @param {(stage: string, meta?: any) => void} [options.onStageChange]
 * @param {(jobId: string) => void} [options.onJobRegistered]
 * @returns {Promise<{job_id: string, status: string, detections: Array}>}
 */
export async function detectReferenceScanAsync({ signal, onStageChange, onJobRegistered } = {}) {
  onStageChange?.('Requesting YOLOv11s inference on reference sonar scan...')

  const response = await fetch(`${API_BASE_URL}/api/v1/detect/reference`, {
    method: 'POST',
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  const initResult = await response.json()
  const jobId = initResult.job_id

  if (!jobId) {
    return initResult
  }

  onJobRegistered?.(jobId)
  onStageChange?.(`Job registered (${jobId}). Opening real-time WebSocket connection...`, { jobId })

  return await streamJobResult(jobId, { signal, onStageChange })
}

/**
 * 5. Report Generation Endpoint: POST /api/v1/reports/generate (B1)
 * @param {'csv' | 'geojson'} format
 * @param {Array} detections
 * @param {AbortSignal} [signal]
 * @returns {Promise<Blob>}
 */
export async function generateReportApi(format, detections, signal) {
  const response = await fetch(`${API_BASE_URL}/api/v1/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      format: format,
      detections: detections,
    }),
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }

  return response.blob()
}

/**
 * 6. Sonar Log Upload: POST /api/v1/sonar/upload
 * @param {File} file
 * @param {AbortSignal} [signal]
 */
export async function uploadSonarLog(file, signal) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/v1/sonar/upload`, {
    method: 'POST',
    body: formData,
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}

/**
 * 7. Geotagging Endpoint: POST /api/v1/geotag
 * @param {Object} detection
 * @param {Array} pingMetadata
 * @param {AbortSignal} [signal]
 */
export async function geotagDetection(detection, pingMetadata, signal) {
  const response = await fetch(`${API_BASE_URL}/api/v1/geotag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ detection, ping_metadata: pingMetadata }),
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}
/**
 * 8. Historical Jobs API: GET /api/v1/jobs (B1)
 * Retrieves paginated list of past detection jobs
 * @param {Object} [options]
 * @param {number} [options.skip=0]
 * @param {number} [options.limit=50]
 * @param {string} [options.status]
 * @param {AbortSignal} [signal]
 * @returns {Promise<{items: Array, total: number, skip: number, limit: number}>}
 */
export async function getHistoricalJobs({ skip = 0, limit = 50, status = null } = {}, signal) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  if (status) {
    params.set('status', status)
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/jobs?${params.toString()}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}

/**
 * 9. Sonar Image Renderer: POST /api/v1/sonar/render-image
 * Uploads an .xtf or .jsf and receives the generated waterfall PNG blob
 * @param {File} file
 * @param {AbortSignal} [signal]
 * @returns {Promise<Blob>}
 */
export async function renderSonarImageBlob(file, signal) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/v1/sonar/render-image`, {
    method: 'POST',
    body: formData,
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }
  return response.blob()
}

/**
 * 10. Persist Operator Detection Review: PATCH /api/v1/jobs/{job_id}/detections/{detection_id}/review
 * @param {string} jobId
 * @param {string} detectionId
 * @param {'confirmed' | 'flagged' | 'rejected' | 'unreviewed'} reviewStatus
 * @param {string|null} [notes]
 * @param {AbortSignal} [signal]
 * @returns {Promise<{status: string, detection: Object}>}
 */
export async function updateDetectionReview(jobId, detectionId, reviewStatus, notes = null, signal) {
  if (!jobId || !detectionId) return null
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/detections/${detectionId}/review`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      review_status: reviewStatus,
      operator_notes: notes,
    }),
    signal,
  })

  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}