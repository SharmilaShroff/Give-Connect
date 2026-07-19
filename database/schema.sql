-- ============================================================
-- Donation Social Platform - MySQL Schema
-- ============================================================
CREATE DATABASE IF NOT EXISTS donation_social CHARACTER SET utf8mb4;
USE donation_social;

-- ------------------------------------------------------------
-- USERS  (both individuals and NGOs live here; account_type differentiates)
-- ------------------------------------------------------------
CREATE TABLE users (
    user_id           VARCHAR(50) PRIMARY KEY,          -- chosen login userId, unique
    password_hash     VARCHAR(255) NOT NULL,
    account_type      ENUM('individual','ngo','admin') NOT NULL,
    email             VARCHAR(255) NOT NULL UNIQUE,
    full_name         VARCHAR(255),                     -- individual name OR NGO name
    profile_picture   VARCHAR(500) DEFAULT NULL,
    bio               VARCHAR(500) DEFAULT NULL,
    interests         TEXT DEFAULT NULL,                -- comma-separated preference tags (individuals)
    is_verified       BOOLEAN NOT NULL DEFAULT FALSE,    -- blue-tick, settable ONLY by admin backend code path
    verified_by        VARCHAR(50) DEFAULT NULL,         -- admin user_id who granted it (audit trail)
    verified_at        DATETIME DEFAULT NULL,
    is_blocked        BOOLEAN NOT NULL DEFAULT FALSE,    -- set by admin after scam confirmation
    is_flagged        BOOLEAN NOT NULL DEFAULT FALSE,    -- auto-set by Scam Alert LangGraph
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- NGO-specific verification & banking details (1:1 with users where account_type='ngo')
CREATE TABLE ngo_details (
    user_id                 VARCHAR(50) PRIMARY KEY,
    registration_number     VARCHAR(100) NOT NULL,
    legal_verification_doc  VARCHAR(500) NOT NULL,   -- path to uploaded registration/80G/12A doc etc.
    bank_account_number     VARCHAR(50) NOT NULL,
    bank_ifsc               VARCHAR(20) NOT NULL,
    bank_name               VARCHAR(150) NOT NULL,
    account_holder_name     VARCHAR(150) NOT NULL,
    admin_review_status     ENUM('pending','approved','rejected') DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- FOLLOWERS
-- ------------------------------------------------------------
CREATE TABLE followers (
    follower_id VARCHAR(50) NOT NULL,
    followee_id VARCHAR(50) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_id, followee_id),
    FOREIGN KEY (follower_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (followee_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- POSTS
-- ------------------------------------------------------------
CREATE TABLE posts (
    post_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id       VARCHAR(50) NOT NULL,
    caption       TEXT,
    image_path    VARCHAR(500),
    location      VARCHAR(255) NOT NULL,       -- COMPULSORY per spec
    donation_type VARCHAR(100) DEFAULT NULL,    -- e.g. food/clothes/money/books - used by chatbot matching
    impressions   INT NOT NULL DEFAULT 0,       -- views count, used by Priority LangGraph
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted    BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE hashtags (
    hashtag_id  INT AUTO_INCREMENT PRIMARY KEY,
    tag         VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE post_hashtags (            -- COMPULSORY: every post must have >=1 row here
    post_id     BIGINT NOT NULL,
    hashtag_id  INT NOT NULL,
    PRIMARY KEY (post_id, hashtag_id),
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (hashtag_id) REFERENCES hashtags(hashtag_id) ON DELETE CASCADE
);

CREATE TABLE post_tags (                -- users tagged IN a post (shows under "Tagged" on their profile)
    post_id     BIGINT NOT NULL,
    tagged_user VARCHAR(50) NOT NULL,
    PRIMARY KEY (post_id, tagged_user),
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (tagged_user) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE comments (
    comment_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    post_id      BIGINT NOT NULL,
    user_id      VARCHAR(50) NOT NULL,
    content      TEXT NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE post_likes (
    post_id  BIGINT NOT NULL,
    user_id  VARCHAR(50) NOT NULL,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE post_shares (
    share_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    post_id     BIGINT NOT NULL,
    user_id     VARCHAR(50) NOT NULL,
    shared_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- "Not interested" feedback -> excluded from feed + used to tune Smart Matching
CREATE TABLE not_interested (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     VARCHAR(50) NOT NULL,
    post_id     BIGINT NOT NULL,
    reason      VARCHAR(255) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
);

-- Reports (includes scam reports which feed the Scam Alert LangGraph)
CREATE TABLE reports (
    report_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    post_id     BIGINT NOT NULL,
    reported_by VARCHAR(50) NOT NULL,
    reason      ENUM('scam','spam','inappropriate','misleading','other') NOT NULL,
    details     VARCHAR(500),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Authority/management review queue populated by Scam Alert LangGraph
CREATE TABLE admin_alerts (
    alert_id     BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id      VARCHAR(50) NOT NULL,
    post_id      BIGINT DEFAULT NULL,
    alert_type   ENUM('scam_suspected') DEFAULT 'scam_suspected',
    ai_reasoning TEXT,
    report_count INT DEFAULT 0,
    status       ENUM('open','deleted_post','blocked_account','dismissed') DEFAULT 'open',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_by  VARCHAR(50) DEFAULT NULL,
    resolved_at  DATETIME DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- DIRECT MESSAGES
-- ------------------------------------------------------------
CREATE TABLE conversations (
    conversation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_a          VARCHAR(50) NOT NULL,
    user_b          VARCHAR(50) NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_pair (user_a, user_b),
    FOREIGN KEY (user_a) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (user_b) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE messages (
    message_id      BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT NOT NULL,
    sender_id       VARCHAR(50) NOT NULL,
    content         TEXT,
    image_path      VARCHAR(500) DEFAULT NULL,
    sent_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read         BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- COMMUNITIES
-- ------------------------------------------------------------
CREATE TABLE communities (
    community_id   BIGINT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    description    VARCHAR(500),
    community_type ENUM('challenge','discussion') NOT NULL,
    created_by     VARCHAR(50) NOT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE community_members (
    community_id BIGINT NOT NULL,
    user_id      VARCHAR(50) NOT NULL,
    joined_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (community_id, user_id),
    FOREIGN KEY (community_id) REFERENCES communities(community_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Per-member progress bar for CHALLENGE communities
CREATE TABLE community_progress (
    community_id  BIGINT NOT NULL,
    user_id       VARCHAR(50) NOT NULL,
    goal_label    VARCHAR(255) DEFAULT 'Challenge Progress',
    current_value INT DEFAULT 0,
    target_value  INT DEFAULT 100,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (community_id, user_id),
    FOREIGN KEY (community_id) REFERENCES communities(community_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Chat/messages inside a community (used for challenge cheer + discussion posts)
CREATE TABLE community_messages (
    message_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    community_id  BIGINT NOT NULL,
    user_id       VARCHAR(50) NOT NULL,
    content       TEXT,
    image_path    VARCHAR(500) DEFAULT NULL,
    is_urgent     BOOLEAN DEFAULT FALSE,   -- "requires immediate action" flag for discussion communities
    sent_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (community_id) REFERENCES communities(community_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE community_message_reactions (
    message_id BIGINT NOT NULL,
    user_id    VARCHAR(50) NOT NULL,
    reaction   ENUM('like','celebrate') DEFAULT 'like',
    PRIMARY KEY (message_id, user_id),
    FOREIGN KEY (message_id) REFERENCES community_messages(message_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- FEED SCORING CACHE (written by the two LangGraph flows)
-- ------------------------------------------------------------
CREATE TABLE post_scores (
    post_id           BIGINT NOT NULL,
    viewer_id         VARCHAR(50) NOT NULL,      -- scores are personalized per viewer (smart matching)
    priority_score    FLOAT DEFAULT 0,           -- from Priority LangGraph (recency + low impressions)
    match_score       FLOAT DEFAULT 0,           -- from Smart Matching LangGraph (hashtag/interest overlap)
    final_score       FLOAT DEFAULT 0,
    computed_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, viewer_id),
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (viewer_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Seed an admin/authority account (password should be changed immediately)
-- password hash below corresponds to 'ChangeMe123!' via bcrypt - replace in production
-- ------------------------------------------------------------
INSERT INTO users (user_id, password_hash, account_type, email, full_name, is_verified)
VALUES ('admin', '$2b$12$6yTeGKHPYX4mgtyjwfTB3u1KBl2N63In4epBZrify27Zf2mot2BWC', 'admin', 'admin@example.com', 'Platform Authority', TRUE)
ON DUPLICATE KEY UPDATE user_id=user_id;

-- ------------------------------------------------------------
-- NOTIFICATIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         VARCHAR(50) NOT NULL,
    sender_id       VARCHAR(50) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    reference_id    BIGINT,
    content         TEXT,
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- PREFERENCES & SAVES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hidden_users (
    user_id VARCHAR(50) NOT NULL,
    hidden_user_id VARCHAR(50) NOT NULL,
    PRIMARY KEY (user_id, hidden_user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (hidden_user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hidden_hashtags (
    user_id VARCHAR(50) NOT NULL,
    hashtag VARCHAR(100) NOT NULL,
    PRIMARY KEY (user_id, hashtag),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS saved_posts (
    user_id VARCHAR(50) NOT NULL,
    post_id BIGINT NOT NULL,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, post_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
);
