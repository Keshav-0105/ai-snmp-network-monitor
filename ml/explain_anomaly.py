import requests

def explain_anomaly(hour, cpu, memory_percent, in_errors, out_errors):
    known_patterns = """
Known patterns:
- High CPU + rising errors + interface still up -> often overload or failing network interface
- High memory + stable CPU -> often a memory leak in a running process
- Interface down + zero traffic -> often a physical or cable issue
"""

    prompt = f"""{known_patterns}

Anomaly detected with these values:
Hour: {hour}
CPU: {cpu}%
Memory usage: {memory_percent:.1f}%
Interface incoming errors: {in_errors}
Interface outgoing errors: {out_errors}

Explain the likely cause of this anomaly in 2-3 sentences, in plain English,
and suggest one thing to check."""

    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.2",
        "prompt": prompt,
        "stream": False
    })

    return response.json()["response"]

