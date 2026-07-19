"""
LangGraph #3 - SCAM ALERT

Goal (per spec): if a post is reported as scam multiple times, notify the
website authority/management (populate admin_alerts), who can then delete
the post or block the account. This graph never deletes/blocks anything itself -
it only escalates; only a human admin (backend/admin.py) can take that action,
matching the "management will have access to delete or block" requirement.

Graph:
    count_scam_reports -> threshold_gate -> ai_scam_reasoning -> raise_alert
Uses its own Grok key: GROK_API_KEY_SCAM.
"""
import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from database.db import run_query, run_update
from backend.langgraph_flows.grok_client import get_grok_client, grok_chat

SCAM_REPORT_THRESHOLD = int(os.getenv("SCAM_REPORT_THRESHOLD", "3"))


class ScamState(TypedDict):
    post_id: int
    report_count: int
    should_escalate: bool
    ai_reasoning: str
    alert_created: bool


def count_scam_reports(state: ScamState) -> ScamState:
    row = run_query(
        "SELECT COUNT(*) AS c FROM reports WHERE post_id=%s AND reason='scam'",
        (state["post_id"],), fetchone=True,
    )
    state["report_count"] = row["c"] if row else 0
    return state


def threshold_gate(state: ScamState) -> ScamState:
    state["should_escalate"] = state["report_count"] >= SCAM_REPORT_THRESHOLD
    return state


def ai_scam_reasoning(state: ScamState) -> ScamState:
    if not state["should_escalate"]:
        state["ai_reasoning"] = "Below report threshold; no escalation."
        return state
    post = run_query("SELECT caption, donation_type, location FROM posts WHERE post_id=%s",
                      (state["post_id"],), fetchone=True) or {}
    try:
        client = get_grok_client("GROQ_API_KEY_SCAM")
        prompt = (
            f"This post has been reported as a scam {state['report_count']} times by different users.\n"
            f"Caption: {post.get('caption','')}\n"
            f"Claimed donation type: {post.get('donation_type','')}\n"
            f"Location: {post.get('location','')}\n"
            "In 2-3 sentences, assess whether this looks like a likely scam/fraudulent donation "
            "request and what red flags (if any) stand out, for a human moderator to review."
        )
        state["ai_reasoning"] = grok_chat(
            client, "You are a trust & safety assistant flagging potential donation scams for human review.",
            prompt,
        )
    except Exception as e:
        state["ai_reasoning"] = f"(AI reasoning unavailable: {e}) Escalated purely on report count."
    return state


def raise_alert(state: ScamState) -> ScamState:
    if not state["should_escalate"]:
        state["alert_created"] = False
        return state
    post = run_query("SELECT user_id FROM posts WHERE post_id=%s", (state["post_id"],), fetchone=True)
    if not post:
        state["alert_created"] = False
        return state
    # avoid duplicate open alerts for the same post
    existing = run_query(
        "SELECT alert_id FROM admin_alerts WHERE post_id=%s AND status='open'",
        (state["post_id"],), fetchone=True,
    )
    if existing:
        run_update(
            "UPDATE admin_alerts SET report_count=%s, ai_reasoning=%s WHERE alert_id=%s",
            (state["report_count"], state["ai_reasoning"], existing["alert_id"]),
        )
    else:
        run_update(
            """INSERT INTO admin_alerts (user_id, post_id, alert_type, ai_reasoning, report_count, status)
               VALUES (%s,%s,'scam_suspected',%s,%s,'open')""",
            (post["user_id"], state["post_id"], state["ai_reasoning"], state["report_count"]),
        )
    run_update("UPDATE users SET is_flagged=TRUE WHERE user_id=%s", (post["user_id"],))
    state["alert_created"] = True
    return state


def build_scam_graph():
    graph = StateGraph(ScamState)
    graph.add_node("count_scam_reports", count_scam_reports)
    graph.add_node("threshold_gate", threshold_gate)
    graph.add_node("ai_scam_reasoning", ai_scam_reasoning)
    graph.add_node("raise_alert", raise_alert)
    graph.set_entry_point("count_scam_reports")
    graph.add_edge("count_scam_reports", "threshold_gate")
    graph.add_edge("threshold_gate", "ai_scam_reasoning")
    graph.add_edge("ai_scam_reasoning", "raise_alert")
    graph.add_edge("raise_alert", END)
    return graph.compile()


_SCAM_GRAPH = None


def run_scam_check(post_id: int) -> dict:
    """Call this right after every `report_post(..., reason='scam')` (see backend/posts.py usage in frontend)."""
    global _SCAM_GRAPH
    if _SCAM_GRAPH is None:
        _SCAM_GRAPH = build_scam_graph()
    return _SCAM_GRAPH.invoke({
        "post_id": post_id, "report_count": 0, "should_escalate": False,
        "ai_reasoning": "", "alert_created": False,
    })
