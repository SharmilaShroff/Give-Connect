"""
Background job: any post tagged #food is automatically soft-deleted 24 hours
after creation (per spec - food donations spoil/expire quickly so the post
shouldn't linger in feeds). Runs via APScheduler inside the Streamlit process.
"""
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from database.db import run_query, run_update

logger = logging.getLogger("food_post_cleanup")
FOOD_POST_LIFETIME_HOURS = int(os.getenv("FOOD_POST_LIFETIME_HOURS", "24"))

_scheduler = None


def delete_expired_food_posts():
    rows = run_query(
        """SELECT p.post_id FROM posts p
           JOIN post_hashtags ph ON ph.post_id = p.post_id
           JOIN hashtags h ON h.hashtag_id = ph.hashtag_id
           WHERE h.tag = 'food'
             AND p.is_deleted = FALSE
             AND p.created_at <= NOW() - INTERVAL %s HOUR""",
        (FOOD_POST_LIFETIME_HOURS,),
    )
    for row in rows:
        run_update("UPDATE posts SET is_deleted=TRUE WHERE post_id=%s", (row["post_id"],))
        logger.info(f"Auto-deleted expired #food post {row['post_id']}")
    return len(rows)


def start_scheduler():
    """Call once per process (guarded in app entrypoint) so it doesn't spin up duplicate jobs
    every Streamlit re-run."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(delete_expired_food_posts, "interval", minutes=15, id="food_post_cleanup")
    _scheduler.start()
    return _scheduler
