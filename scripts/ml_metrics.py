"""Compute rich, honest ML metrics for the README + slide deck."""
import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (average_precision_score, classification_report,
                             confusion_matrix, precision_recall_curve,
                             roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from app import ml

X, y = ml._build_features()
print("dataset:", X.shape, "positives:", int(y.sum()), "base rate:", round(y.mean(), 4))

feat_names = ["hour_sin", "hour_cos", "weekday", "is_weekend", "corridor_volume",
              "priority_high", "heavy_vehicle"] + [f"cause::{c}" for c in ml._CAUSES]

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
clf = RandomForestClassifier(n_estimators=200, max_depth=12, min_samples_leaf=6,
                             class_weight="balanced", n_jobs=-1, random_state=42)
clf.fit(X_tr, y_tr)
proba = clf.predict_proba(X_te)[:, 1]

auc = roc_auc_score(y_te, proba)
ap = average_precision_score(y_te, proba)
print("\nHoldout AUC:", round(auc, 4), "| Avg precision:", round(ap, 4))
print("Lift over base rate:", round(ap / y.mean(), 2), "x")

# 5-fold stratified CV for stability.
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_auc = cross_val_score(clf, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
cv_ap = cross_val_score(clf, X, y, cv=cv, scoring="average_precision", n_jobs=-1)
print(f"\n5-fold CV AUC: {cv_auc.mean():.3f} +/- {cv_auc.std():.3f}")
print(f"5-fold CV AP : {cv_ap.mean():.3f} +/- {cv_ap.std():.3f}")

# Operating point: choose threshold maximising F1.
prec, rec, thr = precision_recall_curve(y_te, proba)
f1 = 2 * prec * rec / (prec + rec + 1e-9)
best = int(np.nanargmax(f1[:-1]))
t = float(thr[best])
pred = (proba >= t).astype(int)
print(f"\nBest-F1 threshold: {t:.3f} | precision {prec[best]:.3f} recall {rec[best]:.3f} F1 {f1[best]:.3f}")
print("\nConfusion matrix @ best-F1 (rows=true 0/1, cols=pred 0/1):")
print(confusion_matrix(y_te, pred))
print("\n", classification_report(y_te, pred, target_names=["no closure", "closure"]))

print("Feature importances (top 10):")
imp = sorted(zip(feat_names, clf.feature_importances_), key=lambda x: -x[1])
for n, v in imp[:10]:
    print(f"  {n:<22} {v:.3f}")

out = {
    "n_samples": int(X.shape[0]), "n_features": int(X.shape[1]),
    "positives": int(y.sum()), "base_rate": round(float(y.mean()), 4),
    "holdout_auc": round(float(auc), 3), "avg_precision": round(float(ap), 3),
    "lift": round(float(ap / y.mean()), 1),
    "cv_auc_mean": round(float(cv_auc.mean()), 3), "cv_auc_std": round(float(cv_auc.std()), 3),
    "cv_ap_mean": round(float(cv_ap.mean()), 3), "cv_ap_std": round(float(cv_ap.std()), 3),
    "f1_threshold": round(t, 3), "precision": round(float(prec[best]), 3),
    "recall": round(float(rec[best]), 3), "f1": round(float(f1[best]), 3),
    "top_features": [(n, round(float(v), 3)) for n, v in imp[:6]],
}
print("\nJSON:", json.dumps(out))
