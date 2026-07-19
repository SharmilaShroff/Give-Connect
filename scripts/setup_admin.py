"""
Run this ONCE after applying database/schema.sql, to set a real bcrypt password
for the seeded 'admin' authority account (the schema.sql placeholder hash is not
a valid login - this script fixes that).

Usage:
    python scripts/setup_admin.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.auth import hash_password
from database.db import run_update

if __name__ == "__main__":
    new_password = input("Set a password for the 'admin' authority account: ").strip()
    if not new_password:
        print("Password cannot be empty.")
        sys.exit(1)
    run_update("UPDATE users SET password_hash=%s WHERE user_id='admin'", (hash_password(new_password),))
    print("Admin password set. Log in with user_id='admin' on the Home page.")
