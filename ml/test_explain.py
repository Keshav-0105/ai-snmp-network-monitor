from explain_anomaly import explain_anomaly

result = explain_anomaly(hour=3, cpu=95, memory_percent=90, in_errors=5000, out_errors=4000)
print(result)

