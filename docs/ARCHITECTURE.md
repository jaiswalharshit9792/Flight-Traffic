# Architecture Documentation

## System Overview

FlightIQ uses a microservices architecture with 6 Docker containers:

1. **MariaDB 11.8**: Vector Search + ColumnStore
2. **Ollama**: Local LLM for NL-to-SQL
3. **Backend**: FastAPI REST API
4. **Frontend**: Streamlit dashboard
5. **Prometheus**: Metrics collection
6. **Grafana**: Visualization

## Data Flow

1. User enters query → Streamlit
2. HTTP POST → FastAPI
3. Generate embedding → Sentence Transformers
4. Vector search → MariaDB
5. Results → JSON → Frontend

## Design Decisions

**Why self-hosted AI?**
- 10x faster than API calls
- Zero cost
- Privacy-first
- No rate limits

**Why ColumnStore?**
- 50x faster for analytics
- Window functions built-in
- Horizontal scaling ready
