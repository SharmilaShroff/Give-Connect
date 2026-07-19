"""
Post lifecycle: creation (location + at least one hashtag are COMPULSORY per spec),
likes, comments, shares, reports, "not interested", and impression tracking.
"""
import re
from database.db import run_query, run_update

def cleanup_expired_food_posts():
    """Automatically marks posts with #food as deleted if they are older than 24 hours."""
    run_update(
        """UPDATE posts p
           JOIN post_hashtags ph ON p.post_id = ph.post_id
           JOIN hashtags h ON ph.hashtag_id = h.hashtag_id
           SET p.is_deleted = TRUE
           WHERE h.tag = 'food' 
             AND p.is_deleted = FALSE 
             AND p.created_at < NOW() - INTERVAL 24 HOUR"""
    )


def _get_or_create_hashtag_id(tag: str) -> int:
    tag = tag.lower().lstrip("#").strip()
    row = run_query("SELECT hashtag_id FROM hashtags WHERE tag=%s", (tag,), fetchone=True)
    if row:
        return row["hashtag_id"]
    return run_update("INSERT INTO hashtags (tag) VALUES (%s)", (tag,), return_lastrowid=True)


def extract_hashtags(caption: str) -> list[str]:
    return re.findall(r"#(\w+)", caption or "")


def create_post(user_id: str, caption: str, image_path: str, location: str,
                 hashtags: list[str], donation_type: str = None, tagged_users: list[str] = None):
    """
    Enforces the two compulsory fields from the spec:
      - location must be non-empty (tag/geo-location)
      - at least one hashtag must be supplied (either typed in caption as #tag or picked explicitly)
    """
    if not location or not location.strip():
        raise ValueError("Location is required for every post.")
    all_tags = list({*(hashtags or []), *extract_hashtags(caption)})
    all_tags = [t.lstrip("#").strip().lower() for t in all_tags if t.strip()]
    if not all_tags:
        raise ValueError("At least one hashtag is required for every post.")

    post_id = run_update(
        """INSERT INTO posts (user_id, caption, image_path, location, donation_type)
           VALUES (%s,%s,%s,%s,%s)""",
        (user_id, caption, image_path, location, donation_type),
        return_lastrowid=True,
    )
    for tag in all_tags:
        hashtag_id = _get_or_create_hashtag_id(tag)
        run_update("INSERT IGNORE INTO post_hashtags (post_id, hashtag_id) VALUES (%s,%s)", (post_id, hashtag_id))
    for tagged in (tagged_users or []):
        if tagged.strip():
            run_update("INSERT IGNORE INTO post_tags (post_id, tagged_user) VALUES (%s,%s)", (post_id, tagged.strip()))
    return post_id


def register_impression(post_id: int, viewer_id: str):
    """Called once per (viewer,post) render to feed the Priority LangGraph's impression count."""
    run_update("UPDATE posts SET impressions = impressions + 1 WHERE post_id=%s", (post_id,))


def like_post(user_id: str, post_id: int):
    run_update("INSERT IGNORE INTO post_likes (post_id, user_id) VALUES (%s,%s)", (post_id, user_id))


def unlike_post(user_id: str, post_id: int):
    run_update("DELETE FROM post_likes WHERE post_id=%s AND user_id=%s", (post_id, user_id))


def add_comment(user_id: str, post_id: int, content: str):
    comment_id = run_update("INSERT INTO comments (post_id, user_id, content) VALUES (%s,%s,%s)",
                       (post_id, user_id, content), return_lastrowid=True)
    try:
        from backend.notifications import parse_comment_tags_and_notify
        parse_comment_tags_and_notify(user_id, post_id, content)
    except Exception:
        pass
    return comment_id


def delete_post(user_id: str, post_id: int):
    # Verify post exists and user owns it
    post = run_query("SELECT user_id FROM posts WHERE post_id=%s AND is_deleted=FALSE", (post_id,), fetchone=True)
    if not post:
        raise ValueError("Post not found.")
    if post["user_id"] != user_id:
        raise PermissionError("You are not authorized to delete this post.")
    run_update("UPDATE posts SET is_deleted=TRUE WHERE post_id=%s", (post_id,))


def share_post(user_id: str, post_id: int):
    run_update("INSERT INTO post_shares (post_id, user_id) VALUES (%s,%s)", (post_id, user_id))


def mark_not_interested(user_id: str, post_id: int, reason: str):
    if not reason or not reason.strip():
        raise ValueError("A reason is required.")
    run_update("INSERT INTO not_interested (user_id, post_id, reason) VALUES (%s,%s,%s)",
               (user_id, post_id, reason.strip()))


