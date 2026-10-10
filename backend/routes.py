import os
import tempfile
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import (
    APIRouter,
    HTTPException,
    File,
    UploadFile,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    Query,
)

from backend.schemas import (
    GeotagRequest,
    GeotaggedDetection,
    DetectResponse,
    JobStatusResponse,
    ErrorResponse,
    ErrorDetail,
    DetectionResult,
    FuseRequest,
    FuseResponse,
    PaginatedHistoryResponse,
    JobHistorySummary,
    ReviewUpdateRequest,
)
from backend.geotagging import GeotaggingEngine, GeotagConfig
from backend.read_log import PingMetadata
from backend.job_manager import job_manager
from backend.fusion import GeospatialFuser
from backend.ws_manager import ws_manager
from model.yolo_detector import yolo_engine

router = APIRouter(prefix="/api/v1")
engine = GeotaggingEngine(GeotagConfig())

ALLOWED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.tiff', '.xtf', '.jsf')

@router.get("/model/status", tags=["Model"])
def get_model_status():
    weights_path = yolo_engine.weights_path
    weights_ok = os.path.exists(weights_path) and os.path.getsize(weights_path) > 1000
    return {
        "model_name": "YOLOv11s",
        "weights_path": weights_path,
        "model_ready": weights_ok,
        "model_loaded": yolo_engine.model is not None,
        "classes": ["pipeline", "shipwreck", "mine_cylinder", "ghost_net", "crab_pot"]
    }

