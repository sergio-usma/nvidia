# RAG Evaluation Metrics

## Retrieval Metrics

### Precision@K

```python
def precision_at_k(retrieved, relevant, k):
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / k
```

### Recall@K

```python
def recall_at_k(retrieved, relevant, k):
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / len(relevant_set)
```

### Mean Average Precision (MAP)

```python
def average_precision(retrieved, relevant):
    score = 0
    num_hits = 0
    for i, doc in enumerate(retrieved):
        if doc in relevant:
            num_hits += 1
            score += num_hits / (i + 1)
    return score / len(relevant) if relevant else 0
```

## Generation Metrics

### Faithfulness

```python
def faithfulness(answer, context):
    """Check if answer is supported by context"""
    prompt = f"""Given this context:
{context}

Is this answer supported? Answer yes or no:
{answer}"""
    
    response = llm.invoke(prompt)
    return "yes" in response.content.lower()
```

### Answer Relevance

```python
def answer_relevance(question, answer):
    """Check if answer addresses question"""
    prompt = f"""Question: {question}
Answer: {answer}

Does the answer address the question? Score 0-1:"""
    
    response = llm.invoke(prompt)
    # Parse score
    return 0.8  # placeholder
```

## Evaluation Script

```python
class RAGEvaluator:
    def __init__(self, rag_system):
        self.rag = rag_system
    
    def evaluate(self, test_questions, ground_truth):
        results = []
        
        for q, expected in zip(test_questions, ground_truth):
            # Get answer
            result = self.rag.query(q, return_sources=True)
            
            # Calculate metrics
            metrics = {
                "question": q,
                "answer": result["answer"],
                "precision_at_3": precision_at_k(result["sources"], expected["sources"], 3),
                "faithfulness": faithfulness(result["answer"], result.get("context", "")),
            }
            results.append(metrics)
        
        return results
    
    def print_results(self, results):
        for r in results:
            print(f"Q: {r['question']}")
            print(f"  P@3: {r['precision_at_3']:.2f}")
            print(f"  Faithful: {r['faithfulness']}")
```

## Next Steps

- [Production](./12-production.md)
- [Troubleshooting](./13-troubleshooting.md)