def report_post(user_id: str, post_id: int, reason: str, details: str = ""):
    run_update("INSERT INTO reports (post_id, reported_by, reason, details) VALUES (%s,%s,%s,%s)",
               (post_id, user_id, reason, details))


def get_post(post_id: int):
    cleanup_expired_food_posts()
    return run_query("SELECT * FROM posts WHERE post_id=%s AND is_deleted=FALSE", (post_id,), fetchone=True)


def get_post_hashtags(post_id: int) -> list[str]:
    rows = run_query(
        """SELECT h.tag FROM post_hashtags ph JOIN hashtags h ON h.hashtag_id=ph.hashtag_id
           WHERE ph.post_id=%s""", (post_id,))
    return [r["tag"] for r in rows]


def get_comments(post_id: int):
    return run_query(
        """SELECT c.*, u.full_name, u.is_verified FROM comments c JOIN users u ON u.user_id=c.user_id
           WHERE c.post_id=%s ORDER BY c.created_at ASC""", (post_id,))


def get_like_count(post_id: int) -> int:
    row = run_query("SELECT COUNT(*) AS c FROM post_likes WHERE post_id=%s", (post_id,), fetchone=True)
    return row["c"] if row else 0


def user_liked(post_id: int, user_id: str) -> bool:
    row = run_query("SELECT 1 FROM post_likes WHERE post_id=%s AND user_id=%s", (post_id, user_id), fetchone=True)
    return row is not None


def get_user_posts(user_id: str):
    cleanup_expired_food_posts()
    return run_query(
        "SELECT * FROM posts WHERE user_id=%s AND is_deleted=FALSE ORDER BY created_at DESC", (user_id,))


def get_tagged_posts(user_id: str):
    return run_query(
        """SELECT p.* FROM posts p JOIN post_tags pt ON pt.post_id=p.post_id
           WHERE pt.tagged_user=%s AND p.is_deleted=FALSE ORDER BY p.created_at DESC""", (user_id,))


def get_saved_posts(user_id: str):
    return run_query(
        """SELECT p.* FROM posts p JOIN saved_posts s ON s.post_id = p.post_id
           WHERE s.user_id=%s AND p.is_deleted=FALSE ORDER BY s.saved_at DESC""", (user_id,))


def save_post(user_id: str, post_id: int):
    run_update("INSERT IGNORE INTO saved_posts (user_id, post_id) VALUES (%s,%s)", (user_id, post_id))


def unsave_post(user_id: str, post_id: int):
    run_update("DELETE FROM saved_posts WHERE user_id=%s AND post_id=%s", (user_id, post_id))


def is_saved(user_id: str, post_id: int) -> bool:
    row = run_query("SELECT 1 FROM saved_posts WHERE user_id=%s AND post_id=%s", (user_id, post_id), fetchone=True)
    return row is not None


def hide_user(user_id: str, target_user_id: str):
    run_update("INSERT IGNORE INTO hidden_users (user_id, hidden_user_id) VALUES (%s,%s)", (user_id, target_user_id))


def hide_hashtag(user_id: str, hashtag: str):
    tag = hashtag.lower().lstrip("#").strip()
    run_update("INSERT IGNORE INTO hidden_hashtags (user_id, hashtag) VALUES (%s,%s)", (user_id, tag))


def candidate_feed_posts(viewer_id: str, limit: int = 200):
    """
    Pulls a candidate pool for the two LangGraph flows to score:
    excludes the viewer's own posts, deleted posts, and posts already marked not-interested,
    as well as hidden users and hidden hashtags.
    """
    cleanup_expired_food_posts()
    return run_query(
        """SELECT p.*, u.full_name, u.is_verified
           FROM posts p
           JOIN users u ON u.user_id = p.user_id
           WHERE p.is_deleted = FALSE
             AND p.user_id != %s
             AND p.post_id NOT IN (SELECT post_id FROM not_interested WHERE user_id=%s)
             AND p.user_id NOT IN (SELECT hidden_user_id FROM hidden_users WHERE user_id=%s)
             AND p.post_id NOT IN (SELECT post_id FROM post_likes WHERE user_id=%s)
             AND p.post_id NOT IN (SELECT post_id FROM saved_posts WHERE user_id=%s)
             AND NOT EXISTS (
                 SELECT 1 FROM post_hashtags ph 
                 JOIN hashtags h ON ph.hashtag_id = h.hashtag_id
                 JOIN hidden_hashtags hh ON h.tag = hh.hashtag 
                 WHERE ph.post_id = p.post_id AND hh.user_id = %s
             )
           ORDER BY p.created_at DESC
           LIMIT %s""",
        (viewer_id, viewer_id, viewer_id, viewer_id, viewer_id, viewer_id, limit),
    )
