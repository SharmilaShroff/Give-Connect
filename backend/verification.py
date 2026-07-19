"""
Blue-tick verification control.

Design intent (per spec: "should not be able to be copied/misused, only authority can give it"):
  - `users.is_verified` is NEVER exposed as an editable field anywhere in the individual/NGO
    registration or profile-edit flows (see auth.py / backend/profile.py - no such field there).
  - This module is the ONLY place in the entire codebase that writes to users.is_verified,
    and every function here demands the acting user's row have account_type='admin'.
  - The frontend renders the badge purely from this DB column (see frontend/utils/badge.py);
    there is no client-side flag a user could tamper with, since Streamlit session_state
    is server-side per session and the badge is re-read from MySQL on every page load.
"""
from database.db import run_query, run_update


class NotAuthorized(Exception):
    pass


def _require_admin(acting_user_id: str):
    row = run_query("SELECT account_type FROM users WHERE user_id=%s", (acting_user_id,), fetchone=True)
    if not row or row["account_type"] != "admin":
        raise NotAuthorized("Only platform authority accounts may grant or revoke verification.")


def grant_verification(acting_admin_id: str, target_user_id: str):
    _require_admin(acting_admin_id)
    run_update(
        """UPDATE users SET is_verified=TRUE, verified_by=%s, verified_at=NOW()
           WHERE user_id=%s""",
        (acting_admin_id, target_user_id),
    )
    return True


def revoke_verification(acting_admin_id: str, target_user_id: str):
    _require_admin(acting_admin_id)
    run_update(
        """UPDATE users SET is_verified=FALSE, verified_by=NULL, verified_at=NULL
           WHERE user_id=%s""",
        (target_user_id,),
    )
    return True


def pending_ngo_verifications(acting_admin_id: str):
    _require_admin(acting_admin_id)
    return run_query(
        """SELECT u.user_id, u.full_name, u.email, u.is_verified, n.registration_number,
                  n.legal_verification_doc, n.bank_name, n.admin_review_status
           FROM ngo_details n JOIN users u ON u.user_id = n.user_id
           WHERE n.admin_review_status='pending'"""
    )


def set_ngo_review_status(acting_admin_id: str, target_user_id: str, status: str):
    """status: 'approved' or 'rejected'. Approving does NOT auto-grant the blue tick -
    that remains a deliberate separate action via grant_verification()."""
    _require_admin(acting_admin_id)
    if status not in ("approved", "rejected"):
        raise ValueError("invalid status")
    run_update("UPDATE ngo_details SET admin_review_status=%s WHERE user_id=%s", (status, target_user_id))
    return True
