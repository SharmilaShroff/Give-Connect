"""
LangGraph #1 - PRIORITY RANKING

Goal (per spec): posts should be ranked primarily based on user interests,
and secondarily based on having fewer impressions. Date/recency is completely ignored.
"""
import math
from typing import TypedDict
from langgraph.graph import StateGraph, END
from backend.langgraph_flows.grok_client import get_grok_client, grok_chat


class PriorityState(TypedDict):
    post_id: int
    user_interests: list[str]
    post_hashtags: list[str]
    impressions: int
    interest_score: float
    impression_score: float
    ai_adjustment: float     # multiplier in [0.7, 1.3] applied by the AI reasoning node
    priority_score: float


def compute_interest_score(state: PriorityState) -> PriorityState:
    interests = {i.lower().strip() for i in state["user_interests"] if i.strip()}
    tags = {t.lower().strip() for t in state["post_hashtags"] if t.strip()}
    if not interests or not tags:
        state["interest_score"] = 0.0
        return state
    overlap = interests & tags
    union = interests | tags
    state["interest_score"] = round(len(overlap) / len(union), 4) if union else 0.0
    return state


def compute_impression_score(state: PriorityState) -> PriorityState:
    impressions = state.get("impressions", 0)
    # inverse relationship: fewer impressions => higher score. Smoothed with +1 to avoid div/0.
    score = 1.0 / math.log2(impressions + 2)
    state["impression_score"] = round(score, 4)
    return state


def ai_reasoner(state: PriorityState) -> PriorityState:
    """Consult Grok (dedicated priority key) for a small bounded adjustment multiplier."""
    try:
        client = get_grok_client("GROQ_API_KEY_PRIORITY")
        prompt = (
            f"A post has an interest-match score of {state['interest_score']*100:.0f}% with the user's preferences, "
            f"and has {state['impressions']} impressions so far. "
            "We want to heavily boost posts that match user interests (1st priority), and secondarily boost posts with low impressions. "
            "Reply with ONLY a single number between 0.7 and 1.3 representing a fairness/boost "
            "multiplier for this specific post (1.0 = no adjustment, >1.0 = boost more, <1.0 = boost less)."
        )
        raw = grok_chat(client, "You are a feed-ranking fairness assistant. Reply with only a number.", prompt)
        value = float("".join(c for c in raw if c.isdigit() or c == "." or c == "-") or 1.0)
        state["ai_adjustment"] = min(max(value, 0.7), 1.3)
    except Exception:
        # Fail-safe: if the Grok call errors out (no key, network, bad output), don't break ranking
        state["ai_adjustment"] = 1.0
    return state


def combine(state: PriorityState) -> PriorityState:
    base = 0.8 * state["interest_score"] + 0.2 * state["impression_score"]
    state["priority_score"] = round(base * state["ai_adjustment"], 4)
    return state


def build_priority_graph():
    graph = StateGraph(PriorityState)
    graph.add_node("compute_interest_score", compute_interest_score)
    graph.add_node("compute_impression_score", compute_impression_score)
    graph.add_node("ai_reasoner", ai_reasoner)
    graph.add_node("combine", combine)
    graph.set_entry_point("compute_interest_score")
    graph.add_edge("compute_interest_score", "compute_impression_score")
    graph.add_edge("compute_impression_score", "ai_reasoner")
    graph.add_edge("ai_reasoner", "combine")
    graph.add_edge("combine", END)
    return graph.compile()


_PRIORITY_GRAPH = None


def get_priority_score(post_id: int, user_interests: list[str], post_hashtags: list[str], impressions: int, use_ai: bool = True) -> float:
    """Public entry point used by feed.py. Set use_ai=False to skip the Grok call (cheaper/faster,
    e.g. when re-scoring hundreds of posts on every feed refresh)."""
    global _PRIORITY_GRAPH
    if _PRIORITY_GRAPH is None:
        _PRIORITY_GRAPH = build_priority_graph()
    
    if not use_ai:
        state = {"post_id": post_id, "user_interests": user_interests, "post_hashtags": post_hashtags, "impressions": impressions,
                  "interest_score": 0, "impression_score": 0, "ai_adjustment": 1.0, "priority_score": 0}
        state = compute_interest_score(state)
        state = compute_impression_score(state)
        return combine(state)["priority_score"]
        
    result = _PRIORITY_GRAPH.invoke({
        "post_id": post_id, "user_interests": user_interests, "post_hashtags": post_hashtags, "impressions": impressions,
        "interest_score": 0, "impression_score": 0, "ai_adjustment": 1.0, "priority_score": 0,
    })
    return result["priority_score"]
