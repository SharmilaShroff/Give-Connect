"""
Backend APIs for the standalone Admin Portal.
All endpoints require an authenticated admin `user_id`.
"""
from database.db import run_query, run_update
from backend.admin import _require_admin

def get_dashboard_metrics(admin_id: str) -> dict:
    _require_admin(admin_id)
    
    users = run_query("SELECT COUNT(*) as c FROM users", fetchone=True)
    posts = run_query("SELECT COUNT(*) as c FROM posts WHERE is_deleted=FALSE", fetchone=True)
    ngos = run_query("SELECT COUNT(*) as c FROM users WHERE account_type='ngo'", fetchone=True)
    reports = run_query("SELECT COUNT(*) as c FROM reports", fetchone=True)
    verified = run_query("SELECT COUNT(*) as c FROM users WHERE is_verified=TRUE AND account_type='ngo'", fetchone=True)
    
    # recent 10 reports
    recent_reports = run_query(
        """SELECT r.*, p.caption, u_reporter.full_name as reporter_name, u_poster.user_id as poster_id
           FROM reports r
           JOIN posts p ON p.post_id = r.post_id
           JOIN users u_reporter ON u_reporter.user_id = r.reported_by
           JOIN users u_poster ON u_poster.user_id = p.user_id
           ORDER BY r.created_at DESC
           LIMIT 10"""
    )
    
    return {
        "total_users": users["c"] if users else 0,
        "total_posts": posts["c"] if posts else 0,
        "total_ngos": ngos["c"] if ngos else 0,
        "total_reports": reports["c"] if reports else 0,
        "total_verified_ngos": verified["c"] if verified else 0,
        "recent_reports": recent_reports or []
    }

def get_all_reports(admin_id: str):
    _require_admin(admin_id)
    return run_query(
        """SELECT r.*, p.caption, p.image_path, u_reporter.full_name as reporter_name, u_poster.user_id as poster_id, u_poster.full_name as poster_name
           FROM reports r
           JOIN posts p ON p.post_id = r.post_id
           JOIN users u_reporter ON u_reporter.user_id = r.reported_by
           JOIN users u_poster ON u_poster.user_id = p.user_id
           ORDER BY r.created_at DESC"""
    )

def ignore_report(admin_id: str, report_id: int):
    _require_admin(admin_id)
    run_update("DELETE FROM reports WHERE report_id=%s", (report_id,))

def delete_post(admin_id: str, post_id: int):
    _require_admin(admin_id)
    # The prompt specified "Deleting a post should remove it from the platform", so we could physically delete it
    # But schema uses is_deleted flag. We can physically delete to clear reports cascadingly, or soft delete.
    # We will do physical delete for full compliance with "Remove it from the platform"
    run_update("DELETE FROM posts WHERE post_id=%s", (post_id,))

def get_all_users(admin_id: str, search_query: str = ""):
    _require_admin(admin_id)
    query = f"%{search_query}%"
    return run_query(
        """SELECT u.*, 
           (SELECT COUNT(*) FROM posts WHERE posts.user_id = u.user_id AND is_deleted=FALSE) as post_count,
           (SELECT COUNT(*) FROM reports r JOIN posts p ON p.post_id = r.post_id WHERE p.user_id = u.user_id) as reports_against
           FROM users u
           WHERE u.user_id LIKE %s OR u.full_name LIKE %s OR u.email LIKE %s
           ORDER BY u.created_at DESC""",
        (query, query, query)
    )

def delete_user(admin_id: str, target_user_id: str):
    _require_admin(admin_id)
    # This will cascade delete their posts, comments, likes, etc. per schema.sql
    run_update("DELETE FROM users WHERE user_id=%s", (target_user_id,))

def get_ngos(admin_id: str):
    _require_admin(admin_id)
    return run_query(
        """SELECT u.*, n.registration_number, n.legal_verification_doc, 
           n.bank_account_number, n.bank_ifsc, n.bank_name, n.account_holder_name
           FROM users u
           LEFT JOIN ngo_details n ON n.user_id = u.user_id
           WHERE u.account_type='ngo'
           ORDER BY u.created_at DESC"""
    )
