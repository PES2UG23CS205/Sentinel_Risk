import pandas as pd
from pathlib import Path

data_dir = Path("data/external/fraud_handbook/data")
files = sorted(data_dir.glob("*.pkl"))
print(f"Total PKL files: {len(files)}")

df1 = pd.read_pickle(files[0]).sort_values("TX_DATETIME").reset_index(drop=True)
print(f"Day 1 total: {len(df1)}")
frauds_day1 = df1[df1["TX_FRAUD"] == 1]
print(f"Day 1 fraud count: {len(frauds_day1)}")
for pos, row in frauds_day1.iterrows():
    print(f"Position {pos}: ID={row['TRANSACTION_ID']}, Time={row['TX_DATETIME']}, Amount={row['TX_AMOUNT']}, Cust={row['CUSTOMER_ID']}, Scenario={row['TX_FRAUD_SCENARIO']}")
