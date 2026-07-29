# generate_data.py — Real Nifty data via yfinance
import yfinance as yf
import pandas as pd

def fetch_nifty_data(symbol="^NSEI", period="1y", interval="1d"):
    """
    Fetch real market data from Yahoo Finance.
    
    Symbols:
        ^NSEI    = Nifty 50
        ^NSEBANK = BankNifty
        ^CNXIT   = Nifty IT
        ^BSESN   = SENSEX
    
    Periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
    Intervals: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
    """
    print(f"Fetching {symbol} data ({period}, {interval} interval)...")
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    
    if df.empty:
        raise ValueError(f"No data returned for {symbol}. Check symbol and period.")
    
    # Standardize column names to lowercase
    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    
    # Keep only OHLCV columns
    df = df[["date", "open", "high", "low", "close", "volume"]]
    
    # Format date
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    
    # Round prices to 2 decimal places
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].round(2)
    
    print(f"Fetched {len(df)} candles for {symbol}")
    print(f"Date range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
    print(f"Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")
    print("\nFirst 5 rows:")
    print(df.head())
    print("\nLast 5 rows:")
    print(df.tail())
    
    return df

if __name__ == "__main__":
    # Fetch 1 year of daily Nifty 50 data
    df = fetch_nifty_data(symbol="^NSEI", period="1y", interval="1d")
    df.to_csv("nifty_data.csv", index=False)
    print(f"\nSaved {len(df)} rows to nifty_data.csv")