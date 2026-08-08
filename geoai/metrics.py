from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings


def load_fusion_metrics() -> dict:
    path = Path(settings.BASE_DIR) / "ml" / "geoai_fusion_metrics.json"
    if not path.exists():
        return {
            "available": False,
            "message": "GeoAI fusion modeli hali o‘qitilmagan.",
            "classes": [],
            "confusion_matrix": [],
            "classification_rows": [],
            "roc_series": [],
            "top_features": [],
            "group_importance": {},
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    report = data.get("classification_report", {})
    for label in data.get("classes", []):
        row = report.get(label, {})
        rows.append({
            "label": label,
            "precision": row.get("precision", 0),
            "recall": row.get("recall", 0),
            "f1": row.get("f1-score", 0),
            "support": row.get("support", 0),
        })
    data["classification_rows"] = rows
    data["confusion_rows"] = [
        {"label": label, "values": values}
        for label, values in zip(data.get("classes", []), data.get("confusion_matrix", []))
    ]
    data["available"] = True
    # Small labelled sample warning is intentionally explicit for scientific honesty.
    data["sample_warning"] = data.get("dataset_size", 0) < 200
    return data
