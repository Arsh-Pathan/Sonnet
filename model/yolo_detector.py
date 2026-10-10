import asyncio
import os
import numpy as np
from typing import List, Dict, Any
from PIL import Image

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from backend.image_generator import SonarImageGenerator
from backend.read_log import read_sonar_file
from backend.geotagging import GeotaggingEngine, GeotagConfig
from model.image_tiler import extract_tiles

geotag_engine = GeotaggingEngine(GeotagConfig())

def _calculate_iou(box1: List[float], box2: List[float]) -> float:
    xa = max(box1[0], box2[0])
    ya = max(box1[1], box2[1])
    xb = min(box1[2], box2[2])
    yb = min(box1[3], box2[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / float(union) if union > 0 else 0.0

class YoloDetector:
    def __init__(self, weights_path: str = "model/weights/best.pt"):
        self.weights_path = weights_path
        self.model = None

    async def infer(self, file_path: str) -> List[Dict[str, Any]]:
        # Run CPU/GPU bound inference in a separate thread to prevent blocking FastAPI
        return await asyncio.to_thread(self._infer_sync, file_path)

    def _infer_sync(self, file_path: str) -> List[Dict[str, Any]]:
        # 1. Parse file (Sonar log or direct image)
        ext = os.path.splitext(file_path)[1].lower()
        parsed_log = None
        if ext in ['.png', '.jpg', '.jpeg', '.tiff']:
            try:
                img = Image.open(file_path).convert("RGB")
            except Exception as e:
                raise ValueError(f"Failed to read image file: {e}")
        else:
            parsed_log = read_sonar_file(file_path)
            if parsed_log.status == "ERROR":
                raise ValueError(f"Failed to parse sonar file: {', '.join(parsed_log.errors)}")
            img = SonarImageGenerator.generate_waterfall(parsed_log)

        img_array = np.array(img)

        # 2. Check if real YOLO weights are available
        has_weights = os.path.exists(self.weights_path) and os.path.getsize(self.weights_path) > 1000
        if YOLO is not None and has_weights:
            if self.model is None:
                self.model = YOLO(self.weights_path)

            raw_candidates = []

            # 2a. Full-frame prediction for large targets and global scene context
            try:
                full_results = self.model.predict(source=img, imgsz=640, conf=0.15, verbose=False)
                for result in full_results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        cls_name = result.names[cls_id]
                        raw_candidates.append({
                            "coords": [x1, y1, x2, y2],
                            "conf": conf,
                            "cls_name": cls_name,
                        })
            except Exception as e:
                pass

            # 2b. High-resolution tiled prediction for small benthic targets
            try:
                tiles = extract_tiles(img_array, tile_width=640, tile_height=640, overlap_x=64, overlap_y=64)
                for tile_info in tiles:
                    tile_img = Image.fromarray(tile_info["tile"])
                    results = self.model.predict(source=tile_img, imgsz=640, conf=0.15, verbose=False)

                    for result in results:
                        for box in result.boxes:
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            conf = float(box.conf[0])
                            cls_id = int(box.cls[0])
                            cls_name = result.names[cls_id]

                            tile_x = tile_info.get("x", tile_info.get("x_offset", 0))
                            tile_y = tile_info.get("y", tile_info.get("y_offset", 0))

                            gx1 = x1 + tile_x
                            gy1 = y1 + tile_y
                            gx2 = x2 + tile_x
                            gy2 = y2 + tile_y

                            raw_candidates.append({
                                "coords": [gx1, gy1, gx2, gy2],
                                "conf": conf,
                                "cls_name": cls_name,
                            })
            except Exception as e:
                pass

            # Non-Maximum Suppression across full-frame and tiled candidates
            raw_candidates.sort(key=lambda c: c["conf"], reverse=True)
            kept_candidates = []
            for cand in raw_candidates:
                duplicate = False
                for kept in kept_candidates:
                    if _calculate_iou(cand["coords"], kept["coords"]) > 0.45:
                        duplicate = True
                        break
                if not duplicate:
                    kept_candidates.append(cand)

            detections = []
            det_id_counter = 1
            mid_x = img.width / 2.0

            for cand in kept_candidates:
                gx1, gy1, gx2, gy2 = cand["coords"]
                conf = cand["conf"]
                cls_name = cand["cls_name"]

                norm_x_min = max(0.0, min(1.0, gx1 / img.width))
                norm_y_min = max(0.0, min(1.0, gy1 / img.height))
                norm_x_max = max(0.0, min(1.0, gx2 / img.width))
                norm_y_max = max(0.0, min(1.0, gy2 / img.height))

                channel = "port" if ((gx1 + gx2) / 2.0) < mid_x else "starboard"
                geotag_dict = None

                # Compute georeferencing using GeotaggingEngine if pings exist
                if parsed_log and parsed_log.pings:
                    try:
                        if channel == "port":
                            col_min = max(0, int(mid_x - gx2))
                            col_max = max(0, int(mid_x - gx1))
                        else:
                            col_min = max(0, int(gx1 - mid_x))
                            col_max = max(0, int(gx2 - mid_x))

                        row_min = max(0, int(gy1))
                        row_max = max(0, int(gy2))

                        res = geotag_engine.geotag_detection(
                            {
                                "detection_id": f"det_{det_id_counter:03d}",
                                "label": cls_name,
                                "confidence": round(conf, 3),
                                "channel": channel,
                                "bbox_pixels": [row_min, col_min, row_max, col_max]
                            },
                            parsed_log.pings
                        )
                        centroid = res.get("geometry", {}).get("centroid_wgs84", {})
                        metrics = res.get("metrics", {})
                        lat = centroid.get("latitude")
                        lon = centroid.get("longitude")
                        depth = metrics.get("sensor_altitude_m")
                        geotag_dict = {
                            "latitude": lat,
                            "longitude": lon,
                            "depth_meters": depth,
                            "channel": channel,
                            "status": res.get("status", "GEOTAGGED"),
                            "geometry": res.get("geometry"),
                            "metrics": metrics
                        }
                    except Exception:
                        geotag_dict = None

                detections.append({
                    "detection_id": f"det_{det_id_counter:03d}",
                    "class_name": cls_name,
                    "confidence": round(conf, 3),
                    "bbox": {
                        "x_min": round(norm_x_min, 4),
                        "y_min": round(norm_y_min, 4),
                        "x_max": round(norm_x_max, 4),
                        "y_max": round(norm_y_max, 4)
                    },
                    "geotag": geotag_dict
                })
                det_id_counter += 1

            if len(detections) > 0:
                return detections

        return []

yolo_engine = YoloDetector()
