import sys
import os

# Add parent directory to path so we can import database.db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import run_update

def main():
    print("Creating saved_posts table...")
    run_update("""
        CREATE TABLE IF NOT EXISTS saved_posts (
            user_id VARCHAR(50) NOT NULL,
            post_id BIGINT NOT NULL,
            saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
        )
    """)

    print("Creating hidden_users table...")
    run_update("""
        CREATE TABLE IF NOT EXISTS hidden_users (
            user_id VARCHAR(50) NOT NULL,
            hidden_user_id VARCHAR(50) NOT NULL,
            PRIMARY KEY (user_id, hidden_user_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (hidden_user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    print("Creating hidden_hashtags table...")
    run_update("""
        CREATE TABLE IF NOT EXISTS hidden_hashtags (
            user_id VARCHAR(50) NOT NULL,
            hashtag VARCHAR(100) NOT NULL,
            PRIMARY KEY (user_id, hashtag),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    print("Database updates completed successfully.")

if __name__ == "__main__":
    main()
