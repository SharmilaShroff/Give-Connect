"""
Communities: two flavors selected at creation time -
  - 'challenge'   -> shows each member's live progress bar; members chat + like/celebrate progress
  - 'discussion'  -> members post items that require immediate action
"""
from database.db import run_query, run_update


def create_community(name: str, description: str, community_type: str, created_by: str) -> int:
    if community_type not in ("challenge", "discussion"):
        raise ValueError("community_type must be 'challenge' or 'discussion'")
    community_id = run_update(
        "INSERT INTO communities (name, description, community_type, created_by) VALUES (%s,%s,%s,%s)",
        (name, description, community_type, created_by), return_lastrowid=True)
    join_community(community_id, created_by)
    return community_id


def join_community(community_id: int, user_id: str):
    run_update("INSERT IGNORE INTO community_members (community_id, user_id) VALUES (%s,%s)",
               (community_id, user_id))
    community = run_query("SELECT community_type FROM communities WHERE community_id=%s",
                           (community_id,), fetchone=True)
    if community and community["community_type"] == "challenge":
        run_update("INSERT IGNORE INTO community_progress (community_id, user_id) VALUES (%s,%s)",
                   (community_id, user_id))


def leave_community(community_id: int, user_id: str):
    run_update("DELETE FROM community_members WHERE community_id=%s AND user_id=%s", (community_id, user_id))


def get_user_communities(user_id: str):
    return run_query(
        """SELECT c.* FROM communities c JOIN community_members cm ON cm.community_id=c.community_id
           WHERE cm.user_id=%s ORDER BY c.created_at DESC""", (user_id,))


def get_all_communities():
    return run_query("SELECT * FROM communities ORDER BY created_at DESC")


def update_progress(community_id: int, user_id: str, current_value: int, target_value: int = None, goal_label: str = None):
    fields, params = ["current_value=%s"], [current_value]
    if target_value is not None:
        fields.append("target_value=%s"); params.append(target_value)
    if goal_label is not None:
        fields.append("goal_label=%s"); params.append(goal_label)
    fields.append("updated_at=NOW()")
    params.extend([community_id, user_id])
    run_update(f"UPDATE community_progress SET {', '.join(fields)} WHERE community_id=%s AND user_id=%s",
               tuple(params))


def get_progress_board(community_id: int):
    return run_query(
        """SELECT cp.*, u.full_name, u.is_verified FROM community_progress cp
           JOIN users u ON u.user_id = cp.user_id
           WHERE cp.community_id=%s ORDER BY (cp.current_value / NULLIF(cp.target_value,0)) DESC""",
        (community_id,))


def post_message(community_id: int, user_id: str, content: str, image_path: str = None, is_urgent: bool = False):
    return run_update(
        """INSERT INTO community_messages (community_id, user_id, content, image_path, is_urgent)
           VALUES (%s,%s,%s,%s,%s)""",
        (community_id, user_id, content, image_path, is_urgent), return_lastrowid=True)


def get_messages(community_id: int):
    return run_query(
        """SELECT cm.*, u.full_name, u.is_verified,
                  (SELECT COUNT(*) FROM community_message_reactions r WHERE r.message_id=cm.message_id AND r.reaction='like') AS likes,
                  (SELECT COUNT(*) FROM community_message_reactions r WHERE r.message_id=cm.message_id AND r.reaction='celebrate') AS celebrations
           FROM community_messages cm JOIN users u ON u.user_id = cm.user_id
           WHERE cm.community_id=%s ORDER BY cm.sent_at ASC""", (community_id,))


def react_to_message(message_id: int, user_id: str, reaction: str):
    if reaction not in ("like", "celebrate"):
        raise ValueError("reaction must be 'like' or 'celebrate'")
    run_update(
        """INSERT INTO community_message_reactions (message_id, user_id, reaction) VALUES (%s,%s,%s)
           ON DUPLICATE KEY UPDATE reaction=%s""",
        (message_id, user_id, reaction, reaction))
