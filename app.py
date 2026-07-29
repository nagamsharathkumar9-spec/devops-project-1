# EMA Backtester - Web API with PostgreSQL + Prometheus metrics
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import time
import pandas as pd
import random
import psycopg2
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

random.seed(42)

# ============================================================
# Prometheus metrics — supports SLO monitoring
# ============================================================
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['path'],
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

BACKTEST_COUNT = Counter(
    'backtest_runs_total',
    'Total number of backtests run'
)

DB_SAVE_COUNT = Counter(
    'db_saves_total',
    'Total database save operations',
    ['status']
)

# ============================================================
# DB connection from environment variables (injected from K8s Secret)
# ============================================================
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "backtestdb"),
    "user": os.environ.get("DB_USER", "backtester"),
    "password": os.environ.get("DB_PASSWORD", "backtester123"),
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id SERIAL PRIMARY KEY,
            run_at TIMESTAMP DEFAULT NOW(),
            total_trades INTEGER,
            win_rate FLOAT,
            total_pnl FLOAT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized.")

def run_backtest():
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

    result = {
        "total_trades": len(trade_log),
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "trades": trade_log
    }

    # Save to PostgreSQL
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO backtest_results (total_trades, win_rate, total_pnl) VALUES (%s, %s, %s)",
            (result["total_trades"], result["win_rate"], result["total_pnl"])
        )
        conn.commit()
        cur.close()
        conn.close()
        DB_SAVE_COUNT.labels(status="success").inc()
        print(f"Saved backtest result to database: {result['total_pnl']} P&L")
    except Exception as e:
        print(f"DB save error: {e}")
        DB_SAVE_COUNT.labels(status="error").inc()

    return result

def get_results():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, run_at, total_trades, win_rate, total_pnl FROM backtest_results ORDER BY run_at DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "run_at": r[1].isoformat(),
                "total_trades": r[2],
                "win_rate": r[3],
                "total_pnl": r[4]
            }
            for r in rows
        ]
    except Exception as e:
        return {"error": str(e)}

class BacktestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        start_time = time.time()

        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode())
            REQUEST_COUNT.labels(method="GET", path="/health", status="200").inc()

        elif self.path == "/backtest":
            result = run_backtest()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            REQUEST_COUNT.labels(method="GET", path="/backtest", status="200").inc()
            BACKTEST_COUNT.inc()

        elif self.path == "/results":
            results = get_results()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            REQUEST_COUNT.labels(method="GET", path="/results", status="200").inc()

        elif self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())

        else:
            self.send_response(404)
            self.end_headers()
            REQUEST_COUNT.labels(method="GET", path=self.path, status="404").inc()

        REQUEST_LATENCY.labels(path=self.path).observe(time.time() - start_time)

    def log_message(self, format, *args):
        print(f"Request: {args[0]}")

if __name__ == "__main__":
    init_db()
    server = HTTPServer(("0.0.0.0", 8000), BacktestHandler)
    print("EMA Backtester API running on port 8000")
    print("Endpoints: /health /backtest /results /metrics")
    server.serve_forever()