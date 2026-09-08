import logging
import math

logger = logging.getLogger(__name__)

def add(*numbers: float, round_to: int = 2) -> dict:
    """Adds multiple numbers and returns a detailed dictionary."""
    logger.info(f"Adding numbers: {numbers}")
    if not numbers:
        return {"total": 0, "status": "empty"}
    
    total = sum(numbers)
    return {
        "total": round(total, round_to),
        "count": len(numbers),
        "operation": "addition"
    }

def multiply(a, b):
    return a * b
def multiply(a, b):
    return a * b
