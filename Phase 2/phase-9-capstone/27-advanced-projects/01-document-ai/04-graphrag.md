# GraphRAG Implementation

Build a knowledge graph from your files for enhanced semantic search and relationship discovery.

## Knowledge Graph Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                      Knowledge Graph                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌─────────┐         ┌─────────┐         ┌─────────┐        │
│    │ File A  │────────▶│ Topic 1 │◀────────│ File B  │        │
│    └─────────┘         └─────────┘         └─────────┘        │
│         │                   │                   │               │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│    ┌─────────┐         ┌─────────┐         ┌─────────┐        │
│    │ Concept │────────▶│ Topic 2 │◀────────│ Concept │        │
│    └─────────┘         └─────────┘         └─────────┘        │
│                                                                  │
│    Nodes: Files, Topics, Concepts, Entities                      │
│    Edges: Contains, Related_to, Mentions, Similar_to            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## GraphRAG Implementation

```python
# graphrag/knowledge_graph.py
import logging
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import json
import networkx as nx

logger = logging.getLogger(__name__)

class KnowledgeGraph:
    """Build and query a knowledge graph from files"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.graph = nx.MultiDiGraph()
        self.entity_types = ['file', 'topic', 'concept', 'entity', 'person', 'organization']
        
    def build_from_files(self, files: List[Dict], ollama_client) -> nx.MultiDiGraph:
        """Build knowledge graph from scanned files"""
        logger.info(f"Building knowledge graph from {len(files)} files")
        
        # Add file nodes
        for file_data in files:
            self._add_file_node(file_data)
        
        # Extract entities and relationships
        for i, file_data in enumerate(files):
            if file_data.get('content'):
                entities = self._extract_entities(file_data['content'], ollama_client)
                self._add_file_entities(file_data['path'], entities)
                
            if (i + 1) % 10 == 0:
                logger.info(f"  Processed {i + 1}/{len(files)} files")
        
        logger.info(f"Graph built with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
        return self.graph
    
    def _add_file_node(self, file_data: Dict):
        """Add a file node to the graph"""
        self.graph.add_node(
            file_data['path'],
            type='file',
            name=file_data.get('name', ''),
            size=file_data.get('size', 0),
            extension=file_data.get('extension', ''),
            modified=file_data.get('modified', '')
        )
    
    def _extract_entities(self, content: str, ollama_client) -> Dict:
        """Extract entities and topics from content using LLM"""
        # Truncate content
        content_sample = content[:3000]
        
        prompt = f"""Extract key entities and topics from the following text.
Return a JSON object with:
- "topics": List of main topics (max 10)
- "concepts": List of key concepts (max 15)
- "entities": List of named entities like people, organizations (max 10)

Text:
{content_sample}

Return ONLY valid JSON, no other text:"""

        try:
            response = ollama_client.chat(
                model=self.config.get('ollama_model', 'qwen2.5-coder'),
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3}
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', response['message']['content'])
            
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
        
        return {'topics': [], 'concepts': [], 'entities': []}
    
    def _add_file_entities(self, file_path: str, entities: Dict):
        """Add entity nodes and relationships"""
        # Add topic nodes
        for topic in entities.get('topics', []):
            topic_id = f"topic_{topic.lower().replace(' ', '_')}"
            
            if not self.graph.has_node(topic_id):
                self.graph.add_node(topic_id, type='topic', name=topic)
            
            self.graph.add_edge(file_path, topic_id, relation='has_topic')
            self.graph.add_edge(topic_id, file_path, relation='found_in')
        
        # Add concept nodes
        for concept in entities.get('concepts', []):
            concept_id = f"concept_{concept.lower().replace(' ', '_')}"
            
            if not self.graph.has_node(concept_id):
                self.graph.add_node(concept_id, type='concept', name=concept)
            
            self.graph.add_edge(file_path, concept_id, relation='has_concept')
            self.graph.add_edge(concept_id, file_path, relation='described_in')
        
        # Add entity nodes
        for entity in entities.get('entities', []):
            entity_id = f"entity_{entity.lower().replace(' ', '_')}"
            
            if not self.graph.has_node(entity_id):
                self.graph.add_node(entity_id, type='entity', name=entity)
            
            self.graph.add_edge(file_path, entity_id, relation='mentions')
            self.graph.add_edge(entity_id, file_path, relation='mentioned_in')
    
    def find_related_files(self, file_path: str, max_distance: int = 3) -> List[Dict]:
        """Find files related to a given file"""
        if not self.graph.has_node(file_path):
            return []
        
        related = []
        
        # Get nodes within max_distance
        for node in self.graph.nodes():
            if node == file_path:
                continue
            
            try:
                # Check if there's a path
                if nx.has_path(self.graph, file_path, node):
                    path_length = nx.shortest_path_length(self.graph, file_path, node)
                    
                    if path_length <= max_distance:
                        node_data = self.graph.nodes[node]
                        related.append({
                            'path': node,
                            'type': node_data.get('type', 'unknown'),
                            'name': node_data.get('name', ''),
                            'distance': path_length,
                            'relation': self._get_relation(file_path, node)
                        })
            except nx.NetworkXNoPath:
                continue
        
        return sorted(related, key=lambda x: x['distance'])
    
    def _get_relation(self, source: str, target: str) -> str:
        """Get the primary relation between two nodes"""
        try:
            edges = self.graph.get_edge_data(source, target)
            if edges:
                return list(edges.values())[0].get('relation', 'related')
            
            edges = self.graph.get_edge_data(target, source)
            if edges:
                return list(edges.values())[0].get('relation', 'related')
        except:
            pass
        
        return 'related'
    
    def get_topics_for_file(self, file_path: str) -> List[str]:
        """Get topics associated with a file"""
        topics = []
        
        for neighbor in self.graph.neighbors(file_path):
            node_data = self.graph.nodes[neighbor]
            if node_data.get('type') == 'topic':
                topics.append(node_data.get('name', ''))
        
        return topics
    
    def find_files_by_topic(self, topic: str) -> List[Dict]:
        """Find all files related to a topic"""
        topic_id = f"topic_{topic.lower().replace(' ', '_')}"
        
        if not self.graph.has_node(topic_id):
            return []
        
        files = []
        for neighbor in self.graph.neighbors(topic_id):
            node_data = self.graph.nodes[neighbor]
            if node_data.get('type') == 'file':
                files.append({
                    'path': neighbor,
                    'name': node_data.get('name', ''),
                    'size': node_data.get('size', 0)
                })
        
        return files
    
    def build_concept_map(self, file_path: str) -> Dict:
        """Build a concept map for a file"""
        if not self.graph.has_node(file_path):
            return {}
        
        concepts = []
        
        # Get direct concepts
        for neighbor in self.graph.neighbors(file_path):
            node_data = self.graph.nodes[neighbor]
            if node_data.get('type') == 'concept':
                concepts.append({
                    'name': node_data.get('name', ''),
                    'direct': True
                })
                
                # Get related concepts
                for related in self.graph.neighbors(neighbor):
                    if related != file_path:
                        related_data = self.graph.nodes[related]
                        if related_data.get('type') == 'concept':
                            concepts.append({
                                'name': related_data.get('name', ''),
                                'direct': False
                            })
        
        return {
            'file': file_path,
            'concepts': concepts[:20]  # Limit to top 20
        }
    
    def save_graph(self, filepath: str):
        """Save graph to file"""
        # Convert to serializable format
        graph_data = {
            'nodes': [
                {
                    'id': node,
                    **data
                }
                for node, data in self.graph.nodes(data=True)
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    **data
                }
                for u, v, data in self.graph.edges(data=True)
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        logger.info(f"Graph saved to {filepath}")
    
    def load_graph(self, filepath: str):
        """Load graph from file"""
        with open(filepath, 'r') as f:
            graph_data = json.load(f)
        
        self.graph = nx.MultiDiGraph()
        
        for node in graph_data['nodes']:
            node_id = node.pop('id')
            self.graph.add_node(node_id, **node)
        
        for edge in graph_data['edges']:
            source = edge.pop('source')
            target = edge.pop('target')
            self.graph.add_edge(source, target, **edge)
        
        logger.info(f"Graph loaded from {filepath}")
```

