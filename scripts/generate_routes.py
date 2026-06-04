import sys
sys.path.append('/app')
from sqlalchemy import create_engine, text
from config import get_settings
import random
import math

engine = create_engine(get_settings().DATABASE_URL)

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two points"""
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

print("Fetching major airports...")
with engine.connect() as conn:
    # Get major airports (those with IATA codes)
    result = conn.execute(text(
        "SELECT id, name, city, country, latitude, longitude, iata_code "
        "FROM airports "
        "WHERE iata_code IS NOT NULL "
        "ORDER BY RAND() "
        "LIMIT 500"
    ))
    airports = [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in result]

print(f"Selected {len(airports)} airports")
print("Generating realistic routes...")

airlines = ['AA', 'UA', 'DL', 'BA', 'LH', 'AF', 'KL', 'EK', 'QR', 'SQ', 
            'CX', 'TG', 'NH', 'JL', 'AC', 'QF', 'NZ', 'VS', 'IB', 'AZ']

routes = []
route_set = set()  # Avoid duplicates

# Generate routes between airports
for i, (src_id, src_name, src_city, src_country, src_lat, src_lon, src_iata) in enumerate(airports):
    # Each airport connects to 5-20 other airports
    num_connections = random.randint(5, 20)
    
    # Prefer connections to nearby airports and major hubs
    potential_destinations = random.sample(airports, min(50, len(airports)))
    
    connections = 0
    for dst_id, dst_name, dst_city, dst_country, dst_lat, dst_lon, dst_iata in potential_destinations:
        if src_id == dst_id:
            continue
            
        # Skip if route already exists
        route_key = (min(src_id, dst_id), max(src_id, dst_id))
        if route_key in route_set:
            continue
            
        # Calculate distance
        distance = haversine(src_lat, src_lon, dst_lat, dst_lon)
        
        # Only create routes for reasonable distances (100km - 15000km)
        if 100 < distance < 15000:
            airline = random.choice(airlines)
            routes.append((airline, src_id, dst_id, round(distance, 2)))
            route_set.add(route_key)
            connections += 1
            
            if connections >= num_connections:
                break
    
    if (i + 1) % 50 == 0:
        print(f"  Generated routes for {i+1}/{len(airports)} airports...")

print(f"\nGenerated {len(routes)} unique routes")
print("Importing into database...")

batch_size = 1000
with engine.connect() as conn:
    for i in range(0, len(routes), batch_size):
        batch = routes[i:i+batch_size]
        
        for airline, src, dst, distance in batch:
            conn.execute(text(
                "INSERT INTO routes (airline, source_airport_id, dest_airport_id, distance_km) "
                "VALUES (:airline, :src, :dst, :distance)"
            ), {
                "airline": airline,
                "src": src,
                "dst": dst,
                "distance": distance
            })
        
        conn.commit()
        print(f"  ✓ {min(i+batch_size, len(routes))}/{len(routes)} routes ({(i+batch_size)/len(routes)*100:.1f}%)")

print(f"✅ Import complete! {len(routes)} routes imported.")

# Show some statistics
with engine.connect() as conn:
    stats = conn.execute(text("""
        SELECT 
            COUNT(*) as total_routes,
            COUNT(DISTINCT source_airport_id) as source_airports,
            COUNT(DISTINCT dest_airport_id) as dest_airports,
            AVG(distance_km) as avg_distance,
            MAX(distance_km) as max_distance
        FROM routes
    """)).fetchone()
    
    print(f"\n📊 Route Statistics:")
    print(f"  Total routes: {stats[0]:,}")
    print(f"  Airports with outgoing routes: {stats[1]}")
    print(f"  Airports with incoming routes: {stats[2]}")
    print(f"  Average distance: {stats[3]:.1f} km")
    print(f"  Longest route: {stats[4]:.1f} km")
