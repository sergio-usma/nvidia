# External Services Integration

## Table of Contents

1. [Weather APIs](#weather-apis)
2. [Database Integration](#database-integration)
3. [Messaging Services](#messaging-services)

## Weather APIs

```python
import requests

def get_weather(city: str) -> str:
    api_key = os.environ.get("WEATHER_API_KEY")
    response = requests.get(
        f"http://api.weatherapi.com/v1/current.json",
        params={"key": api_key, "q": city}
    )
    data = response.json()
    return f"Weather in {city}: {data['current']['temp_c']}°C"
```

## Database Integration

### PostgreSQL

```bash
pip install psycopg2-binary
```

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="mydb",
    user="user",
    password="pass"
)

def save_conversation(user_id: str, message: str, response: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (user_id, message, response) VALUES (%s, %s, %s)",
        (user_id, message, response)
    )
    conn.commit()
```

## Messaging Services

### Telegram Bot

```python
import requests

def send_telegram(message: str):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message}
    )
```

### Discord Webhook

```python
def send_discord(message: str):
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    requests.post(webhook_url, json={"content": message})
```

## Next Steps

- [Automation Patterns](./09-automation-patterns.md) - Advanced patterns
- [Monitoring](./10-monitoring.md) - System monitoring
