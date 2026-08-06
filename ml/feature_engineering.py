import numpy as np
import pandas as pd

def engineer_features(df):
    df = df.copy()

    # Amount Z-score
    df["amount_zscore"] = (
        (df["Amount"] - df["Amount"].mean()) /
        df["Amount"].std()
    )

    # Transaction Velocity
    df["time_diff"] = df["Time"].diff().fillna(0)
    df["transaction_velocity"] = 1 / (df["time_diff"] + 1)

    # Simulated Features
    np.random.seed(42)

    df["device_change_flag"] = np.random.choice(
        [0, 1],
        len(df),
        p=[0.9, 0.1]
    )

    df["geo_velocity"] = np.random.uniform(0, 1, len(df))

    df["biometric_deviation"] = np.random.uniform(0, 1, len(df))

    return df