from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, Dict
from database import get_db
from services.vector_search import VectorSearchService
from services.ollama_service import OllamaService
from services.analytics import AnalyticsService
from services.recommender import RecommendationService
from services.path_optimizer import PathOptimizerService

app = FastAPI(title="FlightIQ ULTIMATE", version="2.0.0-ultimate")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

ollama = OllamaService()

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    preferences: Optional[Dict] = None

@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.0.0-ultimate", "features": ["semantic-search", "recommendations", "path-optimization", "analytics"]}

@app.post("/api/v1/search/airports")
def search(req: SearchRequest, db: Session = Depends(get_db)):
    try:
        if req.preferences:
            # Enhanced semantic search with preferences
            return {"results": RecommendationService(db).recommend_destinations_by_query(req.query, req.preferences, req.limit)}
        else:
            # Standard vector search
            return {"results": VectorSearchService(db).search_similar_airports(req.query, req.limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/query/natural")
def nl_query(req: dict, db: Session = Depends(get_db)):
    question = req.get("question", "")
    result = ollama.text_to_sql(question)

    if result["success"]:
        try:
            query_result = db.execute(text(result["sql"])).fetchall()
            return {"success": True, "sql": result["sql"], "result": [list(row) for row in query_result]}
        except Exception as e:
            return {"success": False, "sql": result["sql"], "error": str(e)}
    return result

@app.get("/api/v1/analytics/stats")
def analytics(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_stats()

# ==================== RECOMMENDATION ENDPOINTS ====================

@app.get("/api/v1/recommend/similar-airports/{airport_id}")
def recommend_similar(airport_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Find airports similar to the given airport"""
    try:
        return {"results": RecommendationService(db).recommend_similar_airports(airport_id, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/recommend/by-preferences")
def recommend_by_prefs(req: dict, db: Session = Depends(get_db)):
    """Recommend airports based on user preferences"""
    try:
        preferences = req.get("preferences", {})
        limit = req.get("limit", 10)
        return {"results": RecommendationService(db).recommend_by_preferences(preferences, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/recommend/routes-from/{airport_id}")
def recommend_routes(airport_id: int, price_tier: Optional[str] = None, limit: int = 10, db: Session = Depends(get_db)):
    """Recommend routes from a specific airport"""
    try:
        preferences = {"price_tier": price_tier} if price_tier else {}
        return {"results": RecommendationService(db).recommend_routes_from_airport(airport_id, preferences, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PATH OPTIMIZATION ENDPOINTS ====================

@app.get("/api/v1/optimize/route")
def optimize_route(
    source: str, 
    dest: str, 
    max_stops: int = 3, 
    criteria: str = "distance",
    db: Session = Depends(get_db)
):
    """Find optimal route between two airports"""
    try:
        return PathOptimizerService(db).find_optimal_path(source, dest, max_stops, criteria)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/optimize/multi-criteria")
def multi_criteria_route(
    source: str,
    dest: str,
    max_stops: int = 3,
    db: Session = Depends(get_db)
):
    """Find routes optimized for multiple criteria"""
    try:
        return PathOptimizerService(db).find_multi_criteria_paths(source, dest, max_stops)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/optimize/connectivity/{airport_iata}")
def airport_connectivity(airport_iata: str, db: Session = Depends(get_db)):
    """Get connectivity score for an airport"""
    try:
        return PathOptimizerService(db).get_connectivity_score(airport_iata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== ADVANCED ANALYTICS ENDPOINTS ====================

@app.get("/api/v1/analytics/busiest-routes")
def busiest_routes(limit: int = 10, db: Session = Depends(get_db)):
    """Get the busiest routes by number of airlines"""
    try:
        sql = """
        SELECT 
            src.name AS source_name, src.iata_code AS source_iata,
            dest.name AS dest_name, dest.iata_code AS dest_iata,
            AVG(r.distance_km) AS avg_distance,
            COUNT(DISTINCT r.airline) AS num_airlines
        FROM routes r
        JOIN airports src ON r.source_airport_id = src.id
        JOIN airports dest ON r.dest_airport_id = dest.id
        GROUP BY r.source_airport_id, r.dest_airport_id
        ORDER BY num_airlines DESC
        LIMIT :limit
        """
        result = db.execute(text(sql), {'limit': limit})
        return {"results": [{
            'source_name': r[0], 'source_iata': r[1],
            'dest_name': r[2], 'dest_iata': r[3],
            'avg_distance_km': float(r[4]),
            'num_airlines': r[5]
        } for r in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/hub-airports")
def hub_airports(hub_type: Optional[str] = None, limit: int = 20, db: Session = Depends(get_db)):
    """Get hub airports with their statistics"""
    try:
        where_clause = "WHERE hub_type = :hub_type" if hub_type else ""
        params: Dict = {'limit': limit}
        if hub_type:
            params['hub_type'] = hub_type
            
        sql = f"""
        SELECT 
            a.name, a.iata_code, a.city, a.country,
            a.hub_type, a.price_tier, a.annual_passengers,
            COUNT(DISTINCT r.dest_airport_id) AS num_destinations
        FROM airports a
        LEFT JOIN routes r ON a.id = r.source_airport_id
        {where_clause}
        GROUP BY a.id
        ORDER BY a.annual_passengers DESC
        LIMIT :limit
        """
        result = db.execute(text(sql), params)
        return {"results": [{
            'name': r[0], 'iata_code': r[1], 'city': r[2], 'country': r[3],
            'hub_type': r[4], 'price_tier': r[5], 'annual_passengers': r[6],
            'num_destinations': r[7]
        } for r in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/analytics/network-stats")
def network_stats(db: Session = Depends(get_db)):
    """Get comprehensive network statistics"""
    try:
        sql = """
        SELECT 
            COUNT(DISTINCT a.id) AS total_airports,
            COUNT(DISTINCT r.id) AS total_routes,
            COUNT(DISTINCT r.airline) AS total_airlines,
            AVG(r.distance_km) AS avg_route_distance,
            MAX(r.distance_km) AS max_route_distance,
            MIN(r.distance_km) AS min_route_distance,
            (SELECT COUNT(*) FROM airports WHERE hub_type = 'major-hub') AS major_hubs,
            (SELECT COUNT(*) FROM airports WHERE price_tier = 'budget-friendly') AS budget_airports
        FROM airports a
        LEFT JOIN routes r ON a.id = r.source_airport_id OR a.id = r.dest_airport_id
        """
        result = db.execute(text(sql)).fetchone()
        if not result:
            return {}
        return {
            'total_airports': result[0] or 0,
            'total_routes': result[1] or 0,
            'total_airlines': result[2] or 0,
            'avg_route_distance_km': round(float(result[3] or 0), 2),
            'max_route_distance_km': float(result[4] or 0),
            'min_route_distance_km': float(result[5] or 0),
            'major_hubs': result[6] or 0,
            'budget_friendly_airports': result[7] or 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
