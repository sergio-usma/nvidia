# Common AI/ML Libraries

This guide covers essential AI/ML libraries for Jetson AGX Orin with JetPack 6.2.2.

## Scikit-learn

Install:

```bash
pip install scikit-learn
```

Usage:

```python
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
```

## Transformers (Hugging Face)

Install:

```bash
pip install transformers torch
```

Usage:

```python
from transformers import pipeline

# Text generation
generator = pipeline('text-generation', model='gpt2')
result = generator("Once upon a time")

# Sentiment analysis
analyzer = pipeline('sentiment-analysis')
result = analyzer("I love this product!")

# Question answering
qa = pipeline('question-answering')
result = qa(question="What is AI?", context="AI is artificial intelligence")
```

## Pillow (Image Processing)

Install:

```bash
pip install Pillow
```

Usage:

```python
from PIL import Image, ImageFilter, ImageEnhance

# Open image
img = Image.open('photo.jpg')

# Resize
img = img.resize((800, 600))

# Rotate
img = img.rotate(45)

# Blur
img = img.filter(ImageFilter.GaussianBlur(radius=5))

# Brightness
enhancer = ImageEnhance.Brightness(img)
img = enhancer.enhance(1.5)
```

## Matplotlib

Install:

```bash
pip install matplotlib
```

Usage:

```python
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.plot(x, y)
plt.xlabel('X axis')
plt.ylabel('Y axis')
plt.title('Sine Wave')
plt.show()

# Save
plt.savefig('plot.png')
```

## Seaborn

Install:

```bash
pip install seaborn
```

Usage:

```python
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv('data.csv')

# Heatmap
sns.heatmap(df.corr(), annot=True)

# Distribution
sns.histplot(df['column'])

# Pair plot
sns.pairplot(df)
```

## Requests (HTTP)

Install:

```bash
pip install requests
```

Usage:

```python
import requests

# GET request
response = requests.get('https://api.example.com/data')
data = response.json()

# POST request
response = requests.post(
    'https://api.example.com/predict',
    json={'input': [1, 2, 3]}
)
result = response.json()
```

## Pydantic (Data Validation)

Install:

```bash
pip install pydantic
```

Usage:

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
    email: str

user = User(name="John", age=30, email="john@example.com")
```

## FastAPI (Web Framework)

Install:

```bash
pip install fastapi uvicorn
```

Usage:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello"}

@app.post("/predict")
def predict(data: dict):
    return {"result": data}
```

Run: `uvicorn app:app --host 0.0.0.0 --port 8000`

## Flask (Web Framework)

Install:

```bash
pip install flask
```

Usage:

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello"

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_json()
    return jsonify({"result": predict_model(data)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## LangChain

Install:

```bash
pip install langchain
```

Usage:

```python
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

llm = Ollama(model="llama2")

prompt = PromptTemplate(
    input_variables=["question"],
    template="Answer: {question}"
)

chain = LLMChain(llm=llm, prompt=prompt)
result = chain.run("What is Python?")
```

## Tqdm (Progress Bars)

Install:

```bash
pip install tqdm
```

Usage:

```python
from tqdm import tqdm
import time

for i in tqdm(range(100), desc="Processing"):
    time.sleep(0.1)
```

## Logging

Usage:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting process")
logger.warning("Warning message")
logger.error("Error occurred")
```

## Python-dotenv

Install:

```bash
pip install python-dotenv
```

Usage:

```python
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("API_KEY")
```

## Schedule

Install:

```bash
pip install schedule
```

Usage:

```python
import schedule
import time

def job():
    print("Running scheduled task")

schedule.every().day.at("10:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Summary Installation Script

```bash
pip install \
    scikit-learn \
    transformers \
    torch \
    Pillow \
    matplotlib \
    seaborn \
    requests \
    pydantic \
    fastapi \
    uvicorn \
    flask \
    langchain \
    tqdm \
    python-dotenv \
    schedule \
    pandas \
    numpy
```

## Troubleshooting Imports

If packages don't import after install:

```bash
# Check installation location
pip show package_name

# Reinstall
pip install --force-reinstall package

# Verify Python path
python3 -c "import sys; print(sys.path)"
```
