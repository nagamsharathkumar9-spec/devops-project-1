# CloudWatch Insights Queries — EMA Backtester

Saved queries for operational monitoring of the EMA Backtester platform.
Run these in AWS Console → CloudWatch → Logs Insights.

Log group: `/aws/containerinsights/ema-backtester-cluster/application`

---

## Query 1: Error Log Detection

Find all ERROR level logs from the backtester in the last hour.
Use this when: alerts fire, something looks wrong, debugging incidents.

fields @timestamp, @message, @logStream
| filter @logStream like /ema-backtester/
| filter @message like /ERROR/ or @message like /error/ or @message like /Exception/
| sort @timestamp desc
| limit 50


---

## Query 2: API Request Log

Track all incoming API requests — useful for traffic analysis and debugging.

fields @timestamp, @message
| filter @logStream like /ema-backtester/
| filter @message like /Request:/
| parse @message "Request: " as endpoint
| stats count() as request_count by endpoint
| sort request_count desc


---

## Query 3: Database Connection Issues

Detect PostgreSQL connection failures — fires before CrashLoopBackOff occurs.

fields @timestamp, @message
| filter @logStream like /ema-backtester/
| filter @message like /DB save error/
or @message like /connection refused/
or @message like /could not connect/
| sort @timestamp desc
| limit 20


---

## Query 4: Backtest Execution Tracking

Track every backtest run and its database save status.

fields @timestamp, @message
| filter @logStream like /ema-backtester/
| filter @message like /Saved backtest result/
or @message like /Running EMA/
| sort @timestamp desc
| limit 100


---

## How to use in AWS Console

1. Go to AWS Console → CloudWatch → Log Insights
2. Select log group: `/aws/containerinsights/ema-backtester-cluster/application`
3. Set time range (Last 1 hour / Last 3 hours / Custom)
4. Paste query → click "Run query"
5. Results appear in table format, exportable to CSV