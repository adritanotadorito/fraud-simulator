"""
retrain_models.py  —  Train XGBoost + IsolationForest on 9 derivable features.

These features can ALL be computed at inference time from a real / uploaded
transaction.  The old models depended on V1–V28 (Kaggle PCA columns) which
are impossible to derive for new data and led to a flat 0.0 risk score.

Usage:
    cd ml
    python retrain_models.py

Output:
    models/fraud_model.pkl          — XGBClassifier
    models/isolation_forest.pkl     — IsolationForest
"""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    classification_report,
)
from xgboost import XGBClassifier
from sklearn.ensemble import IsolationForest

# ── Feature list — must match backend/app/ml/xgboost_model.py::extract_features()
FEATURES = [
    "amount",
    "amount_zscore",
    "transaction_velocity",
    "time_diff",
    "device_change_flag",
    "geo_velocity",
    "biometric_deviation",
    "hour_of_day",
    "is_new_merchant",
]

RANDOM_SEED = 42
N_LEGIT = 19_400       # ~97 %
N_FRAUD = 600           # ~3 %
N_TOTAL = N_LEGIT + N_FRAUD


def generate_synthetic_dataset(seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Build a labeled DataFrame with realistic feature distributions."""
    rng = np.random.RandomState(seed)

    # ── Legitimate transactions ──────────────────────────────────────────
    legit = pd.DataFrame({
        "amount":               rng.lognormal(mean=3.2, sigma=1.0, size=N_LEGIT).clip(1, 5000),
        "transaction_velocity": rng.uniform(0.0, 0.35, N_LEGIT),
        "time_diff":            rng.uniform(5, 3600, N_LEGIT),
        "device_change_flag":   rng.choice([0, 1], N_LEGIT, p=[0.95, 0.05]).astype(float),
        "geo_velocity":         rng.uniform(0, 200, N_LEGIT),
        "biometric_deviation":  rng.uniform(0.02, 0.25, N_LEGIT),
        "hour_of_day":          rng.uniform(6, 22, N_LEGIT),
        "is_new_merchant":      rng.choice([0, 1], N_LEGIT, p=[0.90, 0.10]).astype(float),
        "label":                0,
    })

    # ── Fraudulent transactions ──────────────────────────────────────────
    fraud = pd.DataFrame({
        "amount":               rng.lognormal(mean=7.0, sigma=1.2, size=N_FRAUD).clip(200, 80_000),
        "transaction_velocity": rng.uniform(0.3, 1.0, N_FRAUD),
        "time_diff":            rng.uniform(0, 60, N_FRAUD),
        "device_change_flag":   rng.choice([0, 1], N_FRAUD, p=[0.40, 0.60]).astype(float),
        "geo_velocity":         rng.uniform(500, 5000, N_FRAUD),
        "biometric_deviation":  rng.uniform(0.50, 0.95, N_FRAUD),
        "hour_of_day":          rng.uniform(0, 5, N_FRAUD),
        "is_new_merchant":      rng.choice([0, 1], N_FRAUD, p=[0.50, 0.50]).astype(float),
        "label":                1,
    })

    df = pd.concat([legit, fraud], ignore_index=True)

    # Derived features
    amount_mean = df["amount"].mean()
    amount_std  = df["amount"].std()
    df["amount_zscore"] = (df["amount"] - amount_mean) / amount_std

    # Shuffle
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def train_xgboost(X_train, y_train, X_test, y_test):
    """Train XGBClassifier and report metrics."""
    # Handle class imbalance with scale_pos_weight
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos = neg_count / max(pos_count, 1)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        random_state=RANDOM_SEED,
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 60)
    print("XGBoost Classification Report")
    print("=" * 60)
    print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"]))
    print(f"  ROC-AUC : {roc_auc_score(y_test, y_proba):.4f}")
    print(f"  Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print(f"  Features: {list(X_train.columns)}")

    return model


def train_isolation_forest(X_train):
    """Train IsolationForest for anomaly scoring."""
    model = IsolationForest(
        n_estimators=200,
        contamination=0.03,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train)

    print("\n" + "=" * 60)
    print("Isolation Forest Trained")
    print("=" * 60)
    print(f"  Contamination: 0.03")
    print(f"  Features     : {list(X_train.columns)}")

    return model


def main():
    print("Generating synthetic training data...")
    df = generate_synthetic_dataset()
    print(f"  Total rows : {len(df)}")
    print(f"  Fraud rows : {(df['label'] == 1).sum()}")
    print(f"  Legit rows : {(df['label'] == 0).sum()}")

    X = df[FEATURES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    # ── XGBoost ──
    xgb_model = train_xgboost(X_train, y_train, X_test, y_test)

    # ── Isolation Forest ──
    if_model = train_isolation_forest(X_train)

    # ── Save ──
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(models_dir, exist_ok=True)

    xgb_path = os.path.join(models_dir, "fraud_model.pkl")
    if_path  = os.path.join(models_dir, "isolation_forest.pkl")

    joblib.dump(xgb_model, xgb_path)
    joblib.dump(if_model, if_path)

    print(f"\n[OK] Models saved:")
    print(f"   {xgb_path}")
    print(f"   {if_path}")

    # ── Quick sanity check ──
    print("\n" + "=" * 60)
    print("Sanity Check — scoring an obviously fraudulent transaction")
    print("=" * 60)
    fraudulent_txn = pd.DataFrame([{
        "amount": 15000.0,
        "amount_zscore": 4.5,
        "transaction_velocity": 0.85,
        "time_diff": 5.0,
        "device_change_flag": 1.0,
        "geo_velocity": 3500.0,
        "biometric_deviation": 0.88,
        "hour_of_day": 2.0,
        "is_new_merchant": 1.0,
    }])
    xgb_prob = xgb_model.predict_proba(fraudulent_txn)[0][1]
    if_score = if_model.decision_function(fraudulent_txn)[0]
    if_anomaly = 1.0 if if_score < 0 else 0.0

    print(f"  XGBoost fraud probability : {xgb_prob:.4f}")
    print(f"  IF decision_function      : {if_score:.4f}")
    print(f"  IF anomaly (score < 0)    : {if_anomaly}")

    normal_txn = pd.DataFrame([{
        "amount": 25.0,
        "amount_zscore": -0.3,
        "transaction_velocity": 0.05,
        "time_diff": 1800.0,
        "device_change_flag": 0.0,
        "geo_velocity": 10.0,
        "biometric_deviation": 0.08,
        "hour_of_day": 14.0,
        "is_new_merchant": 0.0,
    }])
    xgb_prob_n = xgb_model.predict_proba(normal_txn)[0][1]
    if_score_n = if_model.decision_function(normal_txn)[0]

    print(f"\n  Normal txn XGBoost prob   : {xgb_prob_n:.4f}")
    print(f"  Normal txn IF score       : {if_score_n:.4f}")

    if xgb_prob > 0.5 and xgb_prob_n < 0.3:
        print("\n✅ Models discriminate correctly between fraud and normal!")
    else:
        print("\n⚠️  Models may need tuning — check feature distributions.")


if __name__ == "__main__":
    main()
