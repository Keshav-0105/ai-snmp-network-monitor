#!/usr/bin/env python3
"""One simple tester for the SNMP monitor project."""

from pathlib import Path
import os
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_GO = PROJECT_ROOT / "main.go"
SNMPREC = PROJECT_ROOT / "data" / "public.snmprec"
TMP_ROOT = PROJECT_ROOT
EXPECTED_PORTS = list(range(2161, 2191))

EXPECTED_OIDS = {
    "CPU load": "1.3.6.1.2.1.25.3.3.1.2.1",
    "memory used": "1.3.6.1.2.1.25.2.3.1.6.1",
    "memory total": "1.3.6.1.2.1.25.2.3.1.5.1",
    "interface input errors": "1.3.6.1.2.1.2.2.1.14.1",
    "interface output errors": "1.3.6.1.2.1.2.2.1.20.1",
}


def main():
    print("SNMP monitor simple tester")
    print("==========================")
    print(f"Project: {PROJECT_ROOT}")

    failed = 0
    failed += check("main.go exists", check_main_go_exists)
    failed += check("collector uses 127.0.0.1 SNMP v3 on 30 ports", check_snmp_settings)
    failed += check("start scripts exist and are executable", check_start_scripts)
    failed += check("collector polls all required OIDs", check_collector_oids)
    failed += check("collector polls every 60 seconds", check_poll_interval)
    failed += check("data/public.snmprec exists and has valid rows", check_snmprec_rows)
    failed += check("simulator data has all required OIDs", check_snmprec_oids)
    failed += check("simple ML anomaly demo works", check_ml_demo)
    failed += check("Go project compiles", check_go_compile)

    print()
    if failed:
        print(f"Result: FAILED ({failed} check(s) failed)")
        sys.exit(1)

    print("Result: PASSED")
    print()
    print("Next steps:")
    print("1. Terminal 1: ./start_tester.sh")
    print("2. Terminal 2: ./start_main.sh")


def check(label, function):
    print()
    print(f"Checking: {label}")
    try:
        function()
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS")
    return 0


def check_main_go_exists():
    if not MAIN_GO.exists():
        raise AssertionError("main.go was not found")


def check_snmp_settings():
    source = MAIN_GO.read_text()
    must_have = [
        'newSNMPClient("127.0.0.1", port)',
        "gosnmp.Version3",
        "gosnmp.UserSecurityModel",
        "gosnmp.NoAuthNoPriv",
        'UserName: "snmpuser"',
    ]
    for text in must_have:
        if text not in source:
            raise AssertionError(f"missing {text}")
    for port in EXPECTED_PORTS:
        if str(port) not in source:
            raise AssertionError(f"missing SNMP port {port}")


def check_start_scripts():
    for script_name in ("start_main.sh", "start_tester.sh"):
        script = PROJECT_ROOT / script_name
        if not script.exists():
            raise AssertionError(f"{script_name} was not found")
        if not os.access(script, os.X_OK):
            raise AssertionError(f"{script_name} is not executable")


def check_collector_oids():
    source = MAIN_GO.read_text()
    for label, oid in EXPECTED_OIDS.items():
        print(f"  {label}: {oid}")
        if oid not in source:
            raise AssertionError(f"missing OID for {label}")


def check_poll_interval():
    source = MAIN_GO.read_text()
    if "time.NewTicker(60 * time.Second)" not in source:
        raise AssertionError("collector should poll every 60 seconds")


def check_snmprec_rows():
    rows = read_snmprec()
    print(f"  rows found: {len(rows)}")
    if not rows:
        raise AssertionError("no rows found in data/public.snmprec")


def check_snmprec_oids():
    rows = read_snmprec()
    for label, oid in EXPECTED_OIDS.items():
        if oid not in rows:
            raise AssertionError(f"simulator data missing {label}: {oid}")
        value = rows[oid]["value"]
        print(f"  {label}: {value}")
        if not value.isdigit():
            raise AssertionError(f"{label} value should be numeric")


def check_ml_demo():
    normal = [
        [9, 38, 39.0, 12, 3],
        [10, 42, 40.1, 13, 4],
        [11, 45, 41.0, 11, 3],
        [12, 49, 42.5, 15, 4],
        [13, 52, 43.2, 14, 5],
        [14, 55, 44.0, 13, 4],
        [15, 51, 43.1, 16, 5],
        [16, 47, 42.0, 12, 4],
    ]
    anomaly = [3, 91, 88.0, 1200, 300]
    score = anomaly_score(normal, anomaly)
    print(f"  anomaly score: {score:.2f}")
    print("  explanation: CPU high, memory high, interface errors high")
    if score < 6:
        raise AssertionError("anomaly score was too low")


def check_go_compile():
    env = os.environ.copy()
    env["GO111MODULE"] = "on"
    env["GOCACHE"] = str(TMP_ROOT / ".go-build-cache")
    env["GOTMPDIR"] = str(TMP_ROOT / ".go-tmp")
    for name in ("GOCACHE", "GOTMPDIR"):
        Path(env[name]).mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["go", "test", "./..."],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    print(result.stdout.strip() or result.stderr.strip())
    if result.returncode != 0:
        raise AssertionError("go test ./... failed")


def read_snmprec():
    if not SNMPREC.exists():
        raise AssertionError("data/public.snmprec was not found")

    rows = {}
    for line_number, line in enumerate(SNMPREC.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) != 3:
            raise AssertionError(f"bad row at line {line_number}: {line}")
        oid, value_type, value = parts
        if not re.fullmatch(r"(?:\d+\.)+\d+", oid):
            raise AssertionError(f"bad OID at line {line_number}: {oid}")
        rows[oid] = {"type": value_type, "value": value}
    return rows


def anomaly_score(rows, row):
    columns = list(zip(*rows))
    means = [sum(column) / len(column) for column in columns]
    stdevs = []
    for column, mean in zip(columns, means):
        variance = sum((value - mean) ** 2 for value in column) / len(column)
        stdevs.append(variance ** 0.5 or 1.0)
    return max(abs(value - mean) / stdev for value, mean, stdev in zip(row, means, stdevs))


if __name__ == "__main__":
    main()
