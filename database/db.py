"""
Central MySQL connection helper.
Every backend module imports `get_connection()` / `run_query()` / `run_update()` from here
instead of opening its own connection, so pooling & config stay in one place.
"""
import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

_POOL = None


def _init_pool():
    global _POOL
    if _POOL is None:
        pool_kwargs = dict(
            pool_name="donation_social_pool",
            pool_size=5,
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "donation_social"),
        )
        # Aiven and other cloud providers require SSL
        if os.getenv("MYSQL_SSL", "").lower() == "true":
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            pool_kwargs["ssl_ca"] = ""
            pool_kwargs["ssl_disabled"] = False
            pool_kwargs["tls_versions"] = ["TLSv1.2", "TLSv1.3"]
        _POOL = pooling.MySQLConnectionPool(**pool_kwargs)
    return _POOL


def get_connection():
    return _init_pool().get_connection()


def run_query(sql: str, params: tuple = (), fetchone: bool = False):
    """SELECT helper. Returns list[dict] or single dict (if fetchone)."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        result = cur.fetchone() if fetchone else cur.fetchall()
        cur.close()
        return result
    finally:
        conn.close()


def run_update(sql: str, params: tuple = (), return_lastrowid: bool = False):
    """INSERT/UPDATE/DELETE helper. Commits automatically."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        last_id = cur.lastrowid
        cur.close()
        return last_id if return_lastrowid else True
    finally:
        conn.close()


def run_many(sql: str, seq_of_params: list):
    """Bulk insert helper, e.g. for hashtags."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(sql, seq_of_params)
        conn.commit()
        cur.close()
        return True
    finally:
        conn.close()
