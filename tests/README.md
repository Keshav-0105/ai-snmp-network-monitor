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


## 3. Next step: store the data in SQLite


```text
SNMP agent gives values -> Go saves values in database -> later ML can read old values
```

Think of SQLite like a small Excel file for your app. It is just one file, for example:

```text
network_monitor.db
```

### Step 1: Add SQLite package

Run this once:

```bash
cd /home/cdot/snmp_monitoring/ai-snmp-network-monitor
GO111MODULE=on go get modernc.org/sqlite
```

This adds SQLite support to your Go project.

### Step 2: Create a new file called `database.go`

Do not put all database code inside `main.go`. Keep it simple and separate and make sure to create a different file

Create:

```text
database.go
```

This file will do 3 jobs:

1. Open the database file.
2. Create the table if it does not exist.
3. Save one SNMP reading.

### Step 3: Create a `Reading` structure

A `Reading` means one full set of SNMP values from one poll.

Example:

```go
type Reading struct {
    Device             string
    CollectedAt        time.Time
    CPU                int
    MemoryUsed         int
    MemoryTotal        int
    InterfaceInErrors  int
    InterfaceOutErrors int
}
```

In simple words, one `Reading` is one row in the database.

### Step 4: Create the database table

The table should look like this:

```sql
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  cpu INTEGER NOT NULL,
  memory_used INTEGER NOT NULL,
  memory_total INTEGER NOT NULL,
  interface_in_errors INTEGER NOT NULL,
  interface_out_errors INTEGER NOT NULL
);
```

Each time your Go app polls SNMP, it should insert one row.

Example row:

```text
1 | 127.0.0.1 | 2026-07-16T11:30:00Z | 42 | 3200 | 8192 | 1200 | 300
```

### Step 5: Open database when app starts

In `main.go`, near the start of `main()`, the idea is:

```go
db, err := openDatabase()
if err != nil {
    log.Fatal(err)
}
defer db.Close()
```

This opens `network_monitor.db`.

If the file does not exist, SQLite creates it.

### Step 6: Convert SNMP OIDs into names

Your Go code currently receives this:

```text
OID -> Value
```

You need to convert that into this:

```text
cpu -> 42
memory_used -> 3200
memory_total -> 8192
interface_in_errors -> 1200
interface_out_errors -> 300
```

Use this mapping:

```text
1.3.6.1.2.1.25.3.3.1.2.1  -> cpu
1.3.6.1.2.1.25.2.3.1.6.1  -> memory_used
1.3.6.1.2.1.25.2.3.1.5.1  -> memory_total
1.3.6.1.2.1.2.2.1.14.1   -> interface_in_errors
1.3.6.1.2.1.2.2.1.20.1   -> interface_out_errors
```

### Step 7: Change `polldevice` idea

Right now your function only prints:

```go
polldevice(snmp, oids)
```

Later, make it return a reading:

```go
reading, err := polldevice(snmp, oids)
```

Then save it:

```go
err = saveReading(db, reading)
```

So the final idea is:

```text
poll device -> make Reading -> save Reading into SQLite
```

### Step 8: Save one row after every successful poll

After every successful SNMP poll, insert one row into `readings`.

In simple words:

```text
If SNMP worked, save it.
If SNMP failed, do not save it.
```

### Step 9: Check if SQLite is working

After running your app for some time, install/use sqlite3 and run:

```bash
sqlite3 network_monitor.db
```

Then inside SQLite:

```sql
SELECT * FROM readings;
```

You should see saved rows.

### Step 10: Why this is needed before ML

Machine learning needs old data.

Without SQLite:

```text
ML has nothing to learn from
```

With SQLite:

```text
ML can read past CPU, memory, and error values
ML learns what normal looks like
ML can detect unusual readings
```

## ML Integration Later

Last step is 

1. Train Isolation Forest using `hour`, `cpu`, `memory_percent`, `interface_in_errors`, `interface_out_errors`.
2. If anomaly is found, explain it and send an alert.


## If we have time integerate telegram so it can send alerts to us