## GraphRAG Query

```python
# graphrag/query_engine.py
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GraphRAGQuery:
    """Query the knowledge graph with RAG"""
    
    def __init__(self, knowledge_graph: 'KnowledgeGraph', vector_store, ollama_client):
        self.graph = knowledge_graph
        self.vector_store = vector_store
        self.ollama = ollama_client
    
    def query(self, query_text: str, top_k: int = 5) -> Dict:
        """Query the knowledge graph"""
        
        # Get vector similar files
        # (Assume vector_store has similarity_search method)
        vector_results = self._semantic_search(query_text, top_k * 2)
        
        # Get graph-based results
        graph_results = self._graph_search(query_text, top_k)
        
        # Combine and rank results
        combined = self._combine_results(vector_results, graph_results)
        
        # Generate answer using LLM
        answer = self._generate_answer(query_text, combined)
        
        return {
            'answer': answer,
            'sources': combined[:top_k],
            'graph_context': graph_results[:3]
        }
    
    def _semantic_search(self, query: str, top_k: int) -> List[Dict]:
        """Semantic search using vector store"""
        # Generate embedding for query
        from rag.embedding_engine import EmbeddingEngine
        # This would use the actual embedding generation
        return []
    
    def _graph_search(self, query: str, top_k: int) -> List[Dict]:
        """Search using knowledge graph"""
        results = []
        
        # Find topics related to query
        query_lower = query.lower()
        
        for node, data in self.graph.graph.nodes(data=True):
            if data.get('type') == 'topic':
                topic_name = data.get('name', '').lower()
                if topic_name in query_lower or any(word in topic_name for word in query.split()):
                    files = self.graph.find_files_by_topic(data.get('name', ''))
                    results.extend(files)
        
        return results[:top_k]
    
    def _combine_results(self, vector_results: List[Dict], graph_results: List[Dict]) -> List[Dict]:
        """Combine vector and graph results"""
        seen = set()
        combined = []
        
        # Prioritize graph results
        for result in graph_results:
            if result.get('path') not in seen:
                seen.add(result['path'])
                result['rank'] = 'graph'
                combined.append(result)
        
        for result in vector_results:
            if result.get('path') not in seen:
                seen.add(result['path'])
                result['rank'] = 'vector'
                combined.append(result)
        
        return combined
    
    def _generate_answer(self, query: str, sources: List[Dict]) -> str:
        """Generate answer using LLM"""
        
        # Prepare context from sources
        context_parts = []
        for source in sources[:5]:
            path = source.get('path', '')
            name = source.get('name', '')
            context_parts.append(f"File: {name}\nPath: {path}")
        
        context = '\n\n'.join(context_parts)
        
        prompt = f"""Based on the following files from the knowledge base, answer the question.

Context:
{context}

Question: {query}

Provide a comprehensive answer based on the available information:"""

        try:
            response = self.ollama.chat(
                model='qwen2.5-coder',
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7}
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "Unable to generate answer at this time."
```

## Usage

```python
# Build graph from scanned files
from graphrag.knowledge_graph import KnowledgeGraph
import ollama

# Initialize
kg = KnowledgeGraph(config)
client = ollama.Client('http://localhost:11434')

# Build from files
with open('data/scan_results.json') as f:
    files = json.load(f)

kg.build_from_files(files, client)

# Save graph
kg.save_graph('data/knowledge_graph.json')

# Query
query_engine = GraphRAGQuery(kg, vector_store, client)
result = query_engine.query("What files are about machine learning?")
print(result['answer'])
```

## Next Steps

- [Usage & Commands](./05-usage-commands.md) - Full command reference
- [Yacht Jobs Overview](./06-yacht-jobs-overview.md) - Next project
