"""
Authority/management actions - only reachable by account_type='admin'.
Handles resolving Scam Alert LangGraph escalations (delete post / block account)
and NGO verification queue is in verification.py.
"""
from database.db import run_query, run_update


class NotAuthorized(Exception):
    pass


def _require_admin(acting_user_id: str):
    row = run_query("SELECT account_type FROM users WHERE user_id=%s", (acting_user_id,), fetchone=True)
    if not row or row["account_type"] != "admin":
        raise NotAuthorized("Admin privileges required.")


def get_open_alerts(acting_admin_id: str):
    _require_admin(acting_admin_id)
    return run_query(
        """SELECT a.*, u.full_name, u.email, u.is_blocked, p.caption, p.image_path
           FROM admin_alerts a
           JOIN users u ON u.user_id = a.user_id
           LEFT JOIN posts p ON p.post_id = a.post_id
           WHERE a.status='open' ORDER BY a.created_at DESC"""
    )


def delete_reported_post(acting_admin_id: str, alert_id: int, post_id: int):
    _require_admin(acting_admin_id)
    run_update("UPDATE posts SET is_deleted=TRUE WHERE post_id=%s", (post_id,))
    run_update(
        "UPDATE admin_alerts SET status='deleted_post', resolved_by=%s, resolved_at=NOW() WHERE alert_id=%s",
        (acting_admin_id, alert_id),
    )


def block_account(acting_admin_id: str, alert_id: int, target_user_id: str):
    _require_admin(acting_admin_id)
    run_update("UPDATE users SET is_blocked=TRUE WHERE user_id=%s", (target_user_id,))
    run_update(
        "UPDATE admin_alerts SET status='blocked_account', resolved_by=%s, resolved_at=NOW() WHERE alert_id=%s",
        (acting_admin_id, alert_id),
    )


def dismiss_alert(acting_admin_id: str, alert_id: int):
    _require_admin(acting_admin_id)
    run_update(
        "UPDATE admin_alerts SET status='dismissed', resolved_by=%s, resolved_at=NOW() WHERE alert_id=%s",
        (acting_admin_id, alert_id),
    )


def unblock_account(acting_admin_id: str, target_user_id: str):
    _require_admin(acting_admin_id)
    run_update("UPDATE users SET is_blocked=FALSE WHERE user_id=%s", (target_user_id,))
