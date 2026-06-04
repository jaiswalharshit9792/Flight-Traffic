#!/usr/bin/env python3
"""
Generate AI embeddings for airport semantic search
Uses enhanced descriptions including hub_type, price_tier, and facilities
"""
import sys
sys.path.append('/app')
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
from config import get_settings
import time

print("Loading embedding model...")
model = SentenceTransformer(get_settings().EMBEDDING_MODEL)
engine = create_engine(get_settings().DATABASE_URL)

print("Fetching ALL airports with descriptions...")
with engine.connect() as conn:
    # Get ALL airports to regenerate with enhanced descriptions
    count_result = conn.execute(text("SELECT COUNT(*) FROM airports WHERE description IS NOT NULL")).fetchone()
    total_count = count_result[0]
    print(f"Total airports to process: {total_count}")
    
    airports = conn.execute(
        text("SELECT id, name, city, country, description FROM airports WHERE description IS NOT NULL")
    ).fetchall()

print(f"Regenerating embeddings for {len(airports)} airports with enhanced descriptions...")

batch_size = 50
for i in range(0, len(airports), batch_size):
    batch = airports[i:i+batch_size]
    
    for aid, name, city, country, description in batch:
        # Use the rich description field which includes hub_type, price_tier, facilities
        text_input = description if description else f"{name}, {city}, {country}"
        embedding = model.encode(text_input).tolist()

        with engine.connect() as conn:
            conn.execute(
                text("UPDATE airports SET embedding = VEC_FromText(:e) WHERE id = :id"),
                {'e': str(embedding), 'id': aid}
            )
            conn.commit()

    progress = min(i + batch_size, len(airports))
    print(f"  {progress}/{len(airports)} ({progress/len(airports)*100:.1f}%)")
    time.sleep(0.1)  # Small delay to avoid overloading

print("✅ Enhanced embeddings regenerated!")
print("\nNow searches like 'budget-friendly hubs in Asia' will work correctly!")
