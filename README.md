# AI-Powered SNMP Network Health Monitor

A network monitoring system that collects SNMP data from network devices, stores it in SQLite, trains a machine learning model to detect anomalies, and generates plain-English explanations for detected anomalies using a locally hosted LLM (Ollama).

## Architecture

```text
SNMP Devices (simulated)
        │
        ▼
Go Collector
(goroutines + channels)
        │
        ▼
SQLite Database
        │
        ▼
Python ML
(Isolation Forest)
        │
        ▼
Ollama
(LLM explanation)
```

## Features

* Concurrent SNMP polling across a configurable port range (2161–2200) using Go goroutines
* SNMPv3 authentication (NoAuthNoPriv, dedicated username, correct ContextName)
* Automatic retry every 60 seconds — no permanent give-up on an unreachable device
* Precise, context-rich error handling and logging throughout
* SQLite-based historical data storage
* Isolation Forest anomaly detection with proper 80/20 train/test split evaluation
* Large, realistic training dataset (2,600+ rows) covering 8 distinct anomaly categories
* Real accuracy metrics (accuracy, precision, recall, F1) on a known-labelled evaluation set
* Local LLM (Ollama / Llama 3.2) generates plain-English explanations for detected anomalies
* Dockerized deployment using a pre-built binary (no Go toolchain required inside the container)
* Automated setup verification test suite

## Prerequisites

* Go 1.26+
* Python 3.12+
* Homebrew (for Ollama installation on macOS)
* Docker Desktop (optional, for containerized deployment)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Keshav-0105/ai-snmp-network-monitor.git
cd ai-snmp-network-monitor
```

### 2. Install Go Dependencies

```bash
go mod download
```

### 3. Install Python Dependencies

```bash
pip3 install -r ml/requirements.txt --break-system-packages
```

### 4. Install the SNMP Simulator

No physical network hardware is required. The project uses `snmpsim` for testing.

```bash
pip3 install snmpsim pysmi --break-system-packages
```

### 5. Install Ollama

On macOS:

```bash
brew install ollama
ollama pull llama3.2
```

## Running the Full Pipeline

The complete pipeline requires four terminals.

### Terminal 1 — SNMP Simulator

Start the SNMP simulator:

```bash
./start_tester.sh
```

Or run it directly:

```bash
python3 -m snmpsim.commands.responder \
  --data-dir=./data \
  --agent-udpv4-endpoint=127.0.0.1:2161 \
  --v3-user=snmpuser
```

### Terminal 2 — Ollama

Start the local LLM service:

```bash
ollama serve
```

### Terminal 3 — Go Collector

Start the SNMP monitoring application:

```bash
./start_main.sh
```

Or run it directly:

```bash
go build .
go run .
```

The collector:

* Connects to devices on ports `2161–2200`
* Polls SNMP metrics every 60 seconds
* Uses concurrent goroutines for device polling
* Retries unreachable devices automatically
* Stores collected readings in `network_monitor.db`

### Terminal 4 — ML Training, Evaluation, and Explanation

Run the machine learning pipeline:

```bash
cd ml
python3 model_train.py
```

The ML pipeline:

1. Loads the training dataset
2. Performs an 80/20 train/test split
3. Trains the Isolation Forest model
4. Evaluates the model on unseen test data
5. Calculates accuracy, precision, recall, and F1 score
6. Generates visualization charts
7. Identifies anomalous readings
8. Sends flagged anomalies to Ollama
9. Generates plain-English explanations

## Running the Test Suite

A verification script checks the project setup, including SNMP configuration, OIDs, simulator data, and Go compilation.

```bash
python3 tests/test.py
```


## Running with Docker

Build the Go binary on the host first:

```bash
GOOS=linux GOARCH=amd64 go build -o snmp-monitor .
```

Build the Docker image:

```bash
docker build -t snmp-monitor .
```

Run the container:

```bash
docker run -e SNMP_TARGET=host.docker.internal snmp-monitor
```

The Docker image uses the pre-built Go binary and does not require the Go toolchain inside the container.

## Project Structure

```text
ai-snmp-network-monitor/
├── main.go
│   └── SNMP polling, goroutine orchestration, connection retry logic
├── database.go
│   └── SQLite storage: Reading struct, openDatabase, saveReading
├── go.mod
│   └── Go module definition and dependencies
├── go.sum
│   └── Go dependency checksums
├── Dockerfile
│   └── Binary-only container build
├── start_main.sh
│   └── Convenience script to build and run the Go collector
├── start_tester.sh
│   └── Convenience script to start the SNMP simulator
├── .gitignore
├── README.md
├── network_monitor.db
│   └── Collected SNMP readings stored in SQLite
├── readings_export.csv
│   └── CSV export of collected monitoring data
│
├── data/
│   └── public.snmprec
│       └── SNMP simulator sample data (OID → value mappings)
│
├── ml/
│   ├── model_train.py
│   │   └── Trains Isolation Forest, evaluates model, and generates charts
│   ├── explain_anomaly.py
│   │   └── Sends flagged anomaly data to Ollama for plain-English explanation
│   ├── generate_data.py
│   │   └── Generates a small realistic synthetic dataset (150 rows)
│   ├── generate_large_dataset.py
│   │   └── Generates the full-scale dataset (2,000+ rows, 8 anomaly categories)
│   ├── requirements.txt
│   │   └── Python dependencies
│   ├── isolation_forest_model.pkl
│   │   └── Saved trained Isolation Forest model
│   ├── chart_split.png
│   │   └── Train/test split visualization
│   ├── chart_anomaly_rate.png
│   │   └── Training vs testing anomaly rate comparison
│   ├── chart_accuracy.png
│   │   └── Model accuracy on the labelled evaluation set
│   └── chart_scatter.png
│       └── CPU vs hour scatter plot of normal and flagged readings
│
├── results/
│   ├── output.txt
│   │   └── Full console output from the latest training run
│   ├── chart_split.png
│   ├── chart_anomaly_rate.png
│   ├── chart_accuracy.png
│   └── chart_scatter.png
│
└── tests/
    ├── test.py
    │   └── Automated setup verification
    │       (SNMP configuration, OIDs, Go build, simulator data)
    └── start_agent.py
        └── Helper script for launching the test simulator
