import requests
from typing import Dict
from config import get_settings

settings = get_settings()

class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

    def text_to_sql(self, question: str) -> Dict:
        prompt = f"""You are a SQL expert. Generate a SIMPLE MariaDB SQL query based on this question.

Database schema:
- airports table: id, name, city, country, iata_code, icao_code, latitude, longitude, altitude, timezone, dst, tz_database_timezone, type, source, embedding
- routes table: id, airline, airline_id, source_airport, source_airport_id, dest_airport, dest_airport_id, codeshare, stops, equipment

CRITICAL RULES:
1. Use SIMPLE queries ONLY - NO subqueries, NO nested SELECT statements
2. Use straightforward JOINs with WHERE, GROUP BY, ORDER BY, LIMIT
3. Column names have NO spaces - always use table.column format (e.g., a.name, r.airline)
4. Use table aliases: 'a' for airports, 'r' for routes
5. MariaDB does NOT support LIMIT inside subqueries - use simple queries only
6. Return ONLY the SELECT statement, no explanations
7. Do NOT use quotes around column names
8. Ensure all column references have table prefix

Question: {question}

Generate ONLY a SIMPLE SQL query without subqueries:"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30
            )

            if response.status_code == 200:
                sql = response.json()["response"].strip()
                # Remove code blocks
                sql = sql.replace("```sql", "").replace("```", "").strip()
                
                # Extract only SELECT statement (remove explanations)
                lines = sql.split('\n')
                sql_lines = []
                for line in lines:
                    line = line.strip()
                    # Skip empty lines and explanatory text
                    if line and not line.startswith('#') and not line.startswith('--'):
                        # Stop if we hit explanatory text
                        if line.lower().startswith(('this', 'note:', 'here', 'the query', 'to find', 'explanation')):
                            break
                        sql_lines.append(line)
                
                sql = ' '.join(sql_lines).strip()
                
                # Remove trailing semicolon if present
                sql = sql.rstrip(';')
                
                # Basic validation
                if 'SELECT' not in sql.upper():
                    return {"success": False, "error": "Generated text is not a valid SQL query"}
                
                # Reject queries with subqueries (MariaDB limitations)
                sql_upper = sql.upper()
                # Count SELECT statements - if more than 1, it has subqueries
                select_count = sql_upper.count('SELECT')
                if select_count > 1:
                    return {"success": False, "error": "Query too complex - subqueries not supported. Please ask a simpler question."}
                
                # Fix incorrect database.alias syntax throughout the entire query
                # The LLM sometimes generates "airports.a" thinking it's database.table
                # We need to replace these EVERYWHERE (SELECT, FROM, JOIN, WHERE, etc.)
                import re
                
                # Remove the pattern "FROM airports.a" -> "FROM airports a" (and similar for routes)
                sql = re.sub(r'\bFROM\s+airports\.([a-zA-Z]\w*)', r'FROM airports \1', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bFROM\s+routes\.([a-zA-Z]\w*)', r'FROM routes \1', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bJOIN\s+airports\.([a-zA-Z]\w*)', r'JOIN airports \1', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bJOIN\s+routes\.([a-zA-Z]\w*)', r'JOIN routes \1', sql, flags=re.IGNORECASE)
                
                # Now remove ALL remaining "airports." and "routes." prefixes (they shouldn't be there)
                # After fixing FROM/JOIN, any remaining ones are errors
                sql = re.sub(r'\bairports\.', '', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\broutes\.', '', sql, flags=re.IGNORECASE)
                
                # Fix common syntax errors - but preserve SQL keywords
                
                # Remove spaces between table aliases and column names (but not keywords)
                # This fixes "T1 dest_airport_id" -> "T1.dest_airport_id"
                # But preserves "T1 JOIN", "T1 WHERE", etc.
                sql_keywords = ['JOIN', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'UNION', 'ON', 'AND', 'OR', 'FROM', 'AS']
                
                # Only fix if the word after T# is NOT a SQL keyword
                def fix_table_column(match):
                    table = match.group(1)
                    word = match.group(2)
                    if word.upper() in sql_keywords:
                        return f'{table} {word}'  # Keep space for keywords
                    else:
                        return f'{table}.{word}'  # Add dot for columns
                
                sql = re.sub(r'\b(T\d+|a|r|routes|airports)\s+([a-zA-Z_]+)', fix_table_column, sql)
                    
                return {"success": True, "sql": sql}
            return {"success": False, "error": "Failed to generate SQL"}
        except Exception as e:
            return {"success": False, "error": str(e)}
