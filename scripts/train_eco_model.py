"""Train from labelled field CSV; spatial AND temporal holdout, portable JSON artifact."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
from gaia.services.eco_model import FEATURES  # noqa: E402


def train(csv_path, kind, label_definition, output, min_rows=100):
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        roc_auc_score,
        average_precision_score,
        brier_score_loss,
        balanced_accuracy_score,
    )

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig", newline="")))
    fields = FEATURES[kind]
    required = {"site_id", "observed_at", "risk_label", *fields}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Required CSV columns: " + ", ".join(sorted(required)))
    if len(rows) < min_rows:
        raise ValueError(f"At least {min_rows} labelled observations are required; more are usually needed")
    dates = [datetime.fromisoformat(r["observed_at"].replace("Z", "+00:00")).date() for r in rows]
    sites = sorted({r["site_id"].strip() for r in rows}, key=lambda s: hashlib.sha256(s.encode()).hexdigest())
    if len(sites) < 10 or "" in sites:
        raise ValueError("At least 10 distinct nonempty site_id values required")
    test_sites = set(sites[: max(2, len(sites) // 5)])
    cutoff = sorted(dates)[int(len(dates) * 0.7)]
    train_idx = [
        i for i, r in enumerate(rows) if r["site_id"].strip() not in test_sites and dates[i] < cutoff
    ]
    test_idx = [i for i, r in enumerate(rows) if r["site_id"].strip() in test_sites and dates[i] >= cutoff]
    x = np.array([[float(r[f]) for f in fields] for r in rows])
    y = np.array([float(r["risk_label"]) for r in rows])
    if not np.isfinite(x).all() or not set(y).issubset({0, 1}):
        raise ValueError("Finite numeric features and risk_label 0/1 are required")
    if len(train_idx) < 40 or len(test_idx) < 20 or len(set(y[train_idx])) != 2 or len(set(y[test_idx])) != 2:
        raise ValueError(
            "Insufficient observations/classes after spatial-temporal split; collect additional sites and dates"
        )
    model = RandomForestClassifier(
        n_estimators=120, max_depth=8, min_samples_leaf=4, class_weight="balanced", random_state=42, n_jobs=-1
    )
    model.fit(x[train_idx], y[train_idx])
    p = model.predict_proba(x[test_idx])[:, 1]
    report = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "label_definition": label_definition,
        "dataset_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "rows": len(rows),
        "train_rows": len(train_idx),
        "test_rows": len(test_idx),
        "excluded_rows": len(rows) - len(train_idx) - len(test_idx),
        "test_sites": sorted(test_sites),
        "cutoff": str(cutoff),
        "roc_auc": float(roc_auc_score(y[test_idx], p)),
        "average_precision": float(average_precision_score(y[test_idx], p)),
        "brier_score": float(brier_score_loss(y[test_idx], p)),
        "balanced_accuracy": float(balanced_accuracy_score(y[test_idx], p >= 0.5)),
        "feature_importance": dict(zip(fields, model.feature_importances_.tolist(), strict=True)),
        "status": "research_only",
        "validation": "Distinct holdout sites at later dates; independent external validation still required",
    }
    trees = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        values = tree.value[:, 0, :]
        trees.append(
            {
                "left": tree.children_left.tolist(),
                "right": tree.children_right.tolist(),
                "feature": tree.feature.tolist(),
                "threshold": tree.threshold.tolist(),
                "probability": (values[:, 1] / values.sum(axis=1)).tolist(),
            }
        )
    artifact = {
        "features": fields,
        "ranges": [[float(x[train_idx, i].min()), float(x[train_idx, i].max())] for i in range(len(fields))],
        "trees": trees,
        "report": report,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("Output exists. Keep the old version and choose a new output path.")
    output.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
    output.with_suffix(".report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--kind", required=True, choices=list(FEATURES))
    parser.add_argument("--label-definition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            train(args.data, args.kind, args.label_definition, args.output), ensure_ascii=False, indent=2
        )
    )
