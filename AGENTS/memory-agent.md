# Memory Agent

## Owns
- `core/memory/`

## Responsibilities
- Consuming clean events from `~/.kb/events/clean/`
- Chunking events into indexable units
- Embedding chunks via local model (Ollama)
- Writing embeddings to vector index at `~/.kb/index/`
- Building and maintaining knowledge graph at `~/.kb/graph/`
- Auto-classifying events into life buckets
- Detecting relationships between entities (concepts, hashed people, topics)

## Interfaces
- Receives: clean events from `~/.kb/events/clean/`
- Writes: vector index to `~/.kb/index/`
- Writes: graph edges to `~/.kb/graph/`
- Exposes: no HTTP endpoints (internal pipeline only)

## Must Never
- Consume raw events directly (always from clean/)
- Store unhashed names (trust what privacy-agent already sanitized)
- Call external LLM APIs directly — use `core/llm_service.py`
- Modify the hash map in `~/.kb/hashes/map.json`
- Delete or overwrite graph edges without versioning

## Required Tests
- Chunking produces consistent results for same input
- Embedding dimensions match configured model output
- Graph edge detection produces valid edge format
- Bucket classification returns valid bucket label
- Index is queryable after write

## Notes
Memory is append-heavy and read-rarely during writes. Optimize for write throughput and
retrieval accuracy, not for write latency. The graph is the long-term asset — treat it carefully.
