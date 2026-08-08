from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from django.conf import settings


ML_DIR = Path(settings.BASE_DIR) / "ml"
METRICS_PATH = ML_DIR / "geoai_fusion_metrics.json"
HISTORY_PATH = ML_DIR / "geoai_model_history.json"
LOCK_PATH = ML_DIR / ".geoai_retrain.lock"
TRAIN_SCRIPT = ML_DIR / "train_geoai_fusion.py"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def load_model_history() -> list[dict]:
    history = _read_json(HISTORY_PATH, [])
    return history if isinstance(history, list) else []


def latest_model_comparison() -> dict:
    history = load_model_history()
    if not history:
        return {}
    return history[-1]


def retrain_geoai_model(timeout_seconds: int = 900) -> dict:
    """Run the project training script and persist an auditable old/new comparison."""
    if LOCK_PATH.exists():
        raise RuntimeError("Modelni qayta o‘qitish jarayoni allaqachon ishlamoqda.")
    if not TRAIN_SCRIPT.exists():
        raise FileNotFoundError(f"Trening skripti topilmadi: {TRAIN_SCRIPT}")

    previous = _read_json(METRICS_PATH, {})
    started_at = datetime.now()
    LOCK_PATH.write_text(started_at.isoformat(), encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(TRAIN_SCRIPT)],
            cwd=str(settings.BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "Noma’lum trening xatosi").strip()
            raise RuntimeError(message[-3000:])

        current = _read_json(METRICS_PATH, {})
        if not current:
            raise RuntimeError("Trening yakunlandi, ammo metrikalar fayli yaratilmagan.")

        metric_keys = [
            "accuracy",
            "precision_weighted",
            "recall_weighted",
            "f1_weighted",
            "roc_auc_macro_ovr",
        ]
        changes = {}
        for key in metric_keys:
            old = float(previous.get(key, 0.0) or 0.0)
            new = float(current.get(key, 0.0) or 0.0)
            changes[key] = {"old": old, "new": new, "delta": new - old}

        record = {
            "retrained_at": datetime.now().isoformat(timespec="seconds"),
            "previous_version": previous.get("algorithm_version", "—"),
            "current_version": current.get("algorithm_version", "—"),
            "dataset_size": current.get("dataset_size", 0),
            "train_size": current.get("train_size", 0),
            "test_size": current.get("test_size", 0),
            "training_duration_seconds": current.get("training_duration_seconds", 0.0),
            "changes": changes,
            "stdout": completed.stdout.strip()[-1500:],
        }
        history = load_model_history()
        history.append(record)
        HISTORY_PATH.write_text(
            json.dumps(history[-30:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return record
    finally:
        LOCK_PATH.unlink(missing_ok=True)
