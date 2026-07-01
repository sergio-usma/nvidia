# Python Type Hints

This guide covers Python type hints for better code quality on Jetson AGX Orin.

## Basic Types

```python
# Primitive types
name: str = "John"
age: int = 30
height: float = 5.9
is_active: bool = True

# Lists
numbers: list[int] = [1, 2, 3]
names: list[str] = ["a", "b"]

# Dictionaries
user: dict[str, str] = {"name": "John", "email": "john@example.com"}

# Optional
name: str | None = None
```

## Functions

```python
def greet(name: str) -> str:
    return f"Hello, {name}"

def add(a: int, b: int) -> int:
    return a + b

def process(items: list[int]) -> dict[str, int]:
    return {"sum": sum(items), "count": len(items)}
```

## Classes

```python
class User:
    def __init__(self, name: str, email: str):
        self.name: str = name
        self.email: str = email
    
    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "email": self.email}
```

## TypeAlias

```python
from typing import TypeAlias

Matrix: TypeAlias = list[list[float]]

def transform(matrix: Matrix) -> Matrix:
    return [[matrix[j][i] for j in range(len(matrix))] for i in range(len(matrix[0]))]
```

## TypedDict

```python
from typing import TypedDict

class UserDict(TypedDict):
    name: str
    email: str
    age: int

user: UserDict = {
    "name": "John",
    "email": "john@example.com",
    "age": 30
}
```

## Generics

```python
from typing import Generic, TypeVar

T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self) -> None:
        self.items: list[T] = []
    
    def push(self, item: T) -> None:
        self.items.append(item)
    
    def pop(self) -> T:
        return self.items.pop()

stack: Stack[int] = Stack()
stack.push(1)
```

## Union Types

```python
from typing import Union

def process(value: Union[str, int]) -> str:
    return str(value)

# Or modern syntax
def process(value: str | int) -> str:
    return str(value)
```

## Callable

```python
from typing import Callable

def apply(func: Callable[[int], int], value: int) -> int:
    return func(value)

def double(x: int) -> int:
    return x * 2

result = apply(double, 5)
```

## Type Checking

```bash
# Install mypy
pip install mypy

# Run type check
mypy mymodule.py

# Strict mode
mypy --strict mymodule.py
```

## Pylance/VSCode

VSCode with Pylance provides real-time type checking:

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true
}
```

## Dataclasses

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    email: str
    age: int = 0
    
    def to_dict(self) -> dict[str, str | int]:
        return {"name": self.name, "email": self.email, "age": self.age}
```

## Named Tuples

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
    
    def distance(self, other: "Point") -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2) ** 0.5
```

## Final

```python
from typing import Final

MAX_RETRIES: Final = 3
API_VERSION: Final = "1.0.0"
```

## Overload

```python
from typing import overload

@overload
def process(value: int) -> int: ...
@overload
def process(value: str) -> str: ...

def process(value: int | str) -> int | str:
    return value
```
