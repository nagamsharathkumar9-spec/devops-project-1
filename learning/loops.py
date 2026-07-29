prices = [21450.75, 21505.30, 21420.50, 21610.25, 21595.80]

print("Example 1 : Each price")
for price in prices:
    print (price)

print("Example 2 :Each price + 100")
for price in prices:
    new_price = price + 100
    print(new_price)

print("Example 3: range loop")
for i in range(5):
    print(i)

print("Example 4 : enumerate(index + value)")
for index ,price in enumerate(prices):
    print(index , price)

# --- Understanding check verification ---
print("--- Q1 ---")
nums = [10, 20, 30]
for n in nums:
    print(n * 2)

print("--- Q2 ---")
for i in range(3):
    print(i)

print("--- Q3 ---")
words = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
for position, word in enumerate(words):
    print(position, word)

print("--- Q4 ---")
total = 0
for n in [5, 10, 15]:
    total = total + n
print(total)