```

## Results Summary

| Metric                                          | Value |
| ----------------------------------------------- | ----: |
| Total readings in dataset                       | 2,647 |
| Training rows (80%)                             | 2,117 |
| Testing rows (20%, unseen)                      |   530 |
| Training anomaly rate                           |  5.0% |
| Testing anomaly rate                            |  4.5% |
| Model accuracy (labelled evaluation set)        | 96.7% |
| Anomaly categories represented in training data |     8 |

The close match between training and testing anomaly rates indicates that the model generalizes well rather than simply memorizing the training data.

See the `results/` directory for the complete training output and generated visualization charts.

## Anomaly Categories Covered in Training Data

| Category                               | Description                                                 |
| -------------------------------------- | ----------------------------------------------------------- |
| **A. CPU overload spikes**             | Sudden, extreme CPU utilization (92–100%)                   |
| **B. Memory leak pattern**             | High memory usage while CPU remains normal                  |
| **C. Interface incoming-error bursts** | Sudden spikes in inbound packet errors                      |
| **D. Interface outgoing-error bursts** | Sudden spikes in outbound packet errors                     |
| **E. Combined catastrophic failure**   | CPU, memory, and both error counters spike together         |
| **F. Time-inappropriate load**         | Business-level CPU activity during 2–4 AM                   |
| **G. Sudden idle drop**                | Device becomes abnormally quiet with near-zero CPU activity |
| **H. Slow degradation ramp**           | Gradual increase of multiple metrics toward failure         |

## Key Technical Decisions

### SNMPv3 over SNMPv2c

SNMPv3 was selected instead of SNMPv2c to avoid relying on plaintext community strings and to provide user-based authentication.

### Goroutines + Channels

The collector uses a producer-consumer architecture where SNMP polling and database writing operate as independent concurrent workers connected through a channel.

This ensures that:

* A slow database operation does not block SNMP polling
* Multiple devices can be monitored concurrently
* Collection and persistence remain loosely coupled

### Isolation Forest over Deep Learning

Isolation Forest was selected because it:

* Works well for unsupervised anomaly detection
* Does not require large amounts of labelled failure data
* Trains quickly
* Does not require a GPU
* Is well suited to detecting unusual network-monitoring patterns

### Local LLM with Ollama

Ollama was selected instead of a cloud-based LLM API because:

* Monitoring data remains local
* No per-request API cost
* No external internet dependency for inference
* Better control over sensitive network information

### Binary-Only Docker Build

The Go application is compiled on the host before the Docker image is built.

The container therefore only needs to execute the finished binary, resulting in a simpler deployment without requiring the Go compiler toolchain inside the runtime image.

### Eight-Category Synthetic Anomaly Generation

The synthetic dataset was deliberately designed to represent multiple realistic network failure patterns rather than relying only on random spikes.

The eight categories cover CPU overload, memory problems, interface errors, catastrophic failures, unusual time-based activity, sudden idle behavior, and gradual degradation.

## Known Limitations / Future Work

* Model scoring is not yet fully real-time. New readings are collected continuously by the Go program, but the ML model must currently be retrained or re-run manually to evaluate the latest data.
* Telegram and email alerting are not yet implemented.
* `host.docker.internal` networking is primarily intended for macOS Docker Desktop and similar desktop environments.
* A multi-container Docker Compose deployment would provide a more portable long-term architecture.
* The current training dataset combines a smaller number of real collected readings with a larger volume of synthetic data.
* As more real-world monitoring data becomes available, the proportion of synthetic training data should gradually be reduced.
* Future versions can integrate continuous model inference directly into the monitoring pipeline.

## Future Enhancements

Potential future improvements include:

* Real-time anomaly scoring for every newly collected SNMP reading
* Automated Telegram/email security alerts
* Grafana-based monitoring dashboards
* Prometheus metrics integration
* Docker Compose deployment
* Automatic model retraining
* Model versioning and experiment tracking
* Additional SNMP metrics and network protocols
* Role-based access control for the monitoring dashboard
* Historical anomaly trend analysis
* Automated incident ticket creation
* Integration with SIEM platforms
* More advanced LLM-based root-cause analysis

## Security Considerations

The project is designed with security and privacy considerations in mind:

* SNMPv3 is used instead of SNMPv2c where supported
* Monitoring data is stored locally in SQLite
* LLM inference is performed locally using Ollama
* No monitoring data needs to be transmitted to an external cloud API
* The Docker runtime does not require the Go compiler
* Connection failures are handled through controlled retry logic
* Configuration and generated data can be excluded from Git using `.gitignore`

## Author

**Keshav Sharma**

B.Tech, Computer Science and Applied Mathematics — Vivekanand Institute of Professional Studies

**Internship Project — Centre for Development of Telematics (C-DOT)**

**Mentor:** Mr. Kunal Rawat

A network monitoring system that collects SNMP data from network devices, stores it in SQLite, trains a machine learning model to detect anomalies, and generates plain-English explanations for detected anomalies using a locally hosted LLM (Ollama).

## Architecture

SNMP Devices (simulated) → Go Collector (goroutines + channels) → SQLite Database
↓
Python ML (Isolation Forest)
↓
Ollama (LLM explanation)


## Features

- Concurrent SNMP polling across a configurable port range (2161–2200) using Go goroutines
- SNMPv3 authentication (NoAuthNoPriv, dedicated username, correct ContextName)
- Automatic retry every 60 seconds — no permanent give-up on an unreachable device
- Precise, context-rich error handling and logging throughout
- SQLite-based historical data storage
- Isolation Forest anomaly detection with proper 80/20 train/test split evaluation
- Large, realistic training dataset (2,600+ rows) covering 8 distinct anomaly categories
- Real accuracy metrics (accuracy, precision, recall, F1) on a known-labelled evaluation set
- Local LLM (Ollama / Llama 3.2) generates plain-English explanations for detected anomalies
- Dockerized deployment using a pre-built binary (no Go toolchain required inside the container)
- Automated setup verification test suite

## Prerequisites

- Go 1.26+
- Python 3.12+
- Homebrew (for Ollama installation on Mac)
- Docker Desktop (optional, for containerized deployment)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Keshav-0105/ai-snmp-network-monitor.git
cd ai-snmp-network-monitor
```

