import random

class CrazyString:
    def __init__(self, temperature: float = 0.7):
        self.temperature = temperature

    def crazify(self, text: str) -> str:
        lower = True
        result = []
        for char in text:
            if not char.isalpha():
                result.append(char)
                continue
            result.append((str.lower if lower else str.upper)(char))
            lower = lower if (random.random() > self.temperature) else not lower
        return "".join(result)
    
def reverse_string(text: str) -> str:
    return text[::-1]
