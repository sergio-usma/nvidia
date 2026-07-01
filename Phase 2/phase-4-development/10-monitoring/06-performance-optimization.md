# Performance Optimization

This guide covers performance optimization for applications on Jetson AGX Orin.

## Python Optimization

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(x):
    return compute(x)
```

### Multiprocessing

```python
from multiprocessing import Pool

def process_item(item):
    return compute(item)

with Pool(4) as pool:
    results = pool.map(process_item, items)
```

### AsyncIO

```python
import asyncio

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
```

## NumPy Optimization

```python
import numpy as np

# Vectorized operations
result = np.sum(data ** 2, axis=1)

# In-place operations
np.add(data, 1, out=data)

# Memory mapping for large arrays
data = np.memmap('largefile.dat', dtype='float32', mode='r', shape=(10000, 10000))
```

## GPU Acceleration

```python
import torch

# Use GPU
device = torch.device('cuda')
model = model.to(device)
data = data.to(device)

# Mixed precision
with torch.cuda.amp.autocast():
    output = model(data)
```

## Database Optimization

```python
# Connection pooling
from sqlalchemy import create_engine
engine = create_engine(
    'postgresql://user:pass@localhost/db',
    pool_size=10,
    max_overflow=20
)

# Query optimization
result = session.query(User).filter_by(active=True).limit(100)
```

## Web Server Optimization

### Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### uvicorn

```bash
uvicorn app:app --workers 4 --limit-concurrency 100
```

### Nginx

```nginx
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    keepalive_timeout 65;
    client_max_body_size 10M;
    
    gzip on;
    gzip_types text/plain text/css application/json;
}
```

## Docker Optimization

```dockerfile
# Multi-stage build
FROM python:3.12-slim AS builder
RUN pip install --user -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
```

## Memory Optimization

```python
import gc

# Explicit garbage collection
gc.collect()

# Use __slots__
class Point:
    __slots__ = ['x', 'y']
    
# Generator instead of list
def get_items():
    for item in database:
        yield item
```

## Algorithmic Optimization

```python
# Instead of O(n^2)
seen = set()
for item in items:
    if item not in seen:
        seen.add(item)

# Use dict comprehension
result = {k: v for k, v in items if v > 0}
```

## CDN

```python
# Use CDN for static files
# In Flask
from flask_static_d import StaticD

app.config['CDN_DOMAIN'] = 'cdn.example.com'
cdn = StaticD(app)
```

## Profiling

```python
# cProfile
python -m cProfile -s cumtime app.py

# Line profiler
@profile
def slow_function():
    pass

# Memory profiler
@profile
def memory_heavy():
    data = [x**2 for x in range(1000000)]
    return data
```

## Benchmarking

```python
import timeit

result = timeit.timeit(
    'func()',
    setup='from __main__ import func',
    number=1000
)
print(f"Time: {result:.4f}s")
```

## C Extensions

```python
# Cython
# hello.pyx
def say_hello():
    print("Hello")

# setup.py
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="hello",
    ext_modules=cythonize("hello.pyx")
)
```

## JIT Compilation

```python
# Numba
from numba import jit

@jit(nopython=True)
def fast_sum(arr):
    total = 0.0
    for i in range(len(arr)):
        total += arr[i]
    return total
```
