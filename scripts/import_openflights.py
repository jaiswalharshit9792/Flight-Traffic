import sys
sys.path.append('/app')
import requests, csv
from sqlalchemy import create_engine, text
from config import get_settings

engine = create_engine(get_settings().DATABASE_URL)

print("Downloading OpenFlights airports dataset...")
r = requests.get("https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat")
with open("airports.dat", "wb") as f:
    f.write(r.content)

with open("airports.dat", encoding="utf-8") as f:
    airports = []
    for row in csv.reader(f):
        if len(row) >= 8 and row[0].isdigit():
            airports.append((row[0], row[1], row[2], row[3],
                           row[4] if row[4] != '\\N' else None,
                           row[6], row[7],
                           row[8] if row[8].lstrip('-').isdigit() else None))

print(f"Importing {len(airports)} airports...")
with engine.connect() as conn:
    for i in range(0, len(airports), 1000):
        batch = airports[i:i+1000]
        for a in batch:
            conn.execute(text(
                "INSERT INTO airports (id,name,city,country,iata_code,latitude,longitude,altitude,embedding) "
                "VALUES (:id,:name,:city,:country,:iata,:lat,:lng,:alt,NULL) "
                "ON DUPLICATE KEY UPDATE name=VALUES(name)"
            ), {
                "id": a[0],
                "name": a[1],
                "city": a[2],
                "country": a[3],
                "iata": a[4],
                "lat": a[5],
                "lng": a[6],
                "alt": a[7]
            })
        conn.commit()
        print(f"  ✓ {min(i+1000, len(airports))}/{len(airports)} airports")

print("✅ Import complete!")
