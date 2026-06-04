"""
Path Optimization Service
Find optimal flight routes using Dijkstra's algorithm with MariaDB recursive CTEs
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import math

class PathOptimizerService:
    def __init__(self, db: Session):
        self.db = db
    
    def find_optimal_path(
        self, 
        source_iata: str, 
        dest_iata: str, 
        max_stops: int = 3,
        criteria: str = 'distance'
    ) -> Dict:
        """
        Find optimal path between two airports using recursive CTE (Dijkstra-like)
        
        Args:
            source_iata: Source airport IATA code (e.g., 'JFK')
            dest_iata: Destination airport IATA code (e.g., 'NRT')
            max_stops: Maximum number of stops allowed
            criteria: Optimization criteria ('distance', 'stops')
        
        Returns:
            Dict with path information, total distance, stops, and route details
        """
        
        # Get airport IDs from IATA codes
        source_id = self._get_airport_id(source_iata)
        dest_id = self._get_airport_id(dest_iata)
        
        if not source_id or not dest_id:
            return {
                'success': False, 
                'error': f'Invalid airport codes: {source_iata} or {dest_iata}'
            }
        
        # Recursive CTE for path finding
        sql = """
        WITH RECURSIVE route_paths AS (
            -- Base case: direct routes from source
            SELECT 
                r.source_airport_id,
                r.dest_airport_id,
                r.distance_km,
                r.airline,
                CAST(CONCAT(r.source_airport_id, '->', r.dest_airport_id) AS CHAR(1000)) AS path,
                CAST(r.source_airport_id AS CHAR(500)) AS airport_sequence,
                1 AS num_stops,
                r.distance_km AS total_distance
            FROM routes r
            WHERE r.source_airport_id = :source_id
            
            UNION ALL
            
            -- Recursive case: extend paths
            SELECT 
                rp.source_airport_id,
                r.dest_airport_id,
                r.distance_km,
                r.airline,
                CAST(CONCAT(rp.path, '->', r.dest_airport_id) AS CHAR(1000)) AS path,
                CAST(CONCAT(rp.airport_sequence, ',', r.dest_airport_id) AS CHAR(500)) AS airport_sequence,
                rp.num_stops + 1,
                rp.total_distance + r.distance_km AS total_distance
            FROM route_paths rp
            JOIN routes r ON rp.dest_airport_id = r.source_airport_id
            WHERE rp.num_stops < :max_stops
                AND FIND_IN_SET(r.dest_airport_id, rp.airport_sequence) = 0  -- Avoid cycles
                AND rp.dest_airport_id != :dest_id  -- Stop when we reach destination
        )
        SELECT 
            path,
            airport_sequence,
            num_stops,
            total_distance,
            airline
        FROM route_paths
        WHERE dest_airport_id = :dest_id
        ORDER BY 
            CASE 
                WHEN :criteria = 'distance' THEN total_distance
                WHEN :criteria = 'stops' THEN num_stops * 10000  -- Prioritize fewer stops
                ELSE total_distance
            END ASC
        LIMIT 5
        """
        
        result = self.db.execute(text(sql), {
            'source_id': source_id,
            'dest_id': dest_id,
            'max_stops': max_stops,
            'criteria': criteria
        })
        
        paths = []
        for row in result:
            airport_ids = [int(x) for x in row[1].split(',')]
            airport_ids.append(dest_id)  # Add final destination
            
            # Get airport details for the path
            route_details = self._get_route_details(airport_ids)
            
            paths.append({
                'path': row[0],
                'stops': row[2],
                'total_distance_km': float(row[3]),
                'estimated_time_hours': round(float(row[3]) / 800, 1),  # Avg speed ~800 km/h
                'route_details': route_details
            })
        
        if not paths:
            return {
                'success': False,
                'error': f'No route found between {source_iata} and {dest_iata} within {max_stops} stops'
            }
        
        return {
            'success': True,
            'source': source_iata,
            'destination': dest_iata,
            'optimal_path': paths[0],
            'alternative_paths': paths[1:] if len(paths) > 1 else []
        }
    
    def find_multi_criteria_paths(
        self,
        source_iata: str,
        dest_iata: str,
        max_stops: int = 3
    ) -> Dict:
        """
        Find multiple paths optimized for different criteria and score them
        """
        source_id = self._get_airport_id(source_iata)
        dest_id = self._get_airport_id(dest_iata)
        
        if not source_id or not dest_id:
            return {'success': False, 'error': 'Invalid airport codes'}
        
        # Get paths optimized for distance
        distance_paths = self.find_optimal_path(source_iata, dest_iata, max_stops, 'distance')
        
        # Get paths optimized for fewer stops
        stops_paths = self.find_optimal_path(source_iata, dest_iata, max_stops, 'stops')
        
        # Combine and score
        all_paths = []
        seen_paths = set()
        
        for result in [distance_paths, stops_paths]:
            if result.get('success'):
                for path in [result['optimal_path']] + result.get('alternative_paths', []):
                    path_key = path['path']
                    if path_key not in seen_paths:
                        seen_paths.add(path_key)
                        
                        # Multi-criteria score (lower is better)
                        score = (
                            path['total_distance_km'] / 1000 +  # Normalize distance
                            path['stops'] * 2000 +  # Penalize stops heavily
                            path['estimated_time_hours'] * 500  # Consider time
                        )
                        
                        path['score'] = round(score, 2)
                        all_paths.append(path)
        
        # Sort by score
        all_paths.sort(key=lambda x: x['score'])
        
        return {
            'success': True,
            'source': source_iata,
            'destination': dest_iata,
            'recommended_path': all_paths[0] if all_paths else None,
            'all_paths': all_paths
        }
    
    def _get_airport_id(self, iata_code: str) -> Optional[int]:
        """Get airport ID from IATA code"""
        result = self.db.execute(
            text("SELECT id FROM airports WHERE iata_code = :iata LIMIT 1"),
            {'iata': iata_code.upper()}
        ).fetchone()
        return result[0] if result else None
    
    def _get_route_details(self, airport_ids: List[int]) -> List[Dict]:
        """Get detailed information for each leg of the route"""
        if len(airport_ids) < 2:
            return []
        
        details = []
        for i in range(len(airport_ids) - 1):
            source_id = airport_ids[i]
            dest_id = airport_ids[i + 1]
            
            sql = """
            SELECT 
                src.name AS source_name,
                src.iata_code AS source_iata,
                src.city AS source_city,
                src.country AS source_country,
                dest.name AS dest_name,
                dest.iata_code AS dest_iata,
                dest.city AS dest_city,
                dest.country AS dest_country,
                r.distance_km,
                r.airline
            FROM routes r
            JOIN airports src ON r.source_airport_id = src.id
            JOIN airports dest ON r.dest_airport_id = dest.id
            WHERE r.source_airport_id = :source_id 
                AND r.dest_airport_id = :dest_id
            LIMIT 1
            """
            
            result = self.db.execute(text(sql), {
                'source_id': source_id,
                'dest_id': dest_id
            }).fetchone()
            
            if result:
                details.append({
                    'leg': i + 1,
                    'from': {
                        'name': result[0],
                        'iata': result[1],
                        'city': result[2],
                        'country': result[3]
                    },
                    'to': {
                        'name': result[4],
                        'iata': result[5],
                        'city': result[6],
                        'country': result[7]
                    },
                    'distance_km': float(result[8]),
                    'airline': result[9]
                })
        
        return details
    
    def get_connectivity_score(self, airport_iata: str) -> Dict:
        """
        Calculate connectivity score for an airport based on:
        - Number of direct routes
        - Number of reachable airports within 2 stops
        - Hub type
        """
        airport_id = self._get_airport_id(airport_iata)
        if not airport_id:
            return {'success': False, 'error': 'Invalid airport code'}
        
        # Direct connections
        direct_sql = """
        SELECT COUNT(DISTINCT dest_airport_id) as direct_destinations
        FROM routes
        WHERE source_airport_id = :airport_id
        """
        
        direct = self.db.execute(text(direct_sql), {'airport_id': airport_id}).fetchone()
        direct_count = direct[0] if direct else 0
        
        # Two-hop reachability
        twohop_sql = """
        SELECT COUNT(DISTINCT r2.dest_airport_id) as reachable
        FROM routes r1
        JOIN routes r2 ON r1.dest_airport_id = r2.source_airport_id
        WHERE r1.source_airport_id = :airport_id
            AND r2.dest_airport_id != :airport_id
        """
        
        twohop = self.db.execute(text(twohop_sql), {'airport_id': airport_id}).fetchone()
        twohop_count = twohop[0] if twohop else 0
        
        # Calculate score (0-100)
        connectivity_score = min(100, (direct_count * 2) + (twohop_count * 0.1))
        
        return {
            'success': True,
            'airport': airport_iata,
            'direct_destinations': direct_count,
            'two_hop_reachable': twohop_count,
            'connectivity_score': round(connectivity_score, 2)
        }
