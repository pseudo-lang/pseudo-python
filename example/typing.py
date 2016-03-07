from typing import Dict, List, Tuple, Callable

def f(s: Callable[[int], int]) -> int:
    return s(2)

class A:
    def expand(self, a: int) -> 'B':
        return B(a)

class B:
    def __init__(self, a):
        self.a = a        

# f(2)

