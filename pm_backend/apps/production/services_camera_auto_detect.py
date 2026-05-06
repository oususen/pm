import base64
import math
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class DetectResult:
    detected_count: int
    pass_count: int
    shape_code: str
    shape_confidence: float | None


class AutoDetectRuntime:
    """YOLO推論 + 通過判定 + 重複防止（セッション単位のメモリ状態）。"""

    def __init__(self):
        self._model = None
        self._model_source = ""
        self._model_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._sessions = {}

    def _load_model(self):
        with self._model_lock:
            # 権限制限環境でも動くよう、Ultralytics設定ディレクトリをプロジェクト配下へ固定
            settings_dir = Path(__file__).resolve().parents[3] / ".ultralytics"
            settings_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("YOLO_CONFIG_DIR", str(settings_dir))
            try:
                from .services_camera_shape_training import camera_shape_training_manager
                model_path = camera_shape_training_manager.get_status().get("model_path") or ""
            except Exception:
                model_path = ""
            source = model_path if model_path and Path(model_path).exists() else "yolov8n.pt"
            if self._model is not None and self._model_source == source:
                return self._model
            try:
                from ultralytics import YOLO
            except Exception as exc:
                raise RuntimeError("ultralytics が未インストールのため自動検知を実行できません。") from exc
            self._model = YOLO(source)
            self._model_source = source
            return self._model

    @staticmethod
    def decode_frame(data_url: str):
        try:
            import cv2
            import numpy as np
        except Exception as exc:
            raise RuntimeError("opencv-python と numpy が未インストールのため自動検知を実行できません。") from exc
        encoded = data_url.split(",", 1)[1] if "," in data_url else data_url
        raw = base64.b64decode(encoded)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("フレーム画像のデコードに失敗しました。")
        return frame

    def process(self, session_id: str, frame_data_url: str, now_dt: datetime, config=None) -> DetectResult:
        config = config or {}
        frame = self.decode_frame(frame_data_url)
        height, width = frame.shape[:2]
        gray = None
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        except Exception:
            gray = None
        model = self._load_model()
        using_default_model = str(self._model_source).endswith("yolov8n.pt")
        yolo_confidence = float(config.get("yolo_confidence", 0.5))
        result = model.predict(frame, verbose=False, conf=yolo_confidence)[0]
        boxes = result.boxes

        detections = []
        top_shape_code = ""
        top_shape_confidence = None
        if boxes is not None:
            cls_ids = boxes.cls.cpu().numpy() if boxes.cls is not None else []
            confs = boxes.conf.cpu().numpy() if boxes.conf is not None else []
            names = result.names or {}
            for idx, xyxy in enumerate(boxes.xyxy.cpu().numpy()):
                class_id = int(cls_ids[idx]) if idx < len(cls_ids) else -1
                conf = float(confs[idx]) if idx < len(confs) else 0.0
                if not top_shape_code or (top_shape_confidence is not None and conf > top_shape_confidence):
                    top_shape_code = str(names.get(class_id, class_id))
                    top_shape_confidence = conf
                # 既定モデル時のみ person で絞る。学習済みモデル時は全クラス対象。
                if using_default_model and class_id != 0:
                    continue
                x1, y1, x2, y2 = [float(v) for v in xyxy]
                cx = (x1 + x2) / 2.0
                person_bottom_ratio = float(config.get("person_bottom_ratio", 0.78))
                min_y_ratio = float(config.get("min_y_ratio", 0.45))
                cy = y1 + (y2 - y1) * person_bottom_ratio
                if using_default_model and cy < height * min_y_ratio:
                    continue
                detections.append((cx, cy))

        line_position_ratio = float(config.get("line_position_ratio", 0.5))
        line_x = width * line_position_ratio
        assoc_threshold = max(48.0, width * 0.08)
        stale_sec = 5.0
        dedup_sec = float(config.get("dedup_seconds", 1.2))
        side_margin = max(20.0, width * float(config.get("side_margin_ratio", 0.03)))

        with self._state_lock:
            session = self._sessions.setdefault(
                session_id,
                {
                    "next_track_id": 1,
                    "tracks": {},
                    "last_gray": None,
                    "motion_side": None,
                    "last_motion_counted": None,
                    "motion_left_ema": 0.0,
                    "motion_right_ema": 0.0,
                },
            )
            tracks = session["tracks"]
            pass_count = 0

            stale_ids = []
            for tid, track in tracks.items():
                age = (now_dt - track["last_seen"]).total_seconds()
                if age > stale_sec:
                    stale_ids.append(tid)
            for tid in stale_ids:
                del tracks[tid]

            assigned = set()
            for cx, cy in detections:
                best_tid = None
                best_dist = None
                for tid, track in tracks.items():
                    if tid in assigned:
                        continue
                    px, py = track["center"]
                    dist = math.hypot(cx - px, cy - py)
                    if dist <= assoc_threshold and (best_dist is None or dist < best_dist):
                        best_tid = tid
                        best_dist = dist

                if best_tid is None:
                    best_tid = session["next_track_id"]
                    session["next_track_id"] += 1
                    if cx < line_x - side_margin:
                        side = "left"
                    elif cx > line_x + side_margin:
                        side = "right"
                    else:
                        side = "mid"
                    tracks[best_tid] = {"center": (cx, cy), "last_seen": now_dt, "last_counted": None, "side": side}
                    assigned.add(best_tid)
                    continue

                track = tracks[best_tid]
                prev_side = track.get("side", "mid")
                track["center"] = (cx, cy)
                track["last_seen"] = now_dt
                assigned.add(best_tid)

                if cx < line_x - side_margin:
                    current_side = "left"
                elif cx > line_x + side_margin:
                    current_side = "right"
                else:
                    current_side = "mid"
                crossed = (
                    prev_side in ("left", "right")
                    and current_side in ("left", "right")
                    and prev_side != current_side
                )
                track["side"] = current_side
                if crossed:
                    can_count = track["last_counted"] is None or (now_dt - track["last_counted"]).total_seconds() >= dedup_sec
                    if can_count:
                        track["last_counted"] = now_dt
                        pass_count += 1

            # YOLOで通過0件のときは、ライン左右の動体変化でフォールバック判定
            if pass_count == 0 and gray is not None:
                prev_gray = session.get("last_gray")
                if prev_gray is not None and prev_gray.shape == gray.shape:
                    import cv2
                    diff = cv2.absdiff(gray, prev_gray)
                    _, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                    x_mid = int(line_x)
                    band_w = max(18, int(width * 0.035))
                    left_band = mask[:, max(0, x_mid - band_w):x_mid]
                    right_band = mask[:, x_mid:min(width, x_mid + band_w)]
                    left_score = int(left_band.sum() // 255)
                    right_score = int(right_band.sum() // 255)
                    motion_threshold = max(40, int(height * band_w * float(config.get("motion_threshold_ratio", 0.01))))
                    alpha = 0.45
                    session["motion_left_ema"] = (1 - alpha) * float(session.get("motion_left_ema", 0.0)) + alpha * float(left_score)
                    session["motion_right_ema"] = (1 - alpha) * float(session.get("motion_right_ema", 0.0)) + alpha * float(right_score)
                    left_eval = session["motion_left_ema"]
                    right_eval = session["motion_right_ema"]
                    current_motion_side = None
                    dominance = max(12.0, motion_threshold * 0.15)
                    if left_eval >= motion_threshold and (left_eval - right_eval) >= dominance:
                        current_motion_side = "left"
                    elif right_eval >= motion_threshold and (right_eval - left_eval) >= dominance:
                        current_motion_side = "right"
                    prev_motion_side = session.get("motion_side")
                    crossed_motion = (
                        prev_motion_side in ("left", "right")
                        and current_motion_side in ("left", "right")
                        and prev_motion_side != current_motion_side
                    )
                    if crossed_motion:
                        last_motion_counted = session.get("last_motion_counted")
                        if last_motion_counted is None or (now_dt - last_motion_counted).total_seconds() >= dedup_sec:
                            pass_count += 1
                            session["last_motion_counted"] = now_dt
                    session["motion_side"] = current_motion_side
                session["last_gray"] = gray

        return DetectResult(
            detected_count=len(detections),
            pass_count=pass_count,
            shape_code=top_shape_code,
            shape_confidence=top_shape_confidence,
        )


auto_detect_runtime = AutoDetectRuntime()
