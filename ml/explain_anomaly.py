# explain_anomaly.py
# Sends the values of a flagged anomaly to a locally running Ollama model
# and returns a short, plain-English explanation of the likely cause.
# Called from model_train.py for every reading the Isolation Forest flags
# as anomalous in the test set.

import requests


def explain_anomaly(hour, cpu, memory_percent, in_errors, out_errors):
    # Build a tightly constrained prompt: one sentence, no reasoning shown,
    # no troubleshooting steps. Keeps output short enough to print inline
    # for every anomaly without cluttering the console.
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

    # Ollama must already be running locally (`ollama serve`) with the
    # llama3.2 model pulled. stream=False waits for the full response
    # instead of streaming tokens, since we just want one short string back.
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    })

    return response.json()["response"].strip()
