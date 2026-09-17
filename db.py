import os
import json
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()

# Configuration from environment
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")

# Global connection pool
# Initialized as None, created once on first access
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = ConnectionPool(conninfo=NEON_DATABASE_URL, open=True)
    return _pool

def fetch_db_schema():
    """
    Fetches the database schema (tables and columns) and returns it as a dictionary.
    Caches to schema_cache.json to avoid redundant calls.
    """
    cache_file = "schema_cache.json"
    
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    pool = get_pool()
    schema = {}
    
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                # Query to get all tables and their columns in the public schema
                cur.execute("""
                    SELECT table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position;
                """)
                
                for table, column, dtype in cur.fetchall():
                    if table not in schema:
                        schema[table] = []
                    schema[table].append({"column": column, "type": dtype})
        
        with open(cache_file, "w") as f:
            json.dump(schema, f, indent=2)
            
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return {}

    return schema

def execute_query(sql):
    """
    Executes a SQL query using the persistent pool and returns results.
    """
    pool = get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
                conn.commit()
                return "Success"
    except Exception as e:
        return f"Error: {str(e)}"