### 2. Install Go dependencies

```bash
go mod download
```

### 3. Install Python dependencies

```bash
pip3 install -r ml/requirements.txt --break-system-packages
```

### 4. Install the SNMP simulator (no real hardware required)

```bash
pip3 install snmpsim pysmi --break-system-packages
```

### 5. Install Ollama

```bash
brew install ollama
ollama pull llama3.2
```

## Running the Full Pipeline

Four terminals are required, each left running.

**Terminal 1 — SNMP simulator:**
```bash
./start_tester.sh
```
or directly:
```bash
python3 -m snmpsim.commands.responder --data-dir=./data --agent-udpv4-endpoint=127.0.0.1:2161 --v3-user=snmpuser
```

**Terminal 2 — Ollama:**
```bash
ollama serve
```

**Terminal 3 — Go collector:**
```bash
./start_main.sh
```
or directly:
```bash
go build .
go run .
```
Connects to devices on ports 2161–2200, polls every 60 seconds, saves readings to `network_monitor.db`.

**Terminal 4 — ML training, evaluation, and explanation:**
```bash
cd ml
python3 model_train.py
```
Trains the model, evaluates it on unseen test data, generates real accuracy metrics, produces charts, and generates plain-English explanations for detected anomalies.

## Running the Test Suite

A verification script checks that the collector, SNMP configuration, simulator data, and Go build are all correctly set up:

```bash
python3 tests/test.py
```

## Running with Docker

```bash
# Build the Go binary on the host first
GOOS=linux GOARCH=amd64 go build -o snmp-monitor .

# Build the Docker image (binary-only, no Go toolchain in the container)
docker build -t snmp-monitor .

# Run it, connecting back to the host machine's simulator
docker run -e SNMP_TARGET=host.docker.internal snmp-monitor
```

## Project Structure

