"""
Recommendation Engine Service
Provides personalized airport and route recommendations based on user preferences
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
from config import get_settings

settings = get_settings()
embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
    
    def recommend_similar_airports(self, airport_id: int, limit: int = 10) -> List[Dict]:
        """
        Find airports similar to the given airport based on:
        - Hub type
        - Price tier
        - Geographic proximity
        - Passenger volume
        """
        sql = """
        SELECT 
            a2.id, a2.name, a2.city, a2.country, a2.iata_code,
            a2.latitude, a2.longitude, a2.hub_type, a2.price_tier,
            a2.annual_passengers,
            (
                -- Similarity score based on multiple factors
                (CASE WHEN a1.hub_type = a2.hub_type THEN 30 ELSE 0 END) +
                (CASE WHEN a1.price_tier = a2.price_tier THEN 25 ELSE 0 END) +
                (CASE WHEN ABS(a1.annual_passengers - a2.annual_passengers) < 5000000 THEN 20 ELSE 0 END) +
                (45 - LEAST(45, ABS(a1.latitude - a2.latitude) + ABS(a1.longitude - a2.longitude)))
            ) AS similarity_score
        FROM airports a1
        JOIN airports a2 ON a1.id != a2.id
        WHERE a1.id = :airport_id
        ORDER BY similarity_score DESC
        LIMIT :limit
        """
        
        result = self.db.execute(text(sql), {'airport_id': airport_id, 'limit': limit})
        
        return [{
            'id': r[0], 'name': r[1], 'city': r[2], 'country': r[3],
            'iata_code': r[4], 'latitude': r[5], 'longitude': r[6],
            'hub_type': r[7], 'price_tier': r[8], 'annual_passengers': r[9],
            'similarity_score': float(r[10])
        } for r in result]
    
    def recommend_by_preferences(self, preferences: Dict, limit: int = 10) -> List[Dict]:
        """
        Recommend airports based on user preferences:
        - hub_type: 'major-hub', 'regional-hub', 'connector', 'small'
        - price_tier: 'budget-friendly', 'moderate', 'premium', 'luxury'
        - min_passengers: minimum annual passengers
        - region: specific country or region
        """
        conditions = ["1=1"]
        params = {'limit': limit}
        
        if preferences.get('hub_type'):
            conditions.append("hub_type = :hub_type")
            params['hub_type'] = preferences['hub_type']
        
        if preferences.get('price_tier'):
            conditions.append("price_tier = :price_tier")
            params['price_tier'] = preferences['price_tier']
        
        if preferences.get('min_passengers'):
            conditions.append("annual_passengers >= :min_passengers")
            params['min_passengers'] = preferences['min_passengers']
        
        if preferences.get('country'):
            conditions.append("country = :country")
            params['country'] = preferences['country']
        
        sql = f"""
        SELECT 
            id, name, city, country, iata_code, latitude, longitude,
            hub_type, price_tier, annual_passengers, facilities
        FROM airports
        WHERE {' AND '.join(conditions)}
        ORDER BY annual_passengers DESC
        LIMIT :limit
        """
        
        result = self.db.execute(text(sql), params)
        
        return [{
            'id': r[0], 'name': r[1], 'city': r[2], 'country': r[3],
            'iata_code': r[4], 'latitude': r[5], 'longitude': r[6],
            'hub_type': r[7], 'price_tier': r[8], 'annual_passengers': r[9],
            'facilities': r[10]
        } for r in result]
    
    def recommend_routes_from_airport(self, airport_id: int, preferences: Dict = None, limit: int = 10) -> List[Dict]:
        """
        Recommend routes from a specific airport based on:
        - Distance preferences
        - Destination characteristics
        - Route popularity (number of airlines)
        """
        price_filter = ""
        params = {'airport_id': airport_id, 'limit': limit}
        
        if preferences and preferences.get('price_tier'):
            price_filter = "AND dest.price_tier = :price_tier"
            params['price_tier'] = preferences['price_tier']
        
        sql = f"""
        SELECT 
            r.id, r.distance_km,
            src.name AS source_name, src.iata_code AS source_iata,
            dest.id AS dest_id, dest.name AS dest_name, dest.city AS dest_city,
            dest.country AS dest_country, dest.iata_code AS dest_iata,
            dest.latitude AS dest_lat, dest.longitude AS dest_lon,
            dest.hub_type, dest.price_tier, dest.facilities,
            COUNT(DISTINCT r.airline) AS num_airlines
        FROM routes r
        JOIN airports src ON r.source_airport_id = src.id
        JOIN airports dest ON r.dest_airport_id = dest.id
        WHERE r.source_airport_id = :airport_id
        {price_filter}
        GROUP BY r.dest_airport_id
        ORDER BY num_airlines DESC, dest.annual_passengers DESC
        LIMIT :limit
        """
        
        result = self.db.execute(text(sql), params)
        
        return [{
            'route_id': r[0], 'distance_km': float(r[1]),
            'source_name': r[2], 'source_iata': r[3],
            'dest_id': r[4], 'dest_name': r[5], 'dest_city': r[6],
            'dest_country': r[7], 'dest_iata': r[8],
            'dest_latitude': float(r[9]), 'dest_longitude': float(r[10]),
            'hub_type': r[11], 'price_tier': r[12], 'facilities': r[13],
            'num_airlines': r[14]
        } for r in result]
    
    def recommend_destinations_by_query(self, query: str, preferences: Dict = None, limit: int = 10) -> List[Dict]:
        """
        Enhanced semantic search with preference filtering
        Example: "budget-friendly hubs in Asia"
        """
        # Generate embedding for the query
        embedding_vector = embedding_model.encode(query, convert_to_numpy=True).tolist()
        embedding_str = str(embedding_vector)
        
        # Build preference filters
        conditions = ["embedding IS NOT NULL"]
        params = {'emb': embedding_str, 'limit': limit}
        
        if preferences:
            if preferences.get('price_tier'):
                conditions.append("price_tier = :price_tier")
                params['price_tier'] = preferences['price_tier']
            
            if preferences.get('hub_type'):
                conditions.append("hub_type = :hub_type")
                params['hub_type'] = preferences['hub_type']
        
        sql = f"""
        SELECT 
            id, name, city, country, iata_code, latitude, longitude,
            hub_type, price_tier, annual_passengers, facilities, description,
            VEC_DISTANCE_COSINE(embedding, VEC_FromText(:emb)) AS score
        FROM airports
        WHERE {' AND '.join(conditions)}
        ORDER BY score ASC
        LIMIT :limit
        """
        
        result = self.db.execute(text(sql), params)
        
        return [{
            'id': r[0], 'name': r[1], 'city': r[2], 'country': r[3],
            'iata_code': r[4], 'latitude': r[5], 'longitude': r[6],
            'hub_type': r[7], 'price_tier': r[8], 'annual_passengers': r[9],
            'facilities': r[10], 'description': r[11], 'score': float(r[12])
        } for r in result]
