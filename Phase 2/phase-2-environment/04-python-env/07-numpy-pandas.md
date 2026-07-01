# NumPy and Pandas for Data Science

This guide covers NumPy and Pandas installation and usage for AI/ML on Jetson AGX Orin.

## Install NumPy

```bash
pip install numpy
```

Verify:

```python
import numpy as np
print(np.__version__)
```

## Install Pandas

```bash
pip install pandas
```

Verify:

```python
import pandas as pd
print(pd.__version__)
```

## NumPy Basics

```python
import numpy as np

# Create array
arr = np.array([1, 2, 3, 4, 5])

# 2D array
matrix = np.array([[1, 2, 3], [4, 5, 6]])

# Zeros
zeros = np.zeros((3, 3))

# Ones
ones = np.ones((2, 4))

# Range
range_arr = np.arange(0, 10, 2)

# Random
rand = np.random.rand(3, 3)
randn = np.random.randn(1000)
randint = np.random.randint(0, 100, (5, 5))

# Operations
arr * 2
arr + 10
np.sin(arr)
np.mean(arr)
np.std(arr)
```

## Array Operations

```python
# Reshape
arr = np.arange(12)
reshaped = arr.reshape(3, 4)

# Transpose
transposed = reshaped.T

# Slicing
subset = arr[2:5]
subset = matrix[0:2, 1:3]

# Broadcasting
a = np.array([[1], [2], [3]])
b = np.array([10, 20, 30])
result = a + b
```

## NumPy for ML

```python
# Normalization
data = np.random.rand(100, 10)
normalized = (data - data.mean(axis=0)) / data.std(axis=0)

# One-hot encoding
labels = np.array([0, 1, 2, 1, 0])
one_hot = np.eye(3)[labels]

# Dot product
a = np.random.rand(100, 50)
b = np.random.rand(50, 10)
result = np.dot(a, b)

# Matrix multiplication
result = a @ b
```

## Pandas Basics

```python
import pandas as pd

# DataFrame from dict
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'score': [85.5, 90.0, 78.5]
})

# From CSV
df = pd.read_csv('data.csv')

# From API
df = pd.read_json('https://api.example.com/data')
```

## DataFrame Operations

```python
# Head/Tail
df.head()
df.tail()

# Info
df.info()
df.describe()

# Selection
df['column']
df[['col1', 'col2']]
df.iloc[0:5]
df.loc[0:5, 'column']

# Filtering
df[df['age'] > 25]
df[(df['age'] > 25) & (df['score'] > 80)]

# Missing values
df.isnull()
df.fillna(0)
df.dropna()
```

## Data Manipulation

```python
# Add column
df['new_col'] = df['col1'] + df['col2']

# Drop column
df.drop('column', axis=1)

# Rename
df.rename(columns={'old': 'new'})

# Group by
df.groupby('category').mean()

# Merge
merged = pd.merge(df1, df2, on='key')

# Pivot
pivot = df.pivot_table(values='score', index='name', columns='category')
```

## Time Series

```python
# Datetime
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# Resample
monthly = df.resample('M').sum()
daily = df.resample('D').mean()

# Rolling
df['rolling_mean'] = df['value'].rolling(window=7).mean()
```

## Integration with NumPy

```python
# NumPy to DataFrame
arr = np.random.rand(100, 5)
df = pd.DataFrame(arr, columns=['a', 'b', 'c', 'd', 'e'])

# DataFrame to NumPy
arr = df.values
arr = df.to_numpy()
```

## Performance Tips

```python
# Vectorization instead of loops
# Bad
result = []
for x in data:
    result.append(x * 2)

# Good
result = data * 2

# Use appropriate dtypes
df['category'] = df['category'].astype('category')

# Use inplace operations
df.drop('column', axis=1, inplace=True)
```

## Working with Large Data

```python
# Read in chunks
chunk_iter = pd.read_csv('large.csv', chunksize=10000)
for chunk in chunk_iter:
    process(chunk)

# Memory optimization
df = pd.read_csv('data.csv', dtype={'id': 'int32', 'value': 'float32'})
```

## Statistical Functions

```python
# Correlation
corr = df.corr()

# Covariance
cov = df.cov()

# Describe
stats = df.describe()

# Rolling statistics
df['ma_7'] = df['value'].rolling(window=7).mean()
df['std_7'] = df['value'].rolling(window=7).std()
```

## Visualization

```python
import matplotlib.pyplot as plt

# Histogram
df['value'].hist()

# Box plot
df.boxplot()

# Line plot
df.plot()

# Correlation heatmap
import seaborn as sns
sns.heatmap(df.corr(), annot=True)
```

## Example: Preprocessing ML Data

```python
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# Load data
df = pd.read_csv('data.csv')

# Handle missing values
df.fillna(df.mean(), inplace=True)

# Encode categorical
df = pd.get_dummies(df, columns=['category'])

# Normalize
scaler = StandardScaler()
numeric_cols = df.select_dtypes(include=[np.number]).columns
df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

# Save
df.to_csv('processed_data.csv', index=False)
```
