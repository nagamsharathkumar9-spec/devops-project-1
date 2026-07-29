trade = {
    "entry_price" : 21450.50,
    "exit_price" :21605.75,
    "quantity" : 50,
    "pnl" : 7762.50,
    "is_winner" : True,
    }
print(trade)

print(trade["entry_price"])
print(trade["pnl"])

trade["exit_date"] = "2026-06-09"
trade["quantity"] = 75
print(trade)

del trade["is_winner"]
print(trade)

if "entry_price" in trade:
    print(" entry_price is in the dictionary")

if "stop_loss" in trade:
    print("stop_loss is set")
else:
    print("stop_loss is not set")

print("All keys:")
for key in trade.keys():
    print(key)

print("All values:")
for value in trade.values():
    print(value)

print("Key + value pairs:")
for key , value in trade.items():
    print( key, "=", value)

print("Number of keys:" , len(trade))

# A real trade log will look like this — a LIST of DICTIONARIES
trade_log = [
    {"entry": 21450, "exit": 21605, "pnl": 155, "type": "BUY"},
    {"entry": 21610, "exit": 21500, "pnl": 110, "type": "SELL"},
    {"entry": 21520, "exit": 21680, "pnl": 160, "type": "BUY"}
]

# To find the best trade:
best_trade = max(trade_log, key=lambda t: t["pnl"])