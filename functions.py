def say_hello():
    print("Hello from a function!")

say_hello()
say_hello()

def greet(name):
    print("hello ," , name)

greet("sharath")
greet("Devops world")

def add(a, b):
    result = a + b
    return result
total = add (5 , 3)
print("Total : ", total)
print("Another total :" , add (100 , 200))

def calculate_percentage_change(old_price , new_price):
    change = ((new_price - old_price)/ old_price) * 100
    return change

pct = calculate_percentage_change(21000 , 21500)
print("Percentage change : ", pct)

def power(base , exponant=2):
    return base ** exponant

print("5 to the power of 2 (default) :" , power(5))
print("5 to the power of 3 (override):" , power(5 ,3))

# --- Understanding check verification ---
print("--- Q1 ---")
def double(x):
    return x * 2
print(double(5))

print("--- Q2 ---")
def hello(name):
    print("Hi", name)
result = hello("Sharath")
print(result)

print("--- Q3 ---")
def greet(name, greeting="Hello"):
    return greeting + ", " + name
print(greet("Sharath"))
print(greet("Sharath", "Hi"))

print("--- Q4 ---")
def calculate(a, b):
    sum_result = a + b
    diff_result = a - b
    return sum_result
result = calculate(10, 3)
print(result)



def test(a , b , c):
    sum = a + b + c
    return sum

testok = test(10 ,20 , 30)
print(testok)