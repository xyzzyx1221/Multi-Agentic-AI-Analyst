import os
import bcrypt
import psycopg
from db import get_pool
from dotenv import load_dotenv

load_dotenv()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_user(username, password):
    pool = get_pool()
    hashed = hash_password(password)
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS users (user_id SERIAL PRIMARY KEY, username VARCHAR(50) UNIQUE NOT NULL, password_hash TEXT NOT NULL, query_count INTEGER DEFAULT 0);"
                )
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING user_id;",
                    (username, hashed)
                )
                user_id = cur.fetchone()[0]
                conn.commit()
                return user_id
    except Exception as e:
        print(f"Signup error: {e}")
        return None

def login_user(username, password):
    pool = get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, password_hash FROM users WHERE username = %s;", (username,))
                result = cur.fetchone()
                if result and verify_password(password, result[1]):
                    return result[0]
    except Exception as e:
        print(f"Login error: {e}")
    return None

def get_user_quota(user_id):
    pool = get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT query_count FROM users WHERE user_id = %s;", (user_id,))
                res = cur.fetchone()
                return res[0] if res else 0
    except Exception:
        return 0

def increment_user_quota(user_id):
    pool = get_pool()
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET query_count = query_count + 1 WHERE user_id = %s;", (user_id,))
                conn.commit()
    except Exception as e:
        print(f"Quota update error: {e}")
