import joblib
from feature_engineering import engineer_features
from rule_engine import calculate_rule_score
from fusion import calculate_final_risk

xgb = joblib.load("models/fraud_model.pkl")
iso = joblib.load("models/isolation_forest.pkl")

def predict(df):

    df = engineer_features(df)

    xgb_score = xgb.predict_proba(df)[0][1]

    iso_score = 1 if iso.predict(df)[0] == -1 else 0

    rule_score = calculate_rule_score(
        df.iloc[0].to_dict()
    )

    final_risk = calculate_final_risk(
        xgb_score,
        iso_score,
        rule_score
    )

    return {
        "xgboost_score": float(xgb_score),
        "isolation_score": iso_score,
        "rule_score": rule_score,
        "final_risk": final_risk
    }