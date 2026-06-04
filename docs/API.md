# API Documentation

## Base URL
`http://localhost:8000`

## Endpoints

### Health Check
`GET /health`

Returns service status.

### Vector Search
`POST /api/v1/search/airports`

Search airports by semantic similarity.

**Request:**
```json
{
  "query": "tropical islands",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 3316,
      "name": "Phuket International Airport",
      "city": "Phuket",
      "country": "Thailand",
      "iata_code": "HKT",
      "latitude": 8.1132,
      "longitude": 98.3169,
      "score": 0.156
    }
  ]
}
```

### Natural Language Query
`POST /api/v1/query/natural`

Convert natural language to SQL.

**Request:**
```json
{
  "question": "Which airports have most routes?"
}
```

### Analytics
`GET /api/v1/analytics/stats`

Get database statistics.
