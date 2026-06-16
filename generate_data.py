import pandas as pd
import random

random.seed(42)

dates = pd.date_range(start="2026-01-01", periods=50, freq="B")

price = 21500.0
rows = []

for date in dates:
    change = random.uniform(-150, 150)
    open_price = round(price, 2)
    close_price = round(price + change, 2)
    high_price = round(max(open_price, close_price) + random.uniform(10, 80), 2)
    low_price = round(min(open_price, close_price) - random.uniform(10, 80), 2)
    rows.append({
        "date": date.strftime("%Y-%m-%d"),
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price
    })
    price = close_price


df = pd.DataFrame(rows)
df.to_csv("nifty_data.csv", index=False)
print(f"Generated {len(df)} rows of sample data.")
print("First 5 rows:")
print(df.head())
print("Last 5 rows:")
print(df.tail())