import sqlite3
import os
import json
import glob
import pandas as pd
import requests

def inspect_database():
    print("=== 1. DATABASE AUDIT ===")
    conn = sqlite3.connect('sentinelrisk.db')
    cursor = conn.cursor()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print("Tables:", [t[0] for t in tables])
    for t in tables:
        count = cursor.execute(f"SELECT count(*) FROM {t[0]}").fetchone()[0]
        print(f"  - {t[0]}: {count:,} rows")
    conn.close()

def inspect_endpoints():
    print("\n=== 2. API ENDPOINTS AUDIT ===")
    base = "http://localhost:8000"
    endpoints = [
        ("GET", "/health"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/health/metrics"),
        ("GET", "/api/v1/metrics/summary"),
        ("GET", "/api/v1/cases/"),
        ("GET", "/api/v1/incidents/active"),
        ("GET", "/api/v1/incidents/history"),
        ("GET", "/stream/live-state"),
        ("GET", "/dashboard"),
        ("GET", "/docs"),
        ("GET", "/download"),
    ]
    for method, path in endpoints:
        try:
            if method == "GET":
                r = requests.get(f"{base}{path}", timeout=3)
            print(f"  {method:4s} {path:<30s} -> Status: {r.status_code}")
        except Exception as e:
            print(f"  {method:4s} {path:<30s} -> FAILED ({e})")

def test_scenarios():
    print("\n=== 3. DEMO SCENARIOS AUDIT ===")
    base = "http://localhost:8000"
    scenarios = [
        "LEGITIMATE_TRANSACTION",
        "ACCOUNT_TAKEOVER",
        "COORDINATED_ABUSE_RING",
        "CARD_TESTING",
        "WHAT_BROKE_AT_2AM",
    ]
    for s in scenarios:
        try:
            r = requests.post(f"{base}/dashboard/evaluate-scenario/{s}", timeout=5)
            data = r.json()
            dec = data.get("decision")
            trig = data.get("primary_trigger")
            print(f"  Scenario: {s:<28s} -> Status: {r.status_code} | Decision: {dec} | Trigger: {trig}")
        except Exception as e:
            print(f"  Scenario: {s:<28s} -> FAILED ({e})")

if __name__ == "__main__":
    inspect_database()
    inspect_endpoints()
    test_scenarios()
