index_name = "Nifty"
close_price = 21450.75
print(f"{index_name} closed at {close_price}")

entry = 21450
exit_price = 21605
print(f"Profit per unit: {exit_price - entry}")

pnl_percent = 2.380952380952381
print(f"P&L: {pnl_percent:.2f}%")

trade_number = 1
signal = "BUY"
price = 21420.50
ema_9 = 21480.30
ema_21 = 21460.10
print(f"Trade #{trade_number}: {signal} at {price}, EMA9={ema_9:.2f}, EMA21={ema_21:.2f}")

prices = [21450.75, 21505.30, 21420.50, 21610.25, 21595.80]
for i, price in enumerate(prices):
    print(f"Day {i}: Close = {price:.2f}")

    