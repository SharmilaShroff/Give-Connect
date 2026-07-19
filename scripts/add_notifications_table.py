"""
Creates the notifications table in the MySQL database.
Usage:
    python scripts/add_notifications_table.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import run_update

if __name__ == "__main__":
    print("Creating notifications table...")
    sql = """
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        sender_id VARCHAR(50) NOT NULL,
        notification_type ENUM('comment_tag', 'new_message') NOT NULL,
        reference_id BIGINT NOT NULL,
        content TEXT,
        is_read BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
    """
    try:
        run_update(sql)
        print("Notifications table created successfully!")
    except Exception as e:
        print(f"Error creating table: {e}")
        sys.exit(1)
