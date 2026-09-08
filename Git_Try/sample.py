from utils import add

def greet():
    print("Greetings, universe!")
    print("This line is intentionally changed to cause a merge conflict.")
    
def perform_calculation():
    # Expecting a dictionary return type now
    res = add(10.5, 20.3, 5.0, round_to=1)
    print(f"Calculation result: {res['total']} (from {res['count']} numbers)")

if __name__ == "__main__":
    greet()
    perform_calculation()
