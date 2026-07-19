"""
Profile & social graph: follow/unfollow, counts, editable profile fields.
Note: is_verified is intentionally NOT editable here - see backend/verification.py.
"""
from database.db import run_query, run_update


def get_user(user_id: str):
    return run_query("SELECT * FROM users WHERE user_id=%s", (user_id,), fetchone=True)


def follow(follower_id: str, followee_id: str):
    if follower_id == followee_id:
        raise ValueError("You can't follow yourself.")
    run_update("INSERT IGNORE INTO followers (follower_id, followee_id) VALUES (%s,%s)",
               (follower_id, followee_id))


def unfollow(follower_id: str, followee_id: str):
    run_update("DELETE FROM followers WHERE follower_id=%s AND followee_id=%s", (follower_id, followee_id))


def is_following(follower_id: str, followee_id: str) -> bool:
    row = run_query("SELECT 1 FROM followers WHERE follower_id=%s AND followee_id=%s",
                     (follower_id, followee_id), fetchone=True)
    return row is not None


def follower_count(user_id: str) -> int:
    row = run_query("SELECT COUNT(*) AS c FROM followers WHERE followee_id=%s", (user_id,), fetchone=True)
    return row["c"] if row else 0


def following_count(user_id: str) -> int:
    row = run_query("SELECT COUNT(*) AS c FROM followers WHERE follower_id=%s", (user_id,), fetchone=True)
    return row["c"] if row else 0


def get_followers(user_id: str):
    return run_query(
        """SELECT u.user_id, u.full_name, u.profile_picture, u.is_verified
           FROM followers f JOIN users u ON u.user_id = f.follower_id WHERE f.followee_id=%s""", (user_id,))


def get_following(user_id: str):
    return run_query(
        """SELECT u.user_id, u.full_name, u.profile_picture, u.is_verified
           FROM followers f JOIN users u ON u.user_id = f.followee_id WHERE f.follower_id=%s""", (user_id,))


def update_profile(user_id: str, full_name: str = None, bio: str = None,
                    profile_picture: str = None, interests: list[str] = None):
    fields, params = [], []
    if full_name is not None:
        fields.append("full_name=%s"); params.append(full_name)
    if bio is not None:
        fields.append("bio=%s"); params.append(bio)
    if profile_picture is not None:
        fields.append("profile_picture=%s"); params.append(profile_picture)
    if interests is not None:
        fields.append("interests=%s"); params.append(",".join(sorted({i.lower().strip() for i in interests if i.strip()})))
    if not fields:
        return
    params.append(user_id)
    run_update(f"UPDATE users SET {', '.join(fields)} WHERE user_id=%s", tuple(params))


def search_users(query: str):
    like = f"%{query}%"
    return run_query(
        """SELECT user_id, full_name, profile_picture, is_verified, account_type FROM users
           WHERE (user_id LIKE %s OR full_name LIKE %s) AND is_blocked=FALSE LIMIT 20""",
        (like, like))