@router.post("/geotag", tags=["Geotagging"], response_model=GeotaggedDetection)
def geotag_detection_endpoint(request: GeotagRequest):
    try:
        pings = []
        for p in request.ping_metadata:
            ts = p.get("timestamp")
            if isinstance(ts, str):
                p["timestamp"] = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            pings.append(PingMetadata(**p))

        result = engine.geotag_detection(request.detection, pings)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/detect",
    tags=["Detection"],
    response_model=DetectResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def detect_anomalies(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Initiates anomaly detection on an uploaded image or sonar log.
    Validates file extension and schedules asynchronous YOLO inference.
    """
    filename = file.filename or ""
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE",
                "message": f"Unsupported file format '{filename}'. Allowed formats: {list(ALLOWED_EXTENSIONS)}"
            }
        )

    file_content = await file.read()
    if len(file_content) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "EMPTY_FILE",
                "message": "The uploaded file is empty."
            }
        )
    await file.seek(0)

    ext = os.path.splitext(filename)[1].lower()
    fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(fd)

    with open(temp_path, "wb") as buffer:
        buffer.write(file_content)

    job_id = await job_manager.create_job()
    await job_manager.update_job_status(job_id, status="processing")

    async def execute_inference(jid: str, file_path: str):
        try:
            detections = await yolo_engine.infer(file_path)
            await job_manager.update_job_status(jid, status="completed", detections=detections)
        except Exception as exc:
            traceback.print_exc()
            await job_manager.update_job_status(
                jid,
                status="failed",
                error={"code": "INFERENCE_FAILED", "message": str(exc)}
            )
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    background_tasks.add_task(execute_inference, job_id, temp_path)

    return DetectResponse(
        job_id=job_id,
        status="processing_async",
        detections=[]
    )

@router.post(
    "/detect/reference",
    tags=["Detection"],
    response_model=DetectResponse,
    responses={500: {"model": ErrorResponse}}
)
async def detect_reference_scan(background_tasks: BackgroundTasks):
    """
    Runs YOLOv11s inference on the reference shipwreck sonar scan asset.
    Creates a real job and streams real detections over WebSocket.
    """
    ref_candidates = [
        os.path.join("ui", "src", "assets", "sonar_shipwreck_scan.jpg"),
        os.path.join(os.path.dirname(__file__), "..", "ui", "src", "assets", "sonar_shipwreck_scan.jpg"),
        os.path.join("assets", "sonar_shipwreck_scan.jpg"),
    ]
    ref_file = None
    for p in ref_candidates:
        if os.path.exists(p):
            ref_file = os.path.abspath(p)
            break

    if not ref_file:
        raise HTTPException(status_code=404, detail="Reference sonar scan asset not found.")

    job_id = await job_manager.create_job()
    await job_manager.update_job_status(job_id, status="processing")

    async def execute_reference_inference(jid: str, file_path: str):
        try:
            detections = await yolo_engine.infer(file_path)
            await job_manager.update_job_status(jid, status="completed", detections=detections)
        except Exception as exc:
            traceback.print_exc()
            await job_manager.update_job_status(
                jid,
                status="failed",
                error={"code": "INFERENCE_FAILED", "message": str(exc)}
            )

    background_tasks.add_task(execute_reference_inference, job_id, ref_file)

    return DetectResponse(
        job_id=job_id,
        status="processing_async",
        detections=[]
    )

@router.get(
    "/jobs/{job_id}",
    tags=["Detection"],
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}}
)
async def get_job_status(job_id: str):
    """
    Polls the status of an asynchronous detection job.
    Returns status: 'processing' or 'completed' along with detection results.
    """
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "JOB_NOT_FOUND",
                "message": f"Detection job with ID '{job_id}' not found."
            }
        )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        detections=[DetectionResult(**d) for d in job.detections] if job.detections else [],
        error=ErrorDetail(**job.error) if job.error else None
    )

@router.patch(
    "/jobs/{job_id}/detections/{detection_id}/review",
    tags=["Detection"],
    responses={404: {"model": ErrorResponse}}
)
async def update_detection_review_endpoint(
    job_id: str,
    detection_id: str,
    request: ReviewUpdateRequest
):
    """
    Persists operator verification decision for a specific detection.
    """
    updated = await job_manager.update_detection_review(
        job_id=job_id,
        detection_id=detection_id,
        review_status=request.review_status,
        notes=request.operator_notes
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "DETECTION_NOT_FOUND",
                "message": f"Detection '{detection_id}' in job '{job_id}' not found."
            }
        )
    return {"status": "ok", "detection": updated}

@router.post("/fuse", tags=["Fusion"], response_model=FuseResponse)
def fuse_detections_endpoint(request: FuseRequest):
    """
    Cluster overlapping or duplicate detections from multiple sonar passes 
    into unified geographical targets.
    """
    try:
        fused = GeospatialFuser.cluster_detections(
            request.detections, 
            threshold_m=request.distance_threshold_m
        )
        return FuseResponse(fused_targets=fused)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/jobs/{job_id}/ws")
async def job_status_websocket(websocket: WebSocket, job_id: str):
    """
    Real-time WebSocket endpoint that streams job status updates to the UI, 
    eliminating the need for the frontend to aggressively poll the REST API.
    """
    job = await job_manager.get_job(job_id)
    if not job:
        await websocket.close(code=4004, reason="Job not found")
        return

    await ws_manager.connect(websocket, job_id)

    try:
        await websocket.send_json({
            "job_id": job.job_id,
            "status": job.status,
            "detections": job.detections,
            "error": job.error
        })

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)

@router.get("/jobs", tags=["Jobs"], response_model=PaginatedHistoryResponse)
async def list_historical_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, gt=0, le=100),
    status: Optional[str] = None
):
    """
    Fetch a paginated list of historical detection jobs.
    """
    VALID_STATUSES = {'pending', 'processing', 'completed', 'failed'}
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status filter '{status}'. Must be one of: {sorted(VALID_STATUSES)}")
    try:
        jobs = await job_manager.get_jobs_history(skip=skip, limit=limit, status_filter=status)

        summaries = [
            JobHistorySummary(
                job_id=j.job_id,
                status=j.status,
                created_at=j.created_at,
                updated_at=j.updated_at,
                detection_count=len(j.detections) if j.detections else 0
            ) for j in jobs
        ]

        return PaginatedHistoryResponse(
            items=summaries,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
