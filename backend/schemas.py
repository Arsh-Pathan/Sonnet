from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Dict, Any, Union
from datetime import datetime

class GeoJSONPoint(BaseModel):
    latitude: float
    longitude: float

class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"
    coordinates_wgs84: List[List[Tuple[float, float]]]
    centroid_wgs84: GeoJSONPoint

class GeotagMetrics(BaseModel):
    across_track_width_m: float
    along_track_length_m: float
    center_ground_range_m: float
    sensor_altitude_m: float
    uncertainty_radius_m: float
    quality_flag: str

class GeotaggedDetection(BaseModel):
    detection_id: str
    label: str
    confidence: float
    channel: str
    status: str
    geometry: GeoJSONPolygon
    metrics: GeotagMetrics

class GeotagRequest(BaseModel):
    detection: Dict[str, Any] = Field(..., description="YOLO AI detection output")
    ping_metadata: List[Dict[str, Any]] = Field(..., description="Ping metadata from sonar log")

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail

class BoundingBox(BaseModel):
    x_min: float = Field(..., ge=0.0, le=1.0)
    y_min: float = Field(..., ge=0.0, le=1.0)
    x_max: float = Field(..., ge=0.0, le=1.0)
    y_max: float = Field(..., ge=0.0, le=1.0)

class SimpleGeotag(BaseModel):
    latitude: float
    longitude: float
    depth_meters: Optional[float] = None

class DetectionResult(BaseModel):
    detection_id: str
    class_name: str = Field(..., description="E.g., plastic, metal, fishing_net, tire, shipwreck, unknown")
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BoundingBox
    geotag: Optional[Union[SimpleGeotag, GeotaggedDetection, Dict[str, Any]]] = None

class DetectResponse(BaseModel):
    job_id: Optional[str] = None
    status: str
    detections: List[DetectionResult] = Field(default_factory=list)

from typing import Literal

class ReportRequest(BaseModel):
    format: Literal["csv", "geojson"] = Field(..., description="The format of the report to generate")
    detections: List[DetectionResult] = Field(..., description="List of detections to include in the report")

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    detections: List[DetectionResult] = Field(default_factory=list)
    error: Optional[ErrorDetail] = None

class FusedTarget(BaseModel):
    fused_id: str
    label: str
    max_confidence: float
    center_wgs84: GeoJSONPoint
    contributing_detection_ids: List[str]
    cluster_radius_m: float

class FuseRequest(BaseModel):
    detections: List[GeotaggedDetection]
    distance_threshold_m: float = Field(15.0, description="Max distance in meters to cluster targets together")

class FuseResponse(BaseModel):
    fused_targets: List[FusedTarget]

class JobHistorySummary(BaseModel):
    job_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    detection_count: int

class PaginatedHistoryResponse(BaseModel):
    items: List[JobHistorySummary]
    skip: int
    limit: int
    total: Optional[int] = None

class ReviewUpdateRequest(BaseModel):
    review_status: str = Field(..., description="'confirmed', 'flagged', 'rejected', or 'unreviewed'")
    operator_notes: Optional[str] = None

