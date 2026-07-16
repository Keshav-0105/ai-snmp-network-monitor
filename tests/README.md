# Simple Testing Guide

## 1. Test Everything

Run this first in first terminal:

```bash
python3 tests/start_agent.py
```

It starts the testing snmp agent

## 2. Start our SNMP Manager

Open terminal 2:

```bash
GO111MODULE=on go run .
```

Keep this running.


You should see output like:

```text
OID:.1.3.6.1.2.1.25.3.3.1.2.1|Value :42
OID:.1.3.6.1.2.1.25.2.3.1.6.1|Value :3200
OID:.1.3.6.1.2.1.25.2.3.1.5.1|Value :8192
OID:.1.3.6.1.2.1.2.2.1.14.1|Value :1200
OID:.1.3.6.1.2.1.2.2.1.20.1|Value :300
```

If you get `connection refused`, the SNMP agent is not running. Start `python3 tests/start_agent.py` first.


## 3. Next step should be storing the data into sqlite database

```sql
CREATE TABLE readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  cpu REAL NOT NULL,
  memory_used REAL NOT NULL,
  memory_total REAL NOT NULL,
  interface_in_errors REAL NOT NULL,
  interface_out_errors REAL NOT NULL
);
```
Reading should be remembered with a timestamp. Add a `readings` table later with columns like:

Then:

1. Convert each SNMP response into one row.
2. Calculate memory percent as `memory_used / memory_total * 100`.
3. Insert the row after every successful poll.

## ML Integration Later

Last step is 

1. Train Isolation Forest using `hour`, `cpu`, `memory_percent`, `interface_in_errors`, `interface_out_errors`.
2. If anomaly is found, explain it and send an alert.


## If we have time integerate telegram so it can send alerts to