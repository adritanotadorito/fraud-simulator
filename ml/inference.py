import joblib

from feature_engineering import engineer_features
from rule_engine import calculate_rule_score
from fusion import calculate_final_risk

xgb = joblib.load("models/fraud_model.pkl")
iso = joblib.load("models/isolation_forest.pkl")


def predict(transaction_df):

    # transaction_df is a pandas DataFrame with ONE transaction

    transaction_df = engineer_features(transaction_df)

    xgb_score = xgb.predict_proba(transaction_df)[0][1]

    iso_prediction = iso.predict(transaction_df)[0]

    isolation_score = 1 if iso_prediction == -1 else 0

    rule_score = calculate_rule_score(
        transaction_df.iloc[0].to_dict()
    )

    final_risk = calculate_final_risk(
        xgb_score,
        isolation_score,
        rule_score,
        threat_score=0
    )

    decision = "ALLOW"

    if final_risk >= 0.8:
        decision = "BLOCK"

    elif final_risk >= 0.5:
        decision = "FLAG"

    return {
        "decision": decision,
        "xgboost_score": float(xgb_score),
        "isolation_score": isolation_score,
        "rule_score": rule_score,
        "final_risk": float(final_risk)
    }