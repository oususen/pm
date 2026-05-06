import os
import random
import shutil
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from PIL import Image


class CameraShapeTrainingManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._status = {
            "state": "idle",
            "message": "未実行",
            "started_at": None,
            "finished_at": None,
            "dataset_dir": "",
            "model_path": "",
        }
        self._thread = None

    @staticmethod
    def _base_dir():
        return Path(__file__).resolve().parents[3] / "media" / "camera_shape"

    def get_status(self):
        with self._lock:
            return dict(self._status)

    def upload_dataset_zip(self, uploaded_file):
        base = self._base_dir()
        zip_dir = base / "uploads"
        extract_dir = base / "dataset"
        zip_dir.mkdir(parents=True, exist_ok=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        zip_path = zip_dir / "dataset.zip"
        with zip_path.open("wb+") as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        data_yaml = extract_dir / "data.yaml"
        if not data_yaml.exists():
            candidates = list(extract_dir.rglob("data.yaml"))
            if candidates:
                data_yaml = candidates[0]
            else:
                raise ValueError("ZIP内に data.yaml が見つかりません。YOLOデータセット形式でアップロードしてください。")

        with self._lock:
            self._status["dataset_dir"] = str(data_yaml.parent)
            self._status["message"] = "データセットアップロード完了"

        return str(data_yaml.parent)

    def append_raw_images(self, files, label_name: str):
        label_name = (label_name or "").strip()
        if not label_name:
            raise ValueError("label_name は必須です。")
        base = self._base_dir()
        dataset_dir = base / "dataset"
        images_train = dataset_dir / "images" / "train"
        images_val = dataset_dir / "images" / "val"
        labels_train = dataset_dir / "labels" / "train"
        labels_val = dataset_dir / "labels" / "val"
        for p in [images_train, images_val, labels_train, labels_val]:
            p.mkdir(parents=True, exist_ok=True)

        class_index, names = self._ensure_class(dataset_dir, label_name)

        saved_count = 0
        for f in files:
            name = getattr(f, "name", "")
            ext = Path(name).suffix.lower()
            if ext not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                continue
            split = "val" if random.random() < 0.2 else "train"
            img_dir = images_val if split == "val" else images_train
            lbl_dir = labels_val if split == "val" else labels_train
            stem = f"{label_name}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{saved_count}"
            img_path = img_dir / f"{stem}{ext}"
            with img_path.open("wb+") as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            try:
                with Image.open(img_path) as im:
                    im.verify()
            except Exception:
                img_path.unlink(missing_ok=True)
                continue
            # 写真全体を1ボックスとして自動ラベル化（PoC）
            (lbl_dir / f"{stem}.txt").write_text(f"{class_index} 0.5 0.5 1.0 1.0\n", encoding="utf-8")
            saved_count += 1

        self._write_data_yaml(dataset_dir, names)
        with self._lock:
            self._status["dataset_dir"] = str(dataset_dir)
            self._status["message"] = f"写真取込完了: {saved_count}枚"
        return saved_count

    def _ensure_class(self, dataset_dir: Path, label_name: str):
        yaml_path = dataset_dir / "data.yaml"
        names = []
        if yaml_path.exists():
            text = yaml_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if ":" in line and line.strip() and line.strip()[0].isdigit():
                    _, val = line.split(":", 1)
                    names.append(val.strip().strip("'").strip('"'))
        if label_name not in names:
            names.append(label_name)
        return names.index(label_name), names

    @staticmethod
    def _write_data_yaml(dataset_dir: Path, names):
        lines = [
            f"path: {str(dataset_dir).replace('\\', '/')}",
            "train: images/train",
            "val: images/val",
            "names:",
        ]
        for idx, name in enumerate(names):
            lines.append(f"  {idx}: {name}")
        (dataset_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def start_training(self, *, epochs, imgsz, base_model="yolov8n.pt"):
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("学習はすでに実行中です。")
            dataset_dir = self._status.get("dataset_dir") or ""
            if not dataset_dir:
                raise ValueError("先に学習データZIPをアップロードしてください。")
            self._status.update(
                {
                    "state": "running",
                    "message": "学習実行中",
                    "started_at": datetime.now().isoformat(),
                    "finished_at": None,
                    "model_path": "",
                }
            )

        self._thread = threading.Thread(
            target=self._run_training,
            kwargs={"dataset_dir": dataset_dir, "epochs": int(epochs), "imgsz": int(imgsz), "base_model": base_model},
            daemon=True,
        )
        self._thread.start()

    def _run_training(self, *, dataset_dir, epochs, imgsz, base_model):
        try:
            settings_dir = Path(__file__).resolve().parents[3] / ".ultralytics"
            settings_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("YOLO_CONFIG_DIR", str(settings_dir))
            from ultralytics import YOLO

            runs_dir = self._base_dir() / "runs"
            runs_dir.mkdir(parents=True, exist_ok=True)
            model = YOLO(base_model)
            result = model.train(
                data=str(Path(dataset_dir) / "data.yaml"),
                epochs=epochs,
                imgsz=imgsz,
                project=str(runs_dir),
                name="shape_train",
                exist_ok=True,
            )
            best_path = str(Path(result.save_dir) / "weights" / "best.pt")
            with self._lock:
                self._status.update(
                    {
                        "state": "completed",
                        "message": "学習完了",
                        "finished_at": datetime.now().isoformat(),
                        "model_path": best_path,
                    }
                )
        except Exception as exc:
            with self._lock:
                self._status.update(
                    {
                        "state": "failed",
                        "message": f"学習失敗: {exc}",
                        "finished_at": datetime.now().isoformat(),
                    }
                )


camera_shape_training_manager = CameraShapeTrainingManager()
