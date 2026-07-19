"""
Direct messages - text + image sharing between any two users/NGOs, Instagram-DM style.
"""
from database.db import run_query, run_update


def _ordered_pair(user_a: str, user_b: str):
    return (user_a, user_b) if user_a < user_b else (user_b, user_a)


def get_or_create_conversation(user_a: str, user_b: str) -> int:
    a, b = _ordered_pair(user_a, user_b)
    row = run_query("SELECT conversation_id FROM conversations WHERE user_a=%s AND user_b=%s",
                     (a, b), fetchone=True)
    if row:
        return row["conversation_id"]
    return run_update("INSERT INTO conversations (user_a, user_b) VALUES (%s,%s)", (a, b),
                       return_lastrowid=True)


def send_message(sender_id: str, other_user_id: str, content: str = None, image_path: str = None):
    if not content and not image_path:
        raise ValueError("Message must have text or an image.")
    conv_id = get_or_create_conversation(sender_id, other_user_id)
    message_id = run_update(
        "INSERT INTO messages (conversation_id, sender_id, content, image_path) VALUES (%s,%s,%s,%s)",
        (conv_id, sender_id, content, image_path),
        return_lastrowid=True
    )
    try:
        from backend.notifications import create_notification
        create_notification(
            user_id=other_user_id,
            sender_id=sender_id,
            notification_type="new_message",
            reference_id=conv_id,
            content=f"@{sender_id} sent you a new direct message."
        )
    except Exception:
        pass
    return conv_id


def get_messages(user_a: str, user_b: str):
    conv_id = get_or_create_conversation(user_a, user_b)
    return run_query(
        "SELECT * FROM messages WHERE conversation_id=%s ORDER BY sent_at ASC", (conv_id,))


def get_inbox(user_id: str):
    """List conversation partners ordered by most recent message."""
    return run_query(
        """SELECT
             CASE WHEN c.user_a=%s THEN c.user_b ELSE c.user_a END AS other_user,
             MAX(m.sent_at) AS last_message_at,
             SUBSTRING_INDEX(GROUP_CONCAT(m.content ORDER BY m.sent_at DESC SEPARATOR '||'), '||', 1) AS last_content
           FROM conversations c
           JOIN messages m ON m.conversation_id = c.conversation_id
           WHERE c.user_a=%s OR c.user_b=%s
           GROUP BY c.conversation_id
           ORDER BY last_message_at DESC""",
        (user_id, user_id, user_id))
