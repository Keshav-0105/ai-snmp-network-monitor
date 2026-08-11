# test_explain.py
# Quick manual smoke test for explain_anomaly(): feeds it one hand-built,
# obviously anomalous reading (high CPU, high memory, high error counts,
# at 3am) and prints the explanation Ollama returns. Used to sanity-check
# the Ollama integration works before relying on it inside model_train.py.

from explain_anomaly import explain_anomaly

result = explain_anomaly(hour=3, cpu=95, memory_percent=90, in_errors=5000, out_errors=4000)
print(result)
