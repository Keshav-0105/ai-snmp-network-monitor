# ============================================================
# model_train.py
# Trains an Isolation Forest anomaly detection model on
# historical SNMP readings, evaluates it properly on unseen
# test data, generates explanations for anomalies using
# Ollama, and produces charts showing the results.
# ============================================================

import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
    "hour": 13, "cpu": 45, "memory_percent": 42.0,
    "interface_in_errors": 1250, "interface_out_errors": 320
}])
night_normal_sample = pd.DataFrame([{
    "hour": 3, "cpu": 18, "memory_percent": 30.0,
    "interface_in_errors": 1150, "interface_out_errors": 280
}])
anomaly_sample = pd.DataFrame([{
    "hour": 3, "cpu": 95, "memory_percent": 90,
    "interface_in_errors": 5000, "interface_out_errors": 4000
}])
print("Daytime normal sample:", model.predict(normal_sample))
print("Nighttime normal sample:", model.predict(night_normal_sample))
print("Anomaly sample:", model.predict(anomaly_sample))

import joblib
joblib.dump(model, "isolation_forest_model.pkl")
print("\nModel saved to isolation_forest_model.pkl")

n_normal_eval = min(50, len(test_data))
normal_eval = test_data.sample(n=n_normal_eval, random_state=42).copy()
normal_eval_labels = np.ones(len(normal_eval))

feature_cols = ["hour", "cpu", "memory_percent", "interface_in_errors", "interface_out_errors"]
means = features[feature_cols].mean()
stds = features[feature_cols].std()

n_anomaly_eval = max(10, int(n_normal_eval * 0.2))
rng = np.random.default_rng(42)
synthetic_anomalies = pd.DataFrame({
    "hour": rng.integers(0, 24, n_anomaly_eval),
    "cpu": np.clip(means["cpu"] + rng.uniform(4, 6, n_anomaly_eval) * stds["cpu"], 90, 100),
    "memory_percent": np.clip(means["memory_percent"] + rng.uniform(4, 6, n_anomaly_eval) * stds["memory_percent"], 85, 100),
    "interface_in_errors": means["interface_in_errors"] + rng.uniform(4, 8, n_anomaly_eval) * stds["interface_in_errors"],
    "interface_out_errors": means["interface_out_errors"] + rng.uniform(4, 8, n_anomaly_eval) * stds["interface_out_errors"],
})
synthetic_anomaly_labels = -np.ones(len(synthetic_anomalies))

eval_data = pd.concat([normal_eval, synthetic_anomalies], ignore_index=True)
eval_true_labels = np.concatenate([normal_eval_labels, synthetic_anomaly_labels])
eval_predictions = model.predict(eval_data)

accuracy = accuracy_score(eval_true_labels, eval_predictions)
precision = precision_score(eval_true_labels, eval_predictions, pos_label=-1, zero_division=0)
recall = recall_score(eval_true_labels, eval_predictions, pos_label=-1, zero_division=0)
f1 = f1_score(eval_true_labels, eval_predictions, pos_label=-1, zero_division=0)

print(f"\nAccuracy:  {accuracy:.3f}")

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

plt.figure(figsize=(6, 4))
plt.bar(["Training", "Testing"], [len(train_data), len(test_data)], color=["#1B3A5C", "#2E7D8C"])
plt.title("Train / Test Split")
plt.ylabel("Number of Readings")
for i, v in enumerate([len(train_data), len(test_data)]):
    plt.text(i, v + 2, str(v), ha="center", fontweight="bold")
plt.tight_layout()
plt.savefig("chart_split.png")
plt.close()

plt.figure(figsize=(6, 4))
plt.bar(["Training", "Testing"], [anomaly_rate_train, anomaly_rate_test], color=["#1B3A5C", "#2E7D8C"])
plt.title("Anomaly Rate: Training vs Testing")
plt.ylabel("Anomaly Rate (%)")
for i, v in enumerate([anomaly_rate_train, anomaly_rate_test]):
    plt.text(i, v + 0.1, f"{v:.1f}%", ha="center", fontweight="bold")
plt.tight_layout()
plt.savefig("chart_anomaly_rate.png")
plt.close()

plt.figure(figsize=(6, 4))
plt.bar(["Accuracy"], [accuracy * 100], color=["#2E7D8C"])
plt.ylim(0, 100)
plt.title("Model Accuracy on Evaluation Set")
plt.ylabel("Accuracy (%)")
plt.text(0, accuracy * 100 + 2, f"{accuracy*100:.1f}%", ha="center", fontweight="bold")
plt.tight_layout()
plt.savefig("chart_accuracy.png")
plt.close()

plt.figure(figsize=(7, 4.5))
plt.scatter(train_data.loc[train_predictions == 1, "hour"],
            train_data.loc[train_predictions == 1, "cpu"],
            s=15, color="#1B3A5C", alpha=0.5, label="Normal")
plt.scatter(train_data.loc[train_predictions == -1, "hour"],
            train_data.loc[train_predictions == -1, "cpu"],
            s=45, color="#C0392B", marker="x", linewidths=2, label="Anomaly")
plt.xlabel("Hour of Day")
plt.ylabel("CPU (%)")
plt.title("CPU vs Hour — Normal vs Flagged Anomalies (Training Data)")
plt.legend()
plt.tight_layout()
plt.savefig("chart_scatter.png")
plt.close()

print("\nCharts saved: chart_split.png, chart_anomaly_rate.png, chart_accuracy.png, chart_scatter.png")
