from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer, StandardScaler

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.csv"
MODEL_PATH = BASE_DIR / "geoai_fusion_model.pkl"
METRICS_PATH = BASE_DIR / "geoai_fusion_metrics.json"
PREDICTIONS_PATH = BASE_DIR / "geoai_fusion_predictions.csv"


def temporal_features(series: pd.Series) -> np.ndarray:
    dt = pd.to_datetime(series, errors="coerce")
    dt = dt.fillna(pd.Timestamp("2026-01-01"))
    # Cyclic features retain temporal periodicity.
    month = dt.dt.month.to_numpy(dtype=float)
    dow = dt.dt.dayofweek.to_numpy(dtype=float)
    day = dt.dt.day.to_numpy(dtype=float)
    return np.column_stack([
        np.sin(2 * np.pi * month / 12.0),
        np.cos(2 * np.pi * month / 12.0),
        np.sin(2 * np.pi * dow / 7.0),
        np.cos(2 * np.pi * dow / 7.0),
        day / 31.0,
    ])


def dense_features(df: pd.DataFrame) -> np.ndarray:
    spatial = df[["lat", "lon"]].astype(float).to_numpy()
    temporal = temporal_features(df["time"])
    return np.column_stack([spatial, temporal])


def build_matrix(df: pd.DataFrame, vectorizer: TfidfVectorizer, scaler: StandardScaler, fit: bool):
    text = df["text"].fillna("").astype(str)
    x_text = vectorizer.fit_transform(text) if fit else vectorizer.transform(text)
    x_dense_raw = dense_features(df)
    x_dense = scaler.fit_transform(x_dense_raw) if fit else scaler.transform(x_dense_raw)
    return hstack([x_text, csr_matrix(x_dense)], format="csr")


def main() -> None:
    started = time.perf_counter()
    df = pd.read_csv(DATASET_PATH).dropna(subset=["text", "category", "lat", "lon", "time"]).copy()
    if len(df) < 20:
        raise ValueError("GeoAI fusion modeli uchun kamida 20 ta belgilangan yozuv kerak.")

    train_df, test_df = train_test_split(
        df,
        test_size=0.30,
        random_state=42,
        stratify=df["category"].astype(str),
    )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    scaler = StandardScaler()
    x_train = build_matrix(train_df, vectorizer, scaler, fit=True)
    x_test = build_matrix(test_df, vectorizer, scaler, fit=False)
    y_train = train_df["category"].astype(str).to_numpy()
    y_test = test_df["category"].astype(str).to_numpy()

    classifier = RandomForestClassifier(
        n_estimators=400,
        random_state=42,
        class_weight="balanced_subsample",
        min_samples_leaf=1,
        n_jobs=-1,
    )
    classifier.fit(x_train, y_train)
    y_pred = classifier.predict(x_test)
    y_prob = classifier.predict_proba(x_test)
    classes = classifier.classes_.tolist()

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted", zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=classes)
    report = classification_report(y_test, y_pred, labels=classes, output_dict=True, zero_division=0)

    lb = LabelBinarizer()
    lb.fit(classes)
    y_bin = lb.transform(y_test)
    if len(classes) == 2:
        y_bin = np.column_stack([1 - y_bin.ravel(), y_bin.ravel()])
    roc_series = []
    per_class_auc = {}
    for idx, label in enumerate(classes):
        if idx >= y_bin.shape[1] or len(np.unique(y_bin[:, idx])) < 2:
            continue
        fpr, tpr, _ = roc_curve(y_bin[:, idx], y_prob[:, idx])
        auc = roc_auc_score(y_bin[:, idx], y_prob[:, idx])
        per_class_auc[label] = float(auc)
        # Reduce payload while preserving the curve.
        step = max(1, len(fpr) // 60)
        roc_series.append({
            "label": label,
            "auc": float(auc),
            "fpr": [float(x) for x in fpr[::step]],
            "tpr": [float(x) for x in tpr[::step]],
        })
    try:
        macro_auc = float(roc_auc_score(y_bin, y_prob, average="macro", multi_class="ovr"))
    except ValueError:
        macro_auc = 0.0

    text_names = vectorizer.get_feature_names_out().tolist()
    dense_names = ["latitude", "longitude", "month_sin", "month_cos", "weekday_sin", "weekday_cos", "day_norm"]
    feature_names = text_names + dense_names
    importances = classifier.feature_importances_
    top_idx = np.argsort(importances)[::-1][:20]
    top_features = [
        {"feature": feature_names[int(i)], "importance": float(importances[int(i)])}
        for i in top_idx
    ]
    group_importance = {
        "semantic": float(importances[: len(text_names)].sum()),
        "spatial": float(importances[len(text_names): len(text_names) + 2].sum()),
        "temporal": float(importances[len(text_names) + 2:].sum()),
    }

    version = f"geoai-fusion-2.1-{datetime.now():%Y%m%d%H%M%S}"
    trained_at = datetime.now().isoformat(timespec="seconds")

    bundle = {
        "vectorizer": vectorizer,
        "scaler": scaler,
        "classifier": classifier,
        "classes": classes,
        "version": version,
    }
    joblib.dump(bundle, MODEL_PATH)

    metrics = {
        "algorithm_version": version,
        "trained_at": trained_at,
        "training_duration_seconds": float(time.perf_counter() - started),
        "dataset_size": int(len(df)),
        "train_size": int(len(train_df)),
        "test_size": int(len(test_df)),
        "classes": classes,
        "accuracy": float(accuracy),
        "precision_weighted": float(precision),
        "recall_weighted": float(recall),
        "f1_weighted": float(f1),
        "roc_auc_macro_ovr": macro_auc,
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "roc_series": roc_series,
        "per_class_auc": per_class_auc,
        "top_features": top_features,
        "group_importance": group_importance,
    }
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    output = test_df[["text", "lat", "lon", "time", "category"]].copy()
    output["predicted"] = y_pred
    output["confidence"] = y_prob.max(axis=1)
    output.to_csv(PREDICTIONS_PATH, index=False)

    print("GeoAI fusion modeli tayyorlandi.")
    print(f"Accuracy: {accuracy:.4f}; F1: {f1:.4f}; ROC-AUC: {macro_auc:.4f}")
    print(f"Model: {MODEL_PATH}")
    print(f"Metrics: {METRICS_PATH}")


if __name__ == "__main__":
    main()
