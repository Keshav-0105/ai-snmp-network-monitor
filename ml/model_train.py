import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np

conn = sqlite3.connect("../network_monitor.db")
df = pd.read_sql_query("SELECT * FROM readings", conn)
conn.close()

df["collected_at"] = pd.to_datetime(df["collected_at"], format="mixed", utc=True)
df["hour"] = df["collected_at"].dt.hour
df["memory_percent"] = (df["memory_used"] / df["memory_total"]) * 100

features = df[["hour", "cpu", "memory_percent", "interface_in_errors", "interface_out_errors"]]

print(f"Total training rows: {len(features)}")

model = IsolationForest(contamination=0.05, random_state=42)
model.fit(features)

print("Model trained successfully")

predictions = model.predict(features)
anomaly_count = (predictions == -1).sum()
print(f"Anomalies found in training data: {anomaly_count} out of {len(features)}")

print("\n--- Testing with new samples ---")

normal_sample = pd.DataFrame([{
    "hour": 13,
    "cpu": 45,
    "memory_percent": 42.0,
    "interface_in_errors": 1250,
    "interface_out_errors": 320
}])

night_normal_sample = pd.DataFrame([{
    "hour": 3,
    "cpu": 18,
    "memory_percent": 30.0,
    "interface_in_errors": 1150,
    "interface_out_errors": 280
}])

anomaly_sample = pd.DataFrame([{
    "hour": 3,
    "cpu": 95,
    "memory_percent": 90,
    "interface_in_errors": 5000,
    "interface_out_errors": 4000
}])

print("Daytime normal sample:", model.predict(normal_sample))
print("Nighttime normal sample:", model.predict(night_normal_sample))
print("Anomaly sample:", model.predict(anomaly_sample))

import joblib
joblib.dump(model, "isolation_forest_model.pkl")
print("\nModel saved to isolation_forest_model.pkl")