import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)
from xgboost import XGBClassifier
from feature_engineering import engineer_features

def main():
    df = pd.read_csv("data/creditcard.csv")
    df = engineer_features(df)
    X = df.drop("Class", axis=1)
    y = df["Class"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    xgb = XGBClassifier(
        random_state=42,
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        eval_metric="logloss"
    )

    xgb.fit(X_train, y_train)

    joblib.dump(xgb, "models/fraud_model.pkl")

    iso = IsolationForest(
        contamination=0.0017,
        random_state=42
    )

    iso.fit(X_train)
    joblib.dump(iso, "models/isolation_forest.pkl")

    y_pred = xgb.predict(X_test)

    print("Accuracy :", accuracy_score(y_test, y_pred))
    print("Precision:", precision_score(y_test, y_pred))
    print("Recall   :", recall_score(y_test, y_pred))
    print("F1 Score :", f1_score(y_test, y_pred))

    print("\nModels trained and saved successfully!")

if __name__ == "__main__":
    main()