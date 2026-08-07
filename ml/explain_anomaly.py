import requests

def explain_anomaly(hour, cpu, memory_percent, in_errors, out_errors):
    prompt = f"""
Anomaly detected with these values:
Hour: {hour}
CPU: {cpu}%
Memory usage: {memory_percent:.1f}%
Interface incoming errors: {in_errors}
Interface outgoing errors: {out_errors}

In EXACTLY ONE SHORT SENTENCE, state the most likely cause of this anomaly.
Do not explain your reasoning. Do not suggest troubleshooting steps.
Just the single most likely cause, nothing else.
"""

    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    })

    return response.json()["response"].strip()