ai-snmp-network-monitor/
├── main.go — SNMP polling, goroutine orchestration, connection retry logic
├── database.go — SQLite storage: Reading struct, openDatabase, saveReading
├── go.mod / go.sum — Go module dependencies
├── Dockerfile — Binary-only container build
├── start_main.sh — Convenience script to build and run the Go collector
├── start_tester.sh — Convenience script to start the SNMP simulator
├── .gitignore
├── README.md
├── network_monitor.db — Collected SNMP readings (SQLite)
├── readings_export.csv — CSV export of collected data
│
├── data/
│ └── public.snmprec — SNMP simulator sample data (OID → value mappings)
│
├── ml/
│ ├── model_train.py — Trains Isolation Forest, evaluates, generates charts and explanations
│ ├── explain_anomaly.py — Sends flagged anomaly data to Ollama, returns plain-English explanation
│ ├── generate_data.py — Generates a small realistic synthetic dataset (150 rows)
│ ├── generate_large_dataset.py — Generates the full-scale dataset (2,000+ rows, 8 anomaly categories)
│ ├── requirements.txt — Python dependencies
│ ├── isolation_forest_model.pkl — Saved trained model
│ ├── chart_split.png — Train/test split visualization
│ ├── chart_anomaly_rate.png — Anomaly rate comparison (training vs testing)
│ ├── chart_accuracy.png — Model accuracy on labelled evaluation set
│ └── chart_scatter.png — CPU vs hour scatter plot, normal vs flagged readings
│
├── results/
│ ├── output.txt — Full console output from the latest training run
│ ├── chart_split.png
│ ├── chart_anomaly_rate.png
│ ├── chart_accuracy.png
│ └── chart_scatter.png
│
└── tests/
├── test.py — Automated setup verification (SNMP config, OIDs, Go build, simulator data)
└── start_agent.py — Helper script for launching the test simulator


## Results Summary

| Metric | Value |
|---|---|
| Total readings in dataset | 2,647 |
| Training rows (80%) | 2,117 |
| Testing rows (20%, unseen) | 530 |
| Training anomaly rate | 5.0% |
| Testing anomaly rate | 4.5% |
| Model accuracy (labelled evaluation set) | 96.7% |
| Anomaly categories represented in training data | 8 |

The close match between training and testing anomaly rates indicates the model generalizes correctly rather than memorizing training data. See `results/` for the full output log and all four charts.

### Anomaly Categories Covered in Training Data

| Category | Description |
|---|---|
| A. CPU overload spikes | Sudden, extreme CPU utilization (92–100%) |
| B. Memory leak pattern | High memory usage while CPU stays normal |
| C. Interface incoming-error bursts | Sudden spike in inbound packet errors |
| D. Interface outgoing-error bursts | Sudden spike in outbound packet errors |
| E. Combined catastrophic failure | CPU, memory, and both error counters spike together |
| F. Time-inappropriate load | Business-level CPU activity during 2–4 AM |
| G. Sudden idle drop | Device goes abnormally quiet (near-zero CPU) |
| H. Slow degradation ramp | Gradual creep of all metrics toward failure over time |

## Key Technical Decisions

- **SNMPv3 over SNMPv2c** — replaces the plaintext community string with proper user-based authentication.
- **Goroutines + channels (producer-consumer pattern)** — SNMP polling and database writing run as independent, concurrently executing workers connected only by a channel, so a slow database write never blocks polling and vice versa.
- **Isolation Forest over deep learning** — requires no labelled failure data, trains in well under a second with no GPU, and is an industry-proven technique for this class of problem.
- **Local LLM (Ollama) over a cloud API** — no per-request cost, no internet dependency, and no monitoring data leaves the machine.
- **Binary-only Docker build** — the Go program is compiled on the host first; the container only needs to run the finished binary, resulting in a smaller, simpler image with no compiler toolchain required inside it.
- **8-category synthetic anomaly generation** — rather than relying on uniform random spikes, training data was deliberately constructed to represent every major real-world failure mode, so the model learns a genuinely diverse notion of "anomalous."

## Known Limitations / Future Work

- Model scoring is not yet fully real-time — new readings are collected continuously by the Go program, but the ML model must currently be retrained/re-run manually to evaluate on the latest data.
- Telegram/email alerting is not yet implemented.
- `host.docker.internal` networking is macOS-Docker-Desktop-specific; a multi-container Docker Compose setup would be a more portable long-term solution.
- Training data combines a smaller number of real collected readings with a larger volume of synthetic data; as more real data accumulates, the synthetic proportion should be reduced.

## Author

Keshav Sharma
B.Tech, Computer Science and Applied Mathematics — Vivekanand Institute of Professional Studies
Internship Project — Centre for Development of Telematics (C-DOT)
Mentor: Mr. Kunal Rawat
