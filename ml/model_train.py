import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
import numpy as np

conn = sqlite3.connect("../network_monitor.db")
df = pd.read_sql_query("SELECT * FROM readings", conn)
conn.close()

df["collected_at"] = pd.to_datetime(df["collected_at"], format="mixed", utc=True)
df["hour"] = df["collected_at"].dt.hour
df["memory_percent"] = (df["memory_used"] / df["memory_total"]) * 100

features = df[["hour", "cpu", "memory_percent", "interface_in_errors", "interface_out_errors"]]

train_data, test_data = train_test_split(features, test_size=0.2, random_state=42)

print(f"Total rows: {len(features)}")
print(f"Training rows: {len(train_data)}")
print(f"Testing rows: {len(test_data)}")

model = IsolationForest(contamination=0.05, random_state=42)
model.fit(train_data)

print("Model trained successfully on training set only")

train_predictions = model.predict(train_data)
train_anomalies = (train_predictions == -1).sum()
print(f"Anomalies in TRAINING data: {train_anomalies} out of {len(train_data)}")

test_predictions = model.predict(test_data)
test_anomalies = (test_predictions == -1).sum()
print(f"Anomalies in TESTING data (never seen during training): {test_anomalies} out of {len(test_data)}")

anomaly_rate_train = train_anomalies / len(train_data) * 100
anomaly_rate_test = test_anomalies / len(test_data) * 100
print(f"Training anomaly rate: {anomaly_rate_train:.1f}%")
print(f"Testing anomaly rate: {anomaly_rate_test:.1f}%")

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
from explain_anomaly import explain_anomaly

anomaly_rows = test_data[test_predictions == -1]

print(f"\nGenerating explanations for {len(anomaly_rows)} anomalies found in TEST data...\n")

for idx, row in anomaly_rows.iterrows():
    explanation = explain_anomaly(
        hour=row["hour"],
        cpu=row["cpu"],
        memory_percent=row["memory_percent"],
        in_errors=row["interface_in_errors"],
        out_errors=row["interface_out_errors"]
    )
    print(f"--- Anomaly at row {idx} ---")
    print(f"Values: hour={row['hour']}, cpu={row['cpu']}, mem%={row['memory_percent']:.1f}")
    print(f"Explanation: {explanation}\n")

