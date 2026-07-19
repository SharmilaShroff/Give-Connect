"""
Donation-finder ChatBot (per spec: uses Gemini API specifically, unlike the 3 LangGraph
flows which use Grok). Helps a user find relevant open posts based on what/where they
want to donate, using hashtags to identify category.
"""
import os
import json
from openai import OpenAI
from database.db import run_query

GROK_MODEL = os.getenv("GROK_MODEL", "grok-beta")

_client = None

def _get_client():
    global _client
    if _client is None:
        # Fallback through the available Grok keys
        api_key = os.getenv("GROK_API_KEY_PRIORITY") or os.getenv("GROK_API_KEY_MATCHING") or os.getenv("GROK_API_KEY_SCAM")
        base_url = os.getenv("GROK_BASE_URL", "https://api.x.ai/v1")
        if not api_key:
            raise RuntimeError("GROK_API_KEY is not set in the environment (.env).")
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _fetch_open_posts(limit: int = 100):
    return run_query(
        """SELECT p.post_id, p.caption, p.location, p.donation_type, u.full_name,
                  GROUP_CONCAT(h.tag SEPARATOR ',') AS hashtags
           FROM posts p
           JOIN users u ON u.user_id = p.user_id
           LEFT JOIN post_hashtags ph ON ph.post_id = p.post_id
           LEFT JOIN hashtags h ON h.hashtag_id = ph.hashtag_id
           WHERE p.is_deleted = FALSE
           GROUP BY p.post_id
           ORDER BY p.created_at DESC
           LIMIT %s""", (limit,))


def find_matching_posts(user_message: str, chat_history: list[dict] = None) -> dict:
    """
    Returns {"reply": str, "matched_post_ids": [int, ...]}
    """
    posts = _fetch_open_posts()
    catalog = [
        {
            "post_id": p["post_id"],
            "caption": (p["caption"] or "")[:200],
            "location": p["location"],
            "donation_type": p["donation_type"],
            "hashtags": p["hashtags"] or "",
        }
        for p in posts
    ]

    try:
        client = _get_client()
        system_instruction = (
            "You are a donation-matching assistant for a community giving platform. "
            "The user will describe what they want to donate (e.g., clothes, food, books) and/or where. "
            "You are given a JSON catalog of currently open posts (each with post_id, caption, location, donation_type, hashtags). "
            "Guidelines:\n"
            "1. Be friendly, empathetic, and conversational in your 'reply'.\n"
            "2. Maintain context across the conversation. Avoid repeating the same greeting or phrase.\n"
            "3. If the user's request is too broad or ambiguous, ask a short clarifying question in your reply.\n"
            "4. Use the catalog to identify category matches. ONLY recommend post_ids that literally appear in the catalog.\n"
            "5. If no posts match perfectly, explain gently and suggest trying a different category or location.\n"
            "You MUST reply in strict JSON format exactly like this: {\"reply\": \"<your conversational response>\", \"matched_post_ids\": [<int>, ...]}\n\n"
            f"Post catalog (JSON):\n{json.dumps(catalog)}"
        )

        messages = [{"role": "system", "content": system_instruction}]
        
        for turn in (chat_history or [])[-6:]:
            # Convert UI roles to OpenAI roles (usually they match, but just to be safe)
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({"role": role, "content": turn["content"]})
            
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=GROK_MODEL,
            messages=messages,
            temperature=0.7
        )
        
        raw = response.choices[0].message.content.strip()
        
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw[4:] if raw.lower().startswith("json") else raw
            
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"reply": raw, "matched_post_ids": []}

    except Exception as e:
        # Fallback to local heuristic matching
        matched_ids = []
        user_words = [w.lower().strip() for w in user_message.split() if len(w) > 2]
        for p in catalog:
            match_score = 0
            for word in user_words:
                if word in p["location"].lower():
                    match_score += 2
                if p["donation_type"] and word in p["donation_type"].lower():
                    match_score += 3
                if word in p["hashtags"].lower():
                    match_score += 2
                if word in p["caption"].lower():
                    match_score += 1
            if match_score > 0:
                matched_ids.append((p["post_id"], match_score))
        
        matched_ids.sort(key=lambda x: x[1], reverse=True)
        top_ids = [x[0] for x in matched_ids[:5]]
        
        if top_ids:
            reply = (
                f"🤖 (Note: AI API is currently unavailable, using local search fallback. Error: {e})\n\n"
                "I found some posts matching your query based on matching hashtags and location details:"
            )
        else:
            reply = (
                f"🤖 (Note: AI API is currently unavailable, using local search fallback. Error: {e})\n\n"
                "I couldn't find any posts matching your description. Try searching for other hashtags (like #food, #clothes, #books)."
            )
        parsed = {"reply": reply, "matched_post_ids": top_ids}

    valid_ids = {p["post_id"] for p in catalog}
    parsed["matched_post_ids"] = [pid for pid in parsed.get("matched_post_ids", []) if pid in valid_ids]
    return parsed
