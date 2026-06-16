# EMA Crossover Backtester v1
# Strategy: Buy when 9 EMA crosses above 21 EMA, Sell when it crosses below
import pandas as pd

# ============================================
# STEP 1: Load data
# ============================================
df = pd.read_csv("nifty_data.csv")
print(f"Loaded {len(df)} candles of Nifty data.")

# ============================================
# STEP 2: Calculate EMAs
# ============================================

df["ema_9"] = df["close"].ewm(span=9).mean()
df["ema_21"] = df["close"].ewm(span=21).mean()

print("EMAs calculated. First 5 rows with EMAs:")
print(df[["date", "close", "ema_9", "ema_21"]].head())

# ============================================
# STEP 3: Detect crossover signals
# ============================================
# We need to compare TODAY's EMAs with YESTERDAY's EMAs


df["prev_ema_9"] = df["ema_9"].shift(1)
df["prev_ema_21"] = df["ema_21"].shift(1)

# Golden cross: 9 EMA was BELOW 21 EMA yesterday, now ABOVE today
# Death cross:  9 EMA was ABOVE 21 EMA yesterday, now BELOW today

def detect_signal(row):
    if pd.isna(row["prev_ema_9"]) or pd.isna(row["prev_ema_21"]):
        return "HOLD"
    if row["ema_9"] > row["ema_21"] and row["prev_ema_9"] <= row["prev_ema_21"]:
        return "BUY"
    elif row["ema_9"] < row["ema_21"] and row["prev_ema_9"] >= row["prev_ema_21"]:
        return "SELL"
    else:
        return "HOLD"

df["signal"] = df.apply(detect_signal, axis=1)

# Show only rows where a signal was generated
signals_df = df[df["signal"] != "HOLD"]
print(f"\nTotal signals detected: {len(signals_df)}")
print(signals_df[["date", "close", "ema_9", "ema_21", "signal"]])

# ============================================
# STEP 4: Simulate trades
# ============================================
trade_log = []
position = None

for i, row in df.iterrows():
    if row["signal"] == "BUY" and position is None:
        position = {
            "entry_date": row["date"],
            "entry_price": row["close"]
        }

    elif row["signal"] == "SELL" and position is not None:
        pnl = row["close"] - position["entry_price"]
        trade = {
            "entry_date": position["entry_date"],
            "entry_price": position["entry_price"],
            "exit_date": row["date"],
            "exit_price": row["close"],
            "pnl": round(pnl, 2),
            "is_winner": pnl > 0
        }
        trade_log.append(trade)
        position = None

# ============================================
# STEP 5: Calculate performance metrics
# ============================================
if len(trade_log) > 0:
    total_trades = len(trade_log)
    winners = sum(1 for t in trade_log if t["is_winner"])
    losers = total_trades - winners
    total_pnl = sum(t["pnl"] for t in trade_log)
    win_rate = (winners / total_trades) * 100

    print(f"\n{'='*50}")
    print(f"BACKTEST RESULTS: 9/21 EMA Crossover on Nifty")
    print(f"{'='*50}")
    print(f"Total trades: {total_trades}")
    print(f"Winners: {winners}")
    print(f"Losers: {losers}")
    print(f"Win rate: {win_rate:.2f}%")
    print(f"Total P&L (per unit): {total_pnl:.2f}")
    print(f"{'='*50}")

    print(f"\nDetailed Trade Log:")
    print(f"{'='*50}")
    for i, trade in enumerate(trade_log):
        result = "WIN" if trade["is_winner"] else "LOSS"
        print(f"Trade {i+1}: {result} | Entry: {trade['entry_date']} @ {trade['entry_price']:.2f} | Exit: {trade['exit_date']} @ {trade['exit_price']:.2f} | P&L: {trade['pnl']:.2f}")
else:
    print("No trades were generated.")

# ============================================
# STEP 6: Save results
# ============================================
df.to_csv("backtest_output.csv", index=False)
print(f"\nFull data with EMAs and signals saved to backtest_output.csv")

if len(trade_log) > 0:
    trades_df = pd.DataFrame(trade_log)
    trades_df.to_csv("trade_log.csv", index=False)
    print(f"Trade log saved to trade_log.csv")