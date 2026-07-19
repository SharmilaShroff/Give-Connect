"""
The verified badge is rendered ONLY from the `is_verified` column fetched fresh
from MySQL on every render - there is no user-editable field anywhere in the
profile-edit or signup forms that maps to this, and no client-side state
(e.g. a session_state flag) is ever trusted for it. See backend/verification.py
for the single authoritative write path (admin-only).
"""

VERIFIED_BADGE_HTML = (
    '<span title="Verified by platform authority" '
    'style="display:inline-flex;align-items:center;justify-content:center;'
    'width:16px;height:16px;border-radius:50%;background:#1877F2;color:white;'
    'font-size:11px;margin-left:4px;">✓</span>'
)


def name_with_badge(name: str, is_verified: bool) -> str:
    # Prevent users from faking the badge using unicode/emojis in their names
    safe_name = str(name).replace("✓", "").replace("✔", "").replace("🔵", "").replace("☑", "")
    return f"{safe_name} {VERIFIED_BADGE_HTML}" if is_verified else safe_name
