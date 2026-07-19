"""
Notifications module for GiveConnect.
Handles creating, fetching, and managing user notifications for comments tags and direct messages.
"""
import re
from database.db import run_query, run_update


def create_notification(user_id: str, sender_id: str, notification_type: str, reference_id: int, content: str):
    """Inserts a notification row."""
    # Ensure user_id exists
    exists = run_query("SELECT 1 FROM users WHERE user_id=%s", (user_id,), fetchone=True)
    if not exists:
        return
    # Ensure sender_id exists
    exists_sender = run_query("SELECT 1 FROM users WHERE user_id=%s", (sender_id,), fetchone=True)
    if not exists_sender:
        return
    run_update(
        """INSERT INTO notifications (user_id, sender_id, notification_type, reference_id, content)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, sender_id, notification_type, reference_id, content)
    )


def get_unread_count(user_id: str) -> int:
    row = run_query("SELECT COUNT(*) AS c FROM notifications WHERE user_id=%s AND is_read=FALSE AND notification_type != 'new_message'", (user_id,), fetchone=True)
    return row["c"] if row else 0

def get_unread_messages_count(user_id: str) -> int:
    row = run_query("SELECT COUNT(*) AS c FROM notifications WHERE user_id=%s AND is_read=FALSE AND notification_type = 'new_message'", (user_id,), fetchone=True)
    return row["c"] if row else 0


def get_recent_notifications(user_id: str, limit: int = 5):
    return run_query(
        """SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT %s""",
        (user_id, limit)
    )


def mark_all_read(user_id: str):
    run_update("UPDATE notifications SET is_read=TRUE WHERE user_id=%s", (user_id,))

def mark_read(notification_id: int):
    run_update("UPDATE notifications SET is_read=TRUE WHERE notification_id=%s", (notification_id,))


def parse_comment_tags_and_notify(sender_id: str, post_id: int, content: str):
    """Parses @username from content and triggers comment_tag notifications."""
    usernames = re.findall(r"@(\w+)", content)
    # Deduplicate usernames
    usernames = list(set(usernames))
    for username in usernames:
        if username == sender_id:
            continue  # don't notify self
        # Verify the user exists
        user_row = run_query("SELECT 1 FROM users WHERE user_id=%s", (username,), fetchone=True)
        if user_row:
            create_notification(
                user_id=username,
                sender_id=sender_id,
                notification_type="comment_tag",
                reference_id=post_id,
                content=f"@{sender_id} tagged you in a comment."
            )
