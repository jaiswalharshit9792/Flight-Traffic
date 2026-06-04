from typing import List, Dict
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import text
from config import get_settings

settings = get_settings()
print("Loading embedding model...")
embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

class VectorSearchService:
    def __init__(self, db: Session):
        self.db = db

    def generate_embedding(self, text: str) -> List[float]:
        embedding = embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def search_similar_airports(self, query: str, limit: int = 10) -> List[Dict]:
        embedding = str(self.generate_embedding(query))

        sql = """SELECT id, name, city, country, iata_code, latitude, longitude,
                 VEC_DISTANCE_COSINE(embedding, VEC_FromText(:emb)) AS score
                 FROM airports WHERE embedding IS NOT NULL
                 ORDER BY score ASC LIMIT :limit"""

        result = self.db.execute(text(sql), {'emb': embedding, 'limit': limit})

        return [{'id': r[0], 'name': r[1], 'city': r[2], 'country': r[3],
                 'iata_code': r[4], 'latitude': r[5], 'longitude': r[6],
                 'score': float(r[7])} for r in result]
