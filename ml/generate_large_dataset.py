"""
generate_large_dataset.py

Generates a large, realistic historical SNMP dataset (2000+ rows) covering:
- Normal daytime/nighttime/weekend variation (the bulk of the data)
- Every major anomaly category, so the model learns a genuinely diverse
  notion of "unusual": CPU overload, memory leaks, interface error bursts,
  combined multi-metric failures, and time-inappropriate spikes.
"""

import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("../network_monitor.db")
cursor = conn.cursor()

rows = []
base_time = datetime.now() - timedelta(days=30)  # spread across 30 days of history


def add_row(timestamp, cpu, mem_used, mem_total, in_err, out_err):
    rows.append((
        "127.0.0.1",
        timestamp.isoformat(),
        int(max(0, min(100, cpu))),
        int(max(0, mem_used)),
        int(mem_total),
        int(max(0, in_err)),
        int(max(0, out_err)),
    ))


# ============================================================
# PART 1: NORMAL DATA — realistic day/night/weekend variation
# ~1800 rows, one every ~24 minutes across 30 days
# ============================================================
minute_step = 24
n_normal = 1800

for i in range(n_normal):
    timestamp = base_time + timedelta(minutes=i * minute_step)
    hour = timestamp.hour
    is_weekend = timestamp.weekday() >= 5

    if is_weekend:
        cpu = random.gauss(20, 5)
        mem_used = random.gauss(2400, 200)
    elif 9 <= hour <= 18:
        cpu = random.gauss(45, 7)
        mem_used = random.gauss(3400, 250)
    elif 6 <= hour < 9 or 18 < hour <= 22:
        cpu = random.gauss(30, 6)         # transitional hours, moderate load
        mem_used = random.gauss(2900, 200)
    else:
        cpu = random.gauss(15, 4)          # deep night
        mem_used = random.gauss(2200, 150)

    mem_total = 8192

    # small, realistic background noise in error counters
    in_err = random.gauss(1200, 60) if random.random() > 0.05 else random.gauss(1300, 80)
    out_err = random.gauss(300, 25)

    add_row(timestamp, cpu, mem_used, mem_total, in_err, out_err)


# ============================================================
# PART 2: ANOMALIES — every major category, spread realistically
# ~220 rows total (roughly matching a ~11% overall anomaly rate,
# intentionally on the richer side so the model sees good variety)
# ============================================================
anomaly_start = base_time + timedelta(days=2)


def anomaly_time(offset_minutes):
    return anomaly_start + timedelta(minutes=offset_minutes)


# ---- Category A: CPU overload spikes (sudden, extreme, short-lived) ----
for i in range(35):
    t = anomaly_time(i * 900 + random.randint(0, 400))
    add_row(t,
            cpu=random.uniform(92, 100),
            mem_used=random.gauss(3500, 300),
            mem_total=8192,
            in_err=random.gauss(1250, 80),
            out_err=random.gauss(310, 30))

# ---- Category B: Memory leak pattern (high memory, CPU stays normal) ----
for i in range(35):
    t = anomaly_time(i * 950 + 300)
    add_row(t,
            cpu=random.gauss(35, 6),
            mem_used=random.uniform(7200, 8100),   # memory nearly full
            mem_total=8192,
            in_err=random.gauss(1220, 70),
            out_err=random.gauss(305, 25))

# ---- Category C: Interface in-error burst (network/cable issue) ----
for i in range(35):
    t = anomaly_time(i * 970 + 600)
    add_row(t,
            cpu=random.gauss(30, 8),
            mem_used=random.gauss(2800, 300),
            mem_total=8192,
            in_err=random.uniform(4500, 8000),      # error spike
            out_err=random.gauss(320, 40))

# ---- Category D: Interface out-error burst (outgoing path issue) ----
for i in range(30):
    t = anomaly_time(i * 1010 + 900)
    add_row(t,
            cpu=random.gauss(28, 7),
            mem_used=random.gauss(2700, 250),
            mem_total=8192,
            in_err=random.gauss(1230, 70),
            out_err=random.uniform(3800, 7000))

# ---- Category E: Combined catastrophic failure (everything spikes together) ----
for i in range(25):
    t = anomaly_time(i * 1100 + 1200)
    add_row(t,
            cpu=random.uniform(90, 100),
            mem_used=random.uniform(7500, 8150),
            mem_total=8192,
            in_err=random.uniform(5000, 9000),
            out_err=random.uniform(4000, 7500))

# ---- Category F: Time-inappropriate load (business-level CPU at 2-4 AM) ----
for i in range(30):
    day_offset = i * 3
    t = anomaly_start + timedelta(days=day_offset, hours=random.choice([2, 3, 4]),
                                   minutes=random.randint(0, 59))
    add_row(t,
            cpu=random.uniform(55, 80),   # normal for daytime, abnormal at night
            mem_used=random.gauss(3600, 300),
            mem_total=8192,
            in_err=random.gauss(1240, 80),
            out_err=random.gauss(315, 30))

# ---- Category G: Sudden idle drop (device appears to go unusually quiet) ----
for i in range(20):
    t = anomaly_time(i * 1200 + 1500)
    add_row(t,
            cpu=random.uniform(0, 3),
            mem_used=random.uniform(1500, 1800),
            mem_total=8192,
            in_err=random.gauss(1100, 50),
            out_err=random.gauss(280, 20))

# ---- Category H: Slow degradation ramp (gradual creep toward failure) ----
ramp_start = anomaly_start + timedelta(days=10)
for i in range(20):
    progress = i / 20
    t = ramp_start + timedelta(minutes=i * 15)
    add_row(t,
            cpu=random.gauss(40 + progress * 55, 5),
            mem_used=random.gauss(3000 + progress * 4500, 200),
            mem_total=8192,
            in_err=random.gauss(1200 + progress * 3000, 100),
            out_err=random.gauss(300 + progress * 900, 40))

print(f"Prepared {len(rows)} rows ({n_normal} normal, {len(rows) - n_normal} anomalous across 8 categories)")

# ============================================================
# INSERT INTO DATABASE
# ============================================================
cursor.executemany("""
    INSERT INTO readings (device, collected_at, cpu, memory_used, memory_total, interface_in_errors, interface_out_errors)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", rows)

conn.commit()
conn.close()

print(f"Inserted {len(rows)} rows into network_monitor.db")
print("\nAnomaly categories included:")
print("  A. CPU overload spikes")
print("  B. Memory leak pattern (high memory, normal CPU)")
print("  C. Interface incoming-error bursts")
print("  D. Interface outgoing-error bursts")
print("  E. Combined catastrophic failure (all metrics spike together)")
print("  F. Time-inappropriate load (business-level activity at 2-4 AM)")
print("  G. Sudden idle drop (device goes abnormally quiet)")
print("  H. Slow degradation ramp (gradual creep toward failure)")


