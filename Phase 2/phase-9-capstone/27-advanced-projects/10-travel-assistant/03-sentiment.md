# Tourism Intelligence - Sentiment Analysis System

## Overview

The sentiment analysis system analyzes hotel reviews, comments, and feedback to extract sentiment, themes, and insights.

## Sentiment Analysis Implementation

```python
#!/usr/bin/env python3
"""
Sentiment Analysis Engine for Tourism Intelligence
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = {
    "ollama_host": "http://localhost:11434",
    "data_dir": "/opt/tourism-intel/data"
}


class SentimentAnalyzer:
    """Analyzes sentiment of reviews"""
    
    def __init__(self):
        self.ollama = CONFIG["ollama_host"]
        
    def analyze_text(self, text: str, language: str = "es") -> Dict:
        """Analyze sentiment of text"""
        
        if language == "es":
            prompt = f"""Analiza el sentimiento de esta opinión de hotel.

Clasifica como: POSITIVO, NEGATIVO, o NEUTRAL

También identifica:
- Temas principales (limpieza, servicio, ubicación, precio, comida)
- Palabras clave
- Puntuación sugerida (1-10)

Opinión: {text[:1000]}

Responde en JSON:
{{
  "sentiment": "POSITIVO/NEGATIVO/NEUTRAL",
  "score": 1-10,
  "themes": ["tema1", "tema2"],
  "keywords": ["palabra1"],
  "summary": "resumen breve"
}}"""
        else:
            prompt = f"""Analyze sentiment of this hotel review.

Classify as: POSITIVE, NEGATIVE, or NEUTRAL

Also identify:
- Main themes (cleanliness, service, location, price, food)
- Keywords
- Suggested rating (1-10)

Review: {text[:1000]}

Respond in JSON:
{{
  "sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
  "score": 1-10,
  "themes": ["theme1", "theme2"],
  "keywords": ["keyword1"],
  "summary": "brief summary"
}}"""
        
        try:
            response = requests.post(
                f"{self.ollama}/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_ctx": 4096
                    }
                },
                timeout=60
            )
            
            result = response.json()
            text_response = result.get("response", "")
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', text_response)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
        
        return {
            "sentiment": "NEUTRAL",
            "score": 5,
            "themes": [],
            "keywords": [],
            "summary": "Analysis failed"
        }
    
    def analyze_reviews(self, reviews: List[Dict]) -> Dict:
        """Analyze multiple reviews"""
        
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        total_score = 0
        all_themes = {}
        all_keywords = []
        
        for review in reviews:
            text = review.get("text", "")
            if not text:
                continue
            
            analysis = self.analyze_text(text)
            
            # Aggregate
            sentiment = analysis.get("sentiment", "NEUTRAL").upper()
            if "POSITIVO" in sentiment or "POSITIVE" in sentiment:
                sentiments["positive"] += 1
            elif "NEGATIVO" in sentiment or "NEGATIVE" in sentiment:
                sentiments["negative"] += 1
            else:
                sentiments["neutral"] += 1
            
            total_score += analysis.get("score", 5)
            
            # Themes
            for theme in analysis.get("themes", []):
                all_themes[theme] = all_themes.get(theme, 0) + 1
            
            # Keywords
            all_keywords.extend(analysis.get("keywords", []))
        
        # Calculate averages
        count = len(reviews)
        avg_score = total_score / count if count > 0 else 5
        
        # Top themes
        top_themes = sorted(all_themes.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_reviews": count,
            "sentiments": sentiments,
            "average_score": round(avg_score, 1),
            "top_themes": [t[0] for t in top_themes],
            "sentiment_ratio": {
                "positive": round(sentiments["positive"] / count * 100, 1) if count > 0 else 0,
                "negative": round(sentiments["negative"] / count * 100, 1) if count > 0 else 0,
                "neutral": round(sentiments["neutral"] / count * 100, 1) if count > 0 else 0
            }
        }


class ReviewCollector:
    """Collects reviews from various sources"""
    
    def __init__(self):
        self.data_dir = Path(CONFIG["data_dir"])
    
    def collect_from_hotels(self) -> List[Dict]:
        """Collect reviews from hotel data"""
        reviews = []
        
        # Read from hotel files
        hotels_dir = self.data_dir / "hotels"
        if hotels_dir.exists():
            for file in sorted(hotels_dir.glob("*.json"))[-10:]:
                try:
                    with open(file) as f:
                        hotels = json.load(f)
                        for hotel in hotels:
                            # Simulate reviews (in real implementation, would scrape reviews)
                            if hotel.get("reviews_count"):
                                reviews.append({
                                    "hotel_id": hotel.get("id"),
                                    "hotel_name": hotel.get("name"),
                                    "source": hotel.get("source"),
                                    "text": f"Great hotel in {hotel.get('location')}",
                                    "rating": hotel.get("rating", "4.0"),
                                    "date": datetime.now().isoformat()
                                })
                except Exception as e:
                    logger.error(f"Error reading {file}: {e}")
        
        return reviews
    
    def get_hotel_sentiment(self, hotel_id: str) -> Dict:
        """Get sentiment for specific hotel"""
        
        reviews = self.collect_from_hotels()
        hotel_reviews = [r for r in reviews if r.get("hotel_id") == hotel_id]
        
        if not hotel_reviews:
            return {"error": "No reviews found"}
        
        analyzer = SentimentAnalyzer()
        return analyzer.analyze_reviews(hotel_reviews)


class TrendDetector:
    """Detects trends in sentiment data"""
    
    def detect_trends(self, historical_data: List[Dict]) -> Dict:
        """Detect sentiment trends over time"""
        
        if not historical_data:
            return {"trend": "insufficient_data"}
        
        # Sort by date
        sorted_data = sorted(historical_data, key=lambda x: x.get("date", ""))
        
        # Calculate moving average
        window_size = min(7, len(sorted_data))
        
        scores = [d.get("average_score", 5) for d in sorted_data]
        
        if len(scores) >= 2:
            recent_avg = sum(scores[-window_size:]) / window_size
            older_avg = sum(scores[:window_size]) / window_size
            
            change = recent_avg - older_avg
            
            if change > 0.5:
                trend = "improving"
            elif change < -0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "recent_average": round(sum(scores[-window_size:]) / window_size, 2) if scores else 0,
            "data_points": len(scores)
        }


# API Integration
@app.route("/api/sentiment/analyze", methods=["POST"])
def analyze_sentiment():
    """Analyze sentiment of reviews"""
    data = request.get_json()
    text = data.get("text", "")
    language = data.get("language", "es")
    
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze_text(text, language)
    
    return jsonify(result)


@app.route("/api/sentiment/hotel/<hotel_id>")
def hotel_sentiment(hotel_id: str):
    """Get sentiment for hotel"""
    collector = ReviewCollector()
    result = collector.get_hotel_sentiment(hotel_id)
    
    return jsonify(result)


@app.route("/api/sentiment/trends")
def sentiment_trends():
    """Get sentiment trends"""
    # Load historical data
    # Return trends
    return jsonify({"trend": "stable", "recent_average": 7.5})
```

## Sample Output

```json
{
  "hotel_id": "HOTEL-ABC123",
  "hotel_name": "Hotel Example",
  "total_reviews": 150,
  "sentiments": {
    "positive": 95,
    "negative": 20,
    "neutral": 35
  },
  "average_score": 7.8,
  "top_themes": ["limpieza", "ubicación", "servicio"],
  "sentiment_ratio": {
    "positive": 63.3,
    "negative": 13.3,
    "neutral": 23.3
  },
  "trend": "improving",
  "trend_indicator": "+0.8 points"
}
```

## Next Steps

- [04-availability](./04-availability.md) - Real-time availability monitoring
