nifty_close = 21500
print("Example 1 : simple if")
if nifty_close > 21000 :
    print("nifty is above 21000")

if nifty_close > 22000:
    print("nifty is above 22000 , ofcourse it will not print")

print("Example 2: if/else")
ema_9 = 21520
ema_21 = 21450

if ema_9 > ema_21:
    print("Bullish : 9 EMA is above 21 EMA")
else:
    print("Bearish : 9 EMA is below 21 EMA")

print("Example 3 : elif chain")
price_change = 0.5

if price_change > 1.0:
    print("strong move up")
elif price_change > 0:
    print("mild move up")
elif price_change == 0 :
    print("no change")
else: 
    print("move down")

print("Example 4 : and / or")
ema_9 = 21520
ema_21 = 21450
volume_high = True

if ema_9 > ema_21 and volume_high:
    print("strong bullish signal ( cross + volume)")

if ema_9 > ema_21 or volume_high:
    print("Atleast one condition met")
