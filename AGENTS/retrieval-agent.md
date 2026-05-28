# Retrieval Agent

## Owns
- `core/retrieval/`

## Responsibilities
- Semantic search over the vector index
- Graph traversal for relationship queries
- Time-filtered retrieval (filter by date range, bucket, person-hash)
- Context assembly: selecting + ranking chunks for LLM input
- Assembling final chat context from multiple retrieval sources

## Interfaces
- Reads: vector index from `~/.kb/index/`
- Reads: graph from `~/.kb/graph/`
- Exposes: `/chat` endpoint (via `core/frontend_backend.py`)
- Calls: `core/llm_service.py` for final response generation

## Must Never
- Read from `~/.kb/events/raw/` (only clean or index)
- Expose raw embeddings over the API
- Call LLM APIs directly — always via `core/llm_service.py`
- Return responses that include unhashed names (reverse-render before returning)

## Required Tests
- Semantic search returns relevant results for test queries
- Time filtering works correctly
- Graph traversal does not produce cycles
- Context assembly stays within token budget
- Latency benchmark: p95 < 2s for standard queries (see `EVALS/retrieval/`)

## Notes
Retrieval quality directly determines chat quality. If chat feels bad, check retrieval first —
it's more likely a retrieval problem than an LLM problem. Log retrieval scores to help diagnose.
