import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest

conn = sqlite3.connect("../network_monitor.db")
df = pd.read_sql_query("SELECT * FROM readings", conn)
conn.close()

df["collected_at"] = pd.to_datetime(df["collected_at"])
df["hour"] = df["collected_at"].dt.hour
df["memory_percent"] = (df["memory_used"] / df["memory_total"]) * 100

features = df[["hour", "cpu", "memory_percent", "interface_in_errors", "interface_out_errors"]]

model = IsolationForest(contamination=0.05, random_state=42)
model.fit(features)

print("Model trained successfully")
print(model.predict(features))
print(features)


import numpy as np

print("\n--- Testing with new samples ---")

normal_sample = pd.DataFrame([{
    "hour": 13,
    "cpu": 42,
    "memory_percent": 39.06,
    "interface_in_errors": 1200,
    "interface_out_errors": 300
}])

anomaly_sample = pd.DataFrame([{
    "hour": 3,
    "cpu": 95,
    "memory_percent": 90,
    "interface_in_errors": 5000,
    "interface_out_errors": 4000
}])

print("Normal sample:", model.predict(normal_sample))
print("Anomaly sample:", model.predict(anomaly_sample))