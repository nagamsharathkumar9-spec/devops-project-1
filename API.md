# API Documentation — EMA Backtester

Base URL (local): `http://localhost:8000`  
Base URL (EKS via port-forward): `http://localhost:8001`

---

## GET /health

Health check endpoint. Used by Kubernetes liveness and readiness probes.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status codes:**
- `200 OK` — service is healthy
- `500` — service is unhealthy (probe will restart pod)

---

## GET /backtest

Runs the 9/21 EMA crossover strategy on real Nifty 50 data (1 year),
saves the result to PostgreSQL, and returns the analysis.

**Response:**
```json
{
  "total_trades": 9,
  "win_rate": 11.11,
  "total_pnl": -2303.75,
  "trades": [
    {
      "entry_date": "2025-10-07",
      "entry": 25108.30,
      "exit_date": "2025-12-17",
      "exit": 25818.55,
      "pnl": 710.25,
      "result": "WIN"
    }
  ]
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `total_trades` | int | Number of completed trades |
| `win_rate` | float | Percentage of winning trades |
| `total_pnl` | float | Total profit/loss in Nifty points |
| `trades` | array | Detailed log of each trade |

**Side effects:** Result is saved to PostgreSQL `backtest_results` table.

---

## GET /results

Returns all historical backtest results from PostgreSQL, ordered by most recent first.

**Response:**
```json
[
  {
    "id": 2,
    "run_at": "2026-07-29T10:15:06.157422",
    "total_trades": 9,
    "win_rate": 11.11,
    "total_pnl": -2303.75
  },
  {
    "id": 1,
    "run_at": "2026-07-29T10:15:04.909625",
    "total_trades": 9,
    "win_rate": 11.11,
    "total_pnl": -2303.75
  }
]
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Auto-incremented primary key |
| `run_at` | string | ISO 8601 timestamp of when backtest ran |
| `total_trades` | int | Number of completed trades |
| `win_rate` | float | Percentage of winning trades |
| `total_pnl` | float | Total P&L in Nifty points |

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `404` | Endpoint not found |
| `500` | Internal server error (check pod logs) |