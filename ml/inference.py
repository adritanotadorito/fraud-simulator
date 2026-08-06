import joblib
model = joblib.load("models/fraud_model.pkl")

def predict(transaction):
    probability = model.predict_proba(transaction)[0][1]

    prediction = int(probability > 0.5)

    return {
        "prediction": prediction,
        "fraud_probability": float(probability)
    }