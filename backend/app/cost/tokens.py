import math


def count_tokens(text: str) -> int:
    """Estimate tokens as characters divided by 4, rounded up.

    The same function counts the estimate and the actual usage for the mock LLM.
    To use a real tokenizer later, change only this function.
    """
    if not text:
        return 0
    return math.ceil(len(text) / 4)