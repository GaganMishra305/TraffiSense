"""Machine-learning layer.

Trains a RandomForest on the real ASTraM incidents to predict an operationally
useful, non-trivial outcome: **will an incident require a road closure?**
(676 closures vs 7,381 non-closures -- a genuinely imbalanced, real problem).

The predictor uses this learned closure propensity to ground its event
forecasts in evidence. Trained once and cached; an honest holdout AUC is
exposed so the UI can show a truthful "model card".
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from . import data

# Causes we one-hot encode; everything else folds into "other".
_CAUSES = ["vehicle_breakdown", "accident", "water_logging", "tree_fall",
           "pot_holes", "construction", "road_conditions", "congestion"]
_HEAVY = {"heavy_vehicle", "truck", "lcv"}


@lru_cache(maxsize=1)
def corridor_volume_lookup() -> Dict[str, float]:
    """Corridor -> log-normalised incident volume (0-1). Public: the
    predictor reuses it so its features match the model's."""
    df = data.load_incidents()
    counts = df["corridor"].value_counts()
    logc = np.log1p(counts.to_numpy(dtype=float))
    norm = logc / logc.max()
    return dict(zip(counts.index, norm))


def _row_features(hour, weekday, corridor_vol, is_high, cause, heavy):
    is_weekend = 1 if weekday >= 5 else 0
    cause_oh = [1 if cause == c else 0 for c in _CAUSES]
    return [
        np.sin(2 * np.pi * hour / 24),
        np.cos(2 * np.pi * hour / 24),
        weekday,
        is_weekend,
        corridor_vol,
        1 if is_high else 0,
        1 if heavy else 0,
        *cause_oh,
    ]


def _build_features() -> tuple[np.ndarray, np.ndarray]:
    df = data.load_incidents()
    vol = corridor_volume_lookup()
    rows = []
    for _, r in df.iterrows():
        rows.append(_row_features(
            r["hour"], r["weekday"], vol.get(r["corridor"], 0.1),
            r["is_high"], r["event_cause"],
            str(r.get("veh_type")) in _HEAVY,
        ))
    X = np.array(rows, dtype=float)
    y = df["closure"].astype(int).to_numpy()
    return X, y


@lru_cache(maxsize=1)
def get_model() -> Dict:
    """Train + cache the closure-prediction model with honest holdout metrics."""
    X, y = _build_features()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=12, min_samples_leaf=6,
        class_weight="balanced", n_jobs=-1, random_state=42,
    )
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)[:, 1]
    try:
        auc = float(roc_auc_score(y_te, proba))
        ap = float(average_precision_score(y_te, proba))
    except ValueError:
        auc = ap = float("nan")
    return {
        "clf": clf,
        "auc": round(auc, 3),
        "avg_precision": round(ap, 3),
        "base_rate": round(float(y.mean()), 3),
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
    }


def closure_propensity(hour: int, weekday: int, corridor_volume: float,
                       high_priority: bool = True,
                       cause: str = "accident", heavy: bool = False) -> float:
    """Learned probability (0-1) that an incident in these conditions needs a
    road closure. The predictor calls this per affected corridor."""
    clf = get_model()["clf"]
    feat = np.array([_row_features(
        hour, weekday, max(0.0, min(corridor_volume, 1.0)),
        high_priority, cause, heavy,
    )])
    return float(clf.predict_proba(feat)[0, 1])


def model_card() -> Dict:
    """Human-facing summary of the trained model for the UI."""
    m = get_model()
    return {
        "algorithm": "RandomForest (200 trees, depth 12, class-balanced)",
        "target": "road-closure requirement",
        "holdout_auc": m["auc"],
        "avg_precision": m["avg_precision"],
        "base_rate": m["base_rate"],
        "train_samples": m["n_train"],
        "test_samples": m["n_test"],
        "features": ["hour (cyclical)", "weekday", "is_weekend",
                     "corridor_volume", "priority", "heavy_vehicle", "cause"],
    }
