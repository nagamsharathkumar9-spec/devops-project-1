# EMA Crossover Backtester v2 — Real Nifty Data
# Strategy: 9/21 EMA crossover on NSE indices

import pandas as pd
from generate_data import fetch_nifty_data

# ============================================
# CONFIGURATION
# ============================================
SYMBOL = "^NSEI"        # Nifty 50 (change to ^NSEBANK for BankNifty)
PERIOD = "1y"           # 1 year of data
EMA_SHORT = 9
EMA_LONG = 21

# ============================================
# STEP 1: Load real market data
# ============================================
print(f"\nRunning EMA {EMA_SHORT}/{EMA_LONG} Crossover Backtest on {SYMBOL}")
print("=" * 60)

df = fetch_nifty_data(symbol=SYMBOL, period=PERIOD)
print(f"\nLoaded {len(df)} candles of real market data.")

# ============================================
# STEP 2: Calculate EMAs
# ============================================
df["ema_short"] = df["close"].ewm(span=EMA_SHORT).mean()
df["ema_long"] = df["close"].ewm(span=EMA_LONG).mean()
df["prev_ema_short"] = df["ema_short"].shift(1)
df["prev_ema_long"] = df["ema_long"].shift(1)

# ============================================
# STEP 3: Detect crossover signals
# ============================================
def detect_signal(row):
    if pd.isna(row["prev_ema_short"]):
        return "HOLD"
    if row["ema_short"] > row["ema_long"] and row["prev_ema_short"] <= row["prev_ema_long"]:
        return "BUY"
    elif row["ema_short"] < row["ema_long"] and row["prev_ema_short"] >= row["prev_ema_long"]:
        return "SELL"
    return "HOLD"

df["signal"] = df.apply(detect_signal, axis=1)
signals_df = df[df["signal"] != "HOLD"]
print(f"\nTotal signals detected: {len(signals_df)}")

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
        trade_log.append({
            "entry_date": position["entry_date"],
            "entry_price": position["entry_price"],
            "exit_date": row["date"],
            "exit_price": row["close"],
            "pnl": round(pnl, 2),
            "is_winner": pnl > 0
        })
        position = None

# ============================================
# STEP 5: Performance metrics
# ============================================
if len(trade_log) > 0:
    total_trades = len(trade_log)
    winners = sum(1 for t in trade_log if t["is_winner"])
    losers = total_trades - winners
    total_pnl = round(sum(t["pnl"] for t in trade_log), 2)
    win_rate = round((winners / total_trades) * 100, 2)
    avg_win = round(sum(t["pnl"] for t in trade_log if t["is_winner"]) / max(winners, 1), 2)
    avg_loss = round(sum(t["pnl"] for t in trade_log if not t["is_winner"]) / max(losers, 1), 2)
    best_trade = max(trade_log, key=lambda t: t["pnl"])
    worst_trade = min(trade_log, key=lambda t: t["pnl"])

    print(f"\n{'=' * 60}")
    print(f"BACKTEST RESULTS: {EMA_SHORT}/{EMA_LONG} EMA Crossover on {SYMBOL}")
    print(f"{'=' * 60}")
    print(f"Period:          {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
    print(f"Total trades:    {total_trades}")
    print(f"Winners:         {winners}")
    print(f"Losers:          {losers}")
    print(f"Win rate:        {win_rate}%")
    print(f"Total P&L:       {total_pnl} points")
    print(f"Avg win:         {avg_win} points")
    print(f"Avg loss:        {avg_loss} points")
    print(f"Best trade:      {best_trade['entry_date']} → {best_trade['exit_date']} | P&L: {best_trade['pnl']}")
    print(f"Worst trade:     {worst_trade['entry_date']} → {worst_trade['exit_date']} | P&L: {worst_trade['pnl']}")
    print(f"{'=' * 60}")

    print(f"\nDetailed Trade Log:")
    print(f"{'=' * 60}")
    for i, trade in enumerate(trade_log):
        result = "WIN" if trade["is_winner"] else "LOSS"
        print(f"Trade {i+1:2d}: {result} | "
              f"Entry: {trade['entry_date']} @ {trade['entry_price']:.2f} | "
              f"Exit:  {trade['exit_date']} @ {trade['exit_price']:.2f} | "
              f"P&L: {trade['pnl']:+.2f}")

    # Save results
    trades_df = pd.DataFrame(trade_log)
    trades_df.to_csv("trade_log.csv", index=False)
    print(f"\nTrade log saved to trade_log.csv")
else:
    print("No completed trades found.")