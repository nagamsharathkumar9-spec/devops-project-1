# EMA Backtester - Web API version
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import pandas as pd
import random

random.seed(42)

def run_backtest():
    # Generate data
    dates = pd.date_range(start="2026-01-01", periods=50, freq="B")
    price = 21500.0
    rows = []
    for date in dates:
        change = random.uniform(-150, 150)
        open_price = round(price, 2)
        close_price = round(price + change, 2)
        rows.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": open_price,
            "close": close_price,
        })
        price = close_price

    df = pd.DataFrame(rows)
    df["ema_9"] = df["close"].ewm(span=9).mean()
    df["ema_21"] = df["close"].ewm(span=21).mean()
    df["prev_ema_9"] = df["ema_9"].shift(1)
    df["prev_ema_21"] = df["ema_21"].shift(1)

    trade_log = []
    position = None

    for i, row in df.iterrows():
        if pd.isna(row["prev_ema_9"]):
            continue
        if row["ema_9"] > row["ema_21"] and row["prev_ema_9"] <= row["prev_ema_21"]:
            if position is None:
                position = {"entry": row["close"], "entry_date": row["date"]}
        elif row["ema_9"] < row["ema_21"] and row["prev_ema_9"] >= row["prev_ema_21"]:
            if position is not None:
                pnl = round(row["close"] - position["entry"], 2)
                trade_log.append({
                    "entry_date": position["entry_date"],
                    "entry": position["entry"],
                    "exit_date": row["date"],
                    "exit": row["close"],
                    "pnl": pnl,
                    "result": "WIN" if pnl > 0 else "LOSS"
                })
                position = None

    total_pnl = sum(t["pnl"] for t in trade_log)
    win_rate = (sum(1 for t in trade_log if t["result"] == "WIN") / len(trade_log) * 100) if trade_log else 0

    return {
        "total_trades": len(trade_log),
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "trades": trade_log
    }

class BacktestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
        elif self.path == "/backtest":
            result = run_backtest()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"Request: {args[0]}")

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), BacktestHandler)
    print("EMA Backtester API running on port 8000")
    server.serve_forever()