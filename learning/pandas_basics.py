import pandas as pd

data = {
    "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
    "open": [21400, 21450, 21505, 21420, 21580],
    "high": [21500, 21550, 21620, 21490, 21680],
    "low": [21380, 21420, 21470, 21380, 21520],
    "close": [21450.75, 21505.30, 21420.50, 21610.25, 21595.80]
}

df = pd.DataFrame(data)
print("Full DataFrame:")
print(df)

print("Shape (rows, coloumns):", df.shape)
print("Coloumn name:", df.columns.tolist())

print("First 3 rows:")
print(df.head(3))

print("Last 2 rows:")
print(df.tail(2))

print("Close prices only:")
print(df["close"])

print("Date + Close columns:")
print(df[["date", "close"]])

print("Close + 100 across all rows:")
print(df["close"] + 100)

df["close_plus_100"] = df["close"] + 100
print("DataFrame with new column:")
print(df)

print("Rows where close > 21500:")
print(df[df["close"] > 21500])