from utils import add

# Dummy comment added by automation for feature-test branch

def greet():
    print("Greetings, universe!")
    print("Hello, awesome world!")
    print("This line is intentionally changed to cause a merge conflict.")
    print("Testing merge conflicts with AI Git Push project!")

def perform_calculation():
    # Expecting a dictionary return type now
    res = add(10.5, 20.3, 5.0, round_to=1)
    print(f"Calculation result: {res['total']} (from {res['count']} numbers)")

if __name__ == "__main__":
    greet()
    perform_calculation()