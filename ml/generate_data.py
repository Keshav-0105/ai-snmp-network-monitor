import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect("../network_monitor.db")
cursor = conn.cursor()

base_time = datetime.now() - timedelta(days=5)

for i in range(150):
    timestamp = base_time + timedelta(minutes=i * 10)
    hour = timestamp.hour
    is_weekend = timestamp.weekday() >= 5

    if is_weekend:
        cpu = random.randint(15, 30)
        mem_used = random.randint(2200, 2900)
    elif 9 <= hour <= 18:
        cpu = random.randint(35, 55)
        mem_used = random.randint(3000, 3800)
    else:
        cpu = random.randint(10, 25)
        mem_used = random.randint(2000, 2800)

    mem_total = 8192

    if random.random() < 0.1:
        in_errors = random.randint(1350, 1500)
    else:
        in_errors = random.randint(1100, 1350)

    out_errors = random.randint(250, 400)

    cursor.execute("""
        INSERT INTO readings (device, collected_at, cpu, memory_used, memory_total, interface_in_errors, interface_out_errors)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("127.0.0.1", timestamp.isoformat(), cpu, mem_used, mem_total, in_errors, out_errors))

conn.commit()
conn.close()

print("Inserted 150 realistic historical readings")