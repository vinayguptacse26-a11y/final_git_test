from utils import add

# Dummy comment added by automation for feature-test branch

def greet():
    print("hello from Anshu Sharma from behroad")


def perform_calculation():
    # Expecting a dictionary return type now
    res = add(10.5, 20.3, 5.0, round_to=1)
    print(f"Calculation result: {res['total']} (from {res['count']} numbers)")

if __name__ == "__main__":
    greet()
    perform_calculation()
