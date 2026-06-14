import pandas as pd

data = {
    "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
    "open": [21400, 21450, 21505, 21420, 21580],
    "high": [21500, 21550, 21620, 21490, 21680],
    "low": [21380, 21420, 21470, 21380, 21520],
    "close": [21450.75, 21505.30, 21420.50, 21610.25, 21595.80]
}
df = pd.DataFrame(data)

df.to_csv("nifty_sample.csv", index=False)
print("nifty_sample.csv has been saved to disk.")

loaded_df = pd.read_csv("nifty_sample.csv")
print("Loaded from CSV:")
print(loaded_df)

print("Shape:", loaded_df.shape)

loaded_df["close_plus_100"] = loaded_df["close"] + 100
print("After adding new column:")
print(loaded_df)

high_close_df = loaded_df[loaded_df["close"] > 21500]
high_close_df.to_csv("high_closes.csv", index=False)
print("high_closes.csv saved with", len(high_close_df), "rows.")
