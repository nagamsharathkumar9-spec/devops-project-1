indices = ["Nifty" , "BankNifty", "FinNifty"]
candle_counts = [50 ,100 ,200, 365]
nifty_closes = [21450.75, 21505.30, 21420.50, 21610.25, 21595.80]
print(indices)
print(candle_counts)
print(nifty_closes)
print(indices[0])
print(indices[1])
print(indices[2])
print(nifty_closes[-1])
print(nifty_closes[-2])
print(len(nifty_closes))
nifty_closes.append(21700.45)
print(nifty_closes)
print(len(nifty_closes))


print(nifty_closes[1:3])
print(nifty_closes[:3])
print(nifty_closes[2:])
print(nifty_closes[-3:])
print(nifty_closes[:-1])

prices = [100,200,300,400,500,600,700]
print(prices[2])
print(prices[-1])
print(prices[2:5])
print(prices[-3:])
print(prices[:-2])
