import pytest
import io
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.job_manager import AsyncJobManager

client = TestClient(app)

TAXONOMY = ["pipeline", "shipwreck", "mine_cylinder", "ghost_net", "crab_pot"]

async def mock_infer(*args, **kwargs):
    return [{
        "detection_id": "det_001",
        "class_name": "ghost_net",
        "confidence": 0.95,
        "bbox": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.3, "y_max": 0.4},
        "geotag": {"latitude": 45.1, "longitude": -12.4, "depth_meters": 15.0}
    }]

@patch("model.yolo_detector.YoloDetector.infer", new_callable=lambda: mock_infer)
def test_detect_endpoint_creates_job(mocked_infer):
    file_bytes = b"fake-png-content"
    response = client.post(
        "/api/v1/detect",
        files={"file": ("sonar_scan.png", io.BytesIO(file_bytes), "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["job_id"].startswith("job_")
    assert data["status"] == "processing_async"
    assert data["detections"] == []

def test_detect_endpoint_rejects_unsupported_format():
    file_bytes = b"fake-pdf-content"
    response = client.post(
        "/api/v1/detect",
        files={"file": ("report.pdf", io.BytesIO(file_bytes), "application/pdf")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_FILE"

def test_detect_endpoint_rejects_empty_file():
    file_bytes = b""
    response = client.post(
        "/api/v1/detect",
        files={"file": ("empty.png", io.BytesIO(file_bytes), "image/png")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "EMPTY_FILE"

def test_get_job_status_not_found():
    response = client.get("/api/v1/jobs/job_nonexistent_99999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "JOB_NOT_FOUND"

@patch("model.yolo_detector.YoloDetector.infer", new_callable=lambda: mock_infer)
def test_get_job_status_lifecycle(mocked_infer):
    file_bytes = b"sonar-log-data"
    post_res = client.post(
        "/api/v1/detect",
        files={"file": ("survey_01.xtf", io.BytesIO(file_bytes), "application/octet-stream")}
    )
    assert post_res.status_code == 200
    job_id = post_res.json()["job_id"]

    poll_res = client.get(f"/api/v1/jobs/{job_id}")
    assert poll_res.status_code == 200
    job_data = poll_res.json()
    assert job_data["job_id"] == job_id
    assert job_data["status"] in ["processing", "completed"]

@patch("model.yolo_detector.YoloDetector.infer", new_callable=lambda: mock_infer)
def test_job_websocket_status_streaming(mocked_infer):
    file_bytes = b"sonar-log-data"
    post_res = client.post(
        "/api/v1/detect",
        files={"file": ("survey_ws.png", io.BytesIO(file_bytes), "image/png")}
    )
    assert post_res.status_code == 200
    job_id = post_res.json()["job_id"]

    with client.websocket_connect(f"/api/v1/jobs/{job_id}/ws") as websocket:
        data = websocket.receive_json()
        assert data["job_id"] == job_id
        assert data["status"] in ["processing", "completed"]

@patch("model.yolo_detector.YoloDetector.infer", new_callable=lambda: mock_infer)
def test_job_websocket_root_alias(mocked_infer):
    file_bytes = b"sonar-log-data"
    post_res = client.post(
        "/api/v1/detect",
        files={"file": ("survey_ws_root.png", io.BytesIO(file_bytes), "image/png")}
    )
    assert post_res.status_code == 200
    job_id = post_res.json()["job_id"]

    with client.websocket_connect(f"/jobs/{job_id}/ws") as websocket:
        data = websocket.receive_json()
        assert data["job_id"] == job_id
        assert data["status"] in ["processing", "completed"]

@pytest.mark.anyio
async def test_job_manager_crud():
    mgr = AsyncJobManager()
    jid = await mgr.create_job()
    assert jid.startswith("job_")

    job = await mgr.get_job(jid)
    assert job is not None
    assert job.status == "pending"

    await mgr.update_job_status(jid, status="processing")
    job = await mgr.get_job(jid)
    assert job.status == "processing"

    sample_detections = [{
        "detection_id": "det_001",
        "class_name": "plastic",
        "confidence": 0.95,
        "bbox": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.3, "y_max": 0.4},
        "geotag": {"latitude": 45.1, "longitude": -12.4, "depth_meters": 15.0}
    }]
    await mgr.update_job_status(jid, status="completed", detections=sample_detections)
    job = await mgr.get_job(jid)
    assert job.status == "completed"
    assert len(job.detections) == 1

    # Test updating detection review status
    updated = await mgr.update_detection_review(jid, "det_001", "confirmed", "Verified by operator")
    assert updated is not None
    assert updated["review_status"] == "confirmed"
    assert updated["operator_notes"] == "Verified by operator"
    assert "reviewed_at" in updated

def test_patch_detection_review_api():
    # Test PATCH review endpoint
    response = client.patch(
        "/api/v1/jobs/nonexistent_job_123/detections/det_001/review",
        json={"review_status": "confirmed"}
    )
    assert response.status_code == 404