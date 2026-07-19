"""
LangGraph #2 - SMART MATCHING

Goal (per spec): match user interest/preference against a post's hashtags to decide
whether the post belongs in that user's feed.

Graph:
    literal_overlap_score -> ai_semantic_match -> combine
`literal_overlap_score` does a fast Jaccard-style overlap between the user's stored
interests and the post's hashtags (deterministic, free). `ai_semantic_match` then calls
Grok (its OWN dedicated key, GROK_API_KEY_MATCHING) to catch semantically related but
non-identical matches, e.g. interest "education" should still match hashtag "#books".
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from backend.langgraph_flows.grok_client import get_grok_client, grok_chat


class MatchState(TypedDict):
    user_interests: list[str]
    post_hashtags: list[str]
    literal_score: float
    ai_semantic_score: float
    match_score: float


def literal_overlap_score(state: MatchState) -> MatchState:
    interests = {i.lower().strip() for i in state["user_interests"] if i.strip()}
    tags = {t.lower().strip() for t in state["post_hashtags"] if t.strip()}
    if not interests or not tags:
        state["literal_score"] = 0.0
        return state
    overlap = interests & tags
    union = interests | tags
    state["literal_score"] = round(len(overlap) / len(union), 4) if union else 0.0
    return state


def ai_semantic_match(state: MatchState) -> MatchState:
    if state["literal_score"] >= 0.5:
        # already a strong literal match, skip the extra API call to save cost
        state["ai_semantic_score"] = state["literal_score"]
        return state
    try:
        client = get_grok_client("GROQ_API_KEY_MATCHING")
        prompt = (
            f"User interests: {', '.join(state['user_interests']) or 'none'}.\n"
            f"Post hashtags: {', '.join(state['post_hashtags']) or 'none'}.\n"
            "On a scale of 0.0 to 1.0, how semantically relevant is this post to this user's "
            "interests, even if the wording differs (e.g. 'education' relates to '#books', "
            "'#food' relates to 'hunger relief')? Reply with ONLY the number."
        )
        raw = grok_chat(client, "You are a semantic relevance scorer. Reply with only a number 0.0-1.0.", prompt)
        value = float("".join(c for c in raw if c.isdigit() or c == "." ) or 0.0)
        state["ai_semantic_score"] = min(max(value, 0.0), 1.0)
    except Exception:
        state["ai_semantic_score"] = state["literal_score"]
    return state


def combine(state: MatchState) -> MatchState:
    state["match_score"] = round(0.4 * state["literal_score"] + 0.6 * state["ai_semantic_score"], 4)
    return state


def build_matching_graph():
    graph = StateGraph(MatchState)
    graph.add_node("literal_overlap_score", literal_overlap_score)
    graph.add_node("ai_semantic_match", ai_semantic_match)
    graph.add_node("combine", combine)
    graph.set_entry_point("literal_overlap_score")
    graph.add_edge("literal_overlap_score", "ai_semantic_match")
    graph.add_edge("ai_semantic_match", "combine")
    graph.add_edge("combine", END)
    return graph.compile()


_MATCH_GRAPH = None


def get_match_score(user_interests: list[str], post_hashtags: list[str], use_ai: bool = True) -> float:
    global _MATCH_GRAPH
    if _MATCH_GRAPH is None:
        _MATCH_GRAPH = build_matching_graph()
    if not use_ai:
        state = {"user_interests": user_interests, "post_hashtags": post_hashtags,
                  "literal_score": 0, "ai_semantic_score": 0, "match_score": 0}
        state = literal_overlap_score(state)
        state["ai_semantic_score"] = state["literal_score"]
        return combine(state)["match_score"]
    result = _MATCH_GRAPH.invoke({
        "user_interests": user_interests, "post_hashtags": post_hashtags,
        "literal_score": 0, "ai_semantic_score": 0, "match_score": 0,
    })
    return result["match_score"]
