"""
Authentication & account creation.
Two registration paths per spec: individual and NGO.
Passwords are bcrypt-hashed; nothing is ever stored in plaintext.
"""
import bcrypt
from database.db import run_query, run_update


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def user_id_exists(user_id: str) -> bool:
    row = run_query("SELECT user_id FROM users WHERE user_id=%s", (user_id,), fetchone=True)
    return row is not None


def email_exists(email: str) -> bool:
    row = run_query("SELECT user_id FROM users WHERE email=%s", (email,), fetchone=True)
    return row is not None


def login(user_id: str, password: str):
    """Returns the user dict on success, None on failure."""
    user = run_query("SELECT * FROM users WHERE user_id=%s", (user_id,), fetchone=True)
    if not user:
        return None
    if user["is_blocked"]:
        raise PermissionError("This account has been blocked by platform authority.")
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def register_individual(user_id: str, password: str, email: str, full_name: str, interests: list[str]):
    if user_id_exists(user_id):
        raise ValueError("User ID already taken.")
    if email_exists(email):
        raise ValueError("Email already registered.")
    pw_hash = hash_password(password)
    interests_str = ",".join(sorted({i.strip().lower() for i in interests if i.strip()}))
    run_update(
        """INSERT INTO users (user_id, password_hash, account_type, email, full_name, interests)
           VALUES (%s,%s,'individual',%s,%s,%s)""",
        (user_id, pw_hash, email, full_name, interests_str),
    )
    return True


def register_ngo(user_id: str, password: str, email: str, ngo_name: str,
                  registration_number: str, legal_doc_path: str,
                  bank_account_number: str, bank_ifsc: str, bank_name: str,
                  account_holder_name: str):
    if user_id_exists(user_id):
        raise ValueError("User ID already taken.")
    if email_exists(email):
        raise ValueError("Email already registered.")
    if not legal_doc_path or not legal_doc_path.strip():
        raise ValueError("Legal verification document is required.")
    if not bank_account_number or not bank_account_number.strip() or not bank_ifsc or not bank_ifsc.strip() or not bank_name or not bank_name.strip() or not account_holder_name or not account_holder_name.strip():
        raise ValueError("All bank details (Account number, IFSC, Bank name, Account holder) are compulsory.")
        
    pw_hash = hash_password(password)
    run_update(
        """INSERT INTO users (user_id, password_hash, account_type, email, full_name)
           VALUES (%s,%s,'ngo',%s,%s)""",
        (user_id, pw_hash, email, ngo_name),
    )
    run_update(
        """INSERT INTO ngo_details (user_id, registration_number, legal_verification_doc,
               bank_account_number, bank_ifsc, bank_name, account_holder_name)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (user_id, registration_number, legal_doc_path, bank_account_number,
         bank_ifsc, bank_name, account_holder_name),
    )
    # NGOs are NOT auto-verified with the blue tick - admin_review_status starts 'pending'
    # and the blue-tick (users.is_verified) can only ever be set by backend/verification.py
    return True
