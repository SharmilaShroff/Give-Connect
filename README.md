# GiveConnect — Donation Social Platform

A full-stack Instagram-style platform for individuals and NGOs to post, discover, and
coordinate donations. **Frontend: Streamlit. Backend: Python. Database: MySQL.**
Three independent **LangGraph** workflows (each with its own Grok/xAI API key) handle
feed ranking, interest matching, and scam detection; a separate **Gemini**-powered
chatbot helps donors find relevant posts.

This has been built and tested end-to-end against a real local MySQL instance
(schema load, signup, posts, follow/like/comment, DMs, communities, feed scoring,
scam escalation, and admin resolution all verified working).

## 1. Setup

```bash
python -m venv venv && source venv/bin/activate      # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env: MySQL credentials + your 3 Grok API keys + your Gemini API key
```

Create the database:
```bash
mysql -u root -p < database/schema.sql
```

Set a real admin password (the schema seeds a placeholder that can't actually log in):
```bash
python scripts/setup_admin.py
```

Run the app:
```bash
streamlit run frontend/Home.py
```
Log in as `admin` (with the password you just set) to reach the Authority Panel,
or use the "Create Account" tab to sign up as an individual or NGO.

## 2. Architecture

```
database/schema.sql        MySQL DDL - users, ngo_details, posts, hashtags, comments,
                            reports, admin_alerts, conversations/messages, communities,
                            community_progress, post_scores, etc.
database/db.py             Connection pool + run_query/run_update helpers

backend/auth.py            Signup (individual & NGO) + bcrypt login
backend/verification.py    THE ONLY code path allowed to set the blue-tick (admin-only)
backend/posts.py           Create post (location + hashtag compulsory), like, comment,
                            share, report, "not interested"
backend/feed.py            Combines LangGraph #1 + #2 into each viewer's personalized feed
backend/profile.py         Follow/unfollow, profile edit, search
backend/dm.py               Direct messages (text + image)
backend/community.py       Challenge / Discussion communities, progress bars, chat
backend/admin.py           Authority actions: delete post / block account / dismiss alert
backend/scheduler.py       Background job: auto-deletes #food posts after 24h
backend/file_utils.py      Upload handling (post images, profile pics, NGO docs, DM images)

backend/langgraph_flows/
  priority_flow.py         LangGraph #1 - PRIORITY: boosts newer + less-seen posts
                            (uses GROK_API_KEY_PRIORITY)
  smart_matching_flow.py   LangGraph #2 - SMART MATCHING: user interests <-> post hashtags
                            (uses GROK_API_KEY_MATCHING)
  scam_alert_flow.py       LangGraph #3 - SCAM ALERT: repeated-report analysis -> escalates
                            to admin_alerts for human review (uses GROK_API_KEY_SCAM)

chatbot/gemini_chatbot.py  Donation-finder chatbot (Gemini API) - grounded strictly in the
                            live post catalog, uses hashtags to identify category

frontend/Home.py           Login + Create Account (Individual / NGO radio)
frontend/pages/
  1_Feed.py                Search bar, ranked feed, share/comment/report/not-interested
  2_Profile.py             Instagram-style profile: pic, followers/following, Posts + Tagged tabs
  3_DM.py                  Inbox + chat, text/image
  4_Community.py           Followed communities, '+' to create (challenge/discussion),
                            live progress bars, chat with like/celebrate
  5_Create_Post.py         Post creation form (location + hashtags enforced)
  6_ChatBot.py             Gemini chatbot UI
  7_Admin.py               Authority panel: NGO doc review, grant/revoke blue-tick,
                            resolve scam alerts (delete post / block account)
```

## 3. Feature -> spec mapping (so you can verify against your original list)

- **Login / Create Account (NGO vs Individual)** → `Home.py`. NGO path collects legal
  verification doc + full bank details (`ngo_details` table); individual path collects
  name/email/interests and creates the userId+password.
- **Feed with search, share/comment/3-dot report/not-interested** → `1_Feed.py`.
  "Not interested" always asks for a reason and stores it (excluded from future feeds).
- **Compulsory location + hashtags on every post** → enforced server-side in
  `backend/posts.py::create_post` (raises `ValueError` if either is missing), not just
  in the UI, so it can't be bypassed.
- **LangGraph #1 - Priority (fresh + low-impression boost, LinkedIn-style)** →
  `priority_flow.py`.
- **LangGraph #2 - Smart Matching (hashtags <-> interests)** → `smart_matching_flow.py`.
  Both graphs' outputs are combined in `feed.py` and cached per-viewer in `post_scores`.
- **Left nav bar: DM / Community / Profile** → rendered in `st.sidebar` on every
  protected page.
- **Profile screen (Instagram-style, incl. Tagged tab)** → `2_Profile.py`.
- **DMs (text + images)** → `3_DM.py` / `backend/dm.py`.
- **Communities: Challenge (progress bar + cheer) vs Discussion (urgent posts), '+' to create** →
  `4_Community.py` / `backend/community.py`.
- **Gemini ChatBot for donation matching by location/type/hashtags** →
  `chatbot/gemini_chatbot.py`, grounded only in real open posts (no hallucinated results).
- **LangGraph #3 - Scam Alert (repeated reports -> notify authority -> admin can
  delete/block)** → `scam_alert_flow.py` + `7_Admin.py`. The graph only *escalates*;
  only a human admin account can actually delete a post or block an account.
- **Auto-delete #food posts after 24h** → `backend/scheduler.py` (APScheduler background
  job, checked every 15 min).
- **Protected blue-tick verification badge** → `backend/verification.py` is the single
  authoritative write path, gated to `account_type='admin'`. No signup or profile-edit
  form anywhere exposes `is_verified` as an editable field, so a user cannot self-grant
  or copy the badge; the frontend (`frontend/utils/badge.py`) always re-reads the flag
  fresh from MySQL rather than trusting any client-side state.

## 4. Notes & honest limitations

- **API keys**: each of the 3 LangGraph flows calls Grok (xAI, OpenAI-SDK-compatible)
  with its *own* key as you requested (`GROK_API_KEY_PRIORITY/MATCHING/SCAM`); the
  chatbot alone uses Gemini. If a Grok call fails (bad key, no network, rate limit),
  each graph fails safe to a deterministic score/behavior rather than crashing the feed.
- **NGO legal/bank verification** here means: the documents are collected and stored,
  and appear in an admin review queue. Actually validating a bank account or a legal
  registration number against a government registry is outside what any code can do
  automatically — that step is intentionally a human admin decision (`7_Admin.py`).
- **Security**: passwords are bcrypt-hashed; the admin panel is gated by `account_type`.
  For a real production deployment you'd want HTTPS, proper session tokens instead of
  Streamlit's in-memory `session_state`, rate limiting, and antivirus/malware scanning
  on uploaded files — none of that is in scope for this build.
- **Scale**: `feed.py` recomputes scores for up to 200 candidate posts per feed load.
  Fine for a prototype/demo; a production version would precompute scores in a queue/cron
  rather than on every page load.
