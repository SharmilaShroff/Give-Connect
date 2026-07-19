from database.db import run_query
from backend.profile import search_users

def search_locations(query: str):
    like = f"%{query}%"
    return run_query(
        """SELECT DISTINCT location FROM posts 
           WHERE location LIKE %s AND is_deleted=FALSE 
           LIMIT 20""", 
        (like,)
    )

def search_hashtags(query: str):
    tag = query.lower().lstrip("#").strip()
    like = f"%{tag}%"
    return run_query(
        """SELECT tag FROM hashtags 
           WHERE tag LIKE %s 
           LIMIT 20""", 
        (like,)
    )

def search_posts_by_location(location: str):
    return run_query(
        """SELECT p.*, u.full_name, u.is_verified 
           FROM posts p 
           JOIN users u ON u.user_id = p.user_id 
           WHERE p.location = %s AND p.is_deleted=FALSE 
           ORDER BY p.created_at DESC LIMIT 50""", 
        (location,)
    )

def search_posts_by_hashtag(hashtag: str):
    tag = hashtag.lower().lstrip("#").strip()
    return run_query(
        """SELECT p.*, u.full_name, u.is_verified 
           FROM posts p 
           JOIN users u ON u.user_id = p.user_id 
           JOIN post_hashtags ph ON ph.post_id = p.post_id
           JOIN hashtags h ON h.hashtag_id = ph.hashtag_id
           WHERE h.tag = %s AND p.is_deleted=FALSE 
           ORDER BY p.created_at DESC LIMIT 50""", 
        (tag,)
    )
