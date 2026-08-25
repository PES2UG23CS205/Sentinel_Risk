\"\"\"
SentinelRisk — Fraud Detection Handbook Dataset Downloader

Downloads the simulated daily transaction pickle files from the official 
Fraud Detection Handbook repository:
https://github.com/Fraud-Detection-Handbook/simulated-data-raw
\"\"\"

import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BASE_URL = \"https://github.com/Fraud-Detection-Handbook/simulated-data-raw/raw/main/data/\"
OUTPUT_DIR = Path(\"data/external/fraud_handbook/data\")

START_DATE = datetime(2018, 4, 1)
END_DATE = datetime(2018, 9, 30)

def download_dataset(days_limit: int | None = None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    current_date = START_DATE
    count = 0
    total_days = (END_DATE - START_DATE).days + 1
    if days_limit:
        total_days = min(total_days, days_limit)
        
    print(f\"Downloading Fraud Detection Handbook dataset to: {OUTPUT_DIR}\")
    print(f\"Date Range: {START_DATE.strftime('%Y-%m-%d')} to {(START_DATE + timedelta(days=total_days-1)).strftime('%Y-%m-%d')} ({total_days} files)\")
    
    while current_date <= END_DATE and (days_limit is None or count < days_limit):
        file_name = f\"{current_date.strftime('%Y-%m-%d')}.pkl\"
        dest_path = OUTPUT_DIR / file_name
        url = f\"{BASE_URL}{file_name}\"
        
        if dest_path.exists():
            print(f\"[{count+1}/{total_days}] Already exists: {file_name}\")
        else:
            print(f\"[{count+1}/{total_days}] Downloading {file_name}...\", end=\" \", flush=True)
            try:
                urllib.request.urlretrieve(url, dest_path)
                print(\"Done\")
            except Exception as e:
                print(f\"Failed ({e})\")
                
        current_date += timedelta(days=1)
        count += 1
        
    print(\"\nDownload complete! Run 'python scripts/replay_fraud_handbook.py --limit 1000' to test.\")

if __name__ == \"__main__\":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    download_dataset(limit)
