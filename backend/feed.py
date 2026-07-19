"""
Builds each viewer's personalized feed by combining:
  - LangGraph #1 (Priority): boosts newer / less-seen posts
  - LangGraph #2 (Smart Matching): boosts posts whose hashtags match viewer's interests
final_score = priority_score * (0.4 + 0.6 * match_score)
  -> priority still matters even for a 0-match post (keeps the feed from being empty for
     new users with no interests set), but matching strongly amplifies relevant posts.
"""
from database.db import run_query, run_update
from backend.posts import candidate_feed_posts, get_post_hashtags
from backend.langgraph_flows.priority_flow import get_priority_score


def build_feed(viewer_id: str, viewer_interests: list[str], limit: int = 30, use_ai: bool = True):
    candidates = candidate_feed_posts(viewer_id, limit=200)
    scored = []
    for post in candidates:
        hashtags = get_post_hashtags(post["post_id"])
        # priority_score natively ranks by interests > low impressions (ignoring date)
        priority_score = get_priority_score(post["post_id"], viewer_interests, hashtags, post["impressions"], use_ai=use_ai)
        match_score = priority_score # Store the same for DB logging
        final_score = priority_score

        run_update(
            """INSERT INTO post_scores (post_id, viewer_id, priority_score, match_score, final_score)
               VALUES (%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE priority_score=%s, match_score=%s, final_score=%s, computed_at=NOW()""",
            (post["post_id"], viewer_id, priority_score, match_score, final_score,
             priority_score, match_score, final_score),
        )
        post["hashtags"] = hashtags
        post["priority_score"] = priority_score
        post["match_score"] = match_score
        post["final_score"] = final_score
        scored.append(post)

    scored.sort(key=lambda p: p["final_score"], reverse=True)
    return scored[:limit]
