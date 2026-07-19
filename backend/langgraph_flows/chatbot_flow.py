"""
LangGraph #4 - CHATBOT ORCHESTRATION

Goal: Intelligent assistant for platform navigation.
Workflow: detect_intent -> extract_entities -> execute_action -> generate_reply
"""
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from backend.langgraph_flows.grok_client import get_grok_client, GROQ_MODEL
from backend import search as search_backend
from backend import profile as profile_backend
from backend.posts import get_post

class ChatbotState(TypedDict):
    user_message: str
    chat_history: list[dict]
    detected_intent: str
    extracted_entities: dict
    action_result: dict
    navigation_action: str
    navigation_params: dict
    final_reply: str


def _call_grok_json(client, system_prompt, user_message, chat_history=None):
    messages = [{"role": "system", "content": system_prompt}]
    for turn in (chat_history or [])[-4:]:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})
    
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.1
    )
    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def detect_intent(state: ChatbotState) -> ChatbotState:
    client = get_grok_client("GROQ_API_KEY_CHATBOT")
    sys_prompt = (
        "Classify the user's intent into exactly ONE of the following:\n"
        "- location_search (asking for posts in/from a city or place)\n"
        "- hashtag_search (asking for topics like #food, #ai)\n"
        "- user_search (asking to find or open a user profile)\n"
        "- general_search (asking for generic topics like 'startup posts')\n"
        "- conversation (general chat, help, or unknown)\n"
        "Return ONLY JSON format: {\"intent\": \"<intent_name>\"}"
    )
    result = _call_grok_json(client, sys_prompt, state["user_message"], state["chat_history"])
    state["detected_intent"] = result.get("intent", "conversation")
    return state


def extract_entities(state: ChatbotState) -> ChatbotState:
    intent = state["detected_intent"]
    if intent == "conversation":
        state["extracted_entities"] = {}
        return state
        
    client = get_grok_client("GROQ_API_KEY_CHATBOT")
    sys_prompt = (
        f"The user's intent is {intent}. Extract the relevant entity based on this intent.\n"
        "Return ONLY JSON format with one of the following keys depending on intent:\n"
        "- 'location': string (if location_search)\n"
        "- 'hashtag': string (if hashtag_search, omit the # symbol)\n"
        "- 'username': string (if user_search, omit the @ symbol)\n"
        "- 'keywords': string (if general_search)\n"
    )
    result = _call_grok_json(client, sys_prompt, state["user_message"], state["chat_history"])
    state["extracted_entities"] = result
    return state


def execute_action(state: ChatbotState) -> ChatbotState:
    intent = state["detected_intent"]
    entities = state["extracted_entities"]
    
    action = None
    params = {}
    result_data = {"count": 0, "matched_post_ids": []}
    
    try:
        if intent == "location_search" and "location" in entities:
            loc = entities["location"]
            # Even if exact location not found in location table, we can just search_posts_by_location directly
            # Or pass it to UI to render
            posts = search_backend.search_posts_by_location(loc)
            result_data["count"] = len(posts)
            result_data["matched_post_ids"] = [p["post_id"] for p in posts[:5]]
            action = "feed_filter"
            params = {"filter_type": "location", "query": loc}
            
        elif intent == "hashtag_search" and "hashtag" in entities:
            tag = entities["hashtag"].replace("#", "")
            posts = search_backend.search_posts_by_hashtag(tag)
            result_data["count"] = len(posts)
            result_data["matched_post_ids"] = [p["post_id"] for p in posts[:5]]
            action = "feed_filter"
            params = {"filter_type": "hashtag", "query": tag}
            
        elif intent == "user_search" and "username" in entities:
            users = profile_backend.search_users(entities["username"])
            if users:
                target_user = users[0]["user_id"]
                result_data["count"] = 1
                result_data["matched_user_id"] = target_user
                action = "profile"
                params = {"user_id": target_user}
            else:
                result_data["count"] = 0
                
        elif intent == "general_search":
            # For general search, we just pass to feed global search
            action = "feed_filter"
            params = {"filter_type": "general", "query": entities.get("keywords", state["user_message"])}
            result_data["count"] = -1 # indicates delegated to global search
            
    except Exception as e:
        result_data["error"] = str(e)
        
    state["action_result"] = result_data
    state["navigation_action"] = action
    state["navigation_params"] = params
    return state


def generate_reply(state: ChatbotState) -> ChatbotState:
    client = get_grok_client("GROQ_API_KEY_CHATBOT")
    intent = state["detected_intent"]
    nav_action = state["navigation_action"]
    res = state.get("action_result", {})
    count = res.get("count", 0)
    
    sys_prompt = (
        "You are a professional, helpful assistant for a social donation platform.\n"
        "Guidelines:\n"
        "- Be friendly, concise, and natural.\n"
        "- Do not explain your technical intent detection process.\n"
    )
    
    if nav_action == "feed_filter":
        if count == 0:
            sys_prompt += f"You tried to search for {state['extracted_entities']}, but found 0 results. Apologize and suggest trying a different query."
        elif count == -1:
            sys_prompt += f"You are forwarding their general search to the global feed. Tell them you are taking them to the search results."
        else:
            sys_prompt += f"You found {count} results. Tell them you are taking them to the filtered feed right now."
    elif nav_action == "profile":
        sys_prompt += f"You found the user. Tell them you are opening the profile of {res.get('matched_user_id')} now."
    elif intent == "user_search" and not nav_action:
        sys_prompt += f"You searched for the user {state['extracted_entities'].get('username')} but couldn't find them."
    else:
        sys_prompt += "Engage in helpful conversation. If they ask how to use the app, explain they can search for locations, hashtags, or users."
        
    messages = [{"role": "system", "content": sys_prompt}]
    for turn in (state.get("chat_history") or [])[-4:]:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": state["user_message"]})
    
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.5
        )
        state["final_reply"] = resp.choices[0].message.content.strip()
    except Exception as e:
        state["final_reply"] = f"Oops, I ran into a connection issue: {e}"
        
    return state


def build_chatbot_graph():
    graph = StateGraph(ChatbotState)
    graph.add_node("detect_intent", detect_intent)
    graph.add_node("extract_entities", extract_entities)
    graph.add_node("execute_action", execute_action)
    graph.add_node("generate_reply", generate_reply)
    
    graph.set_entry_point("detect_intent")
    graph.add_edge("detect_intent", "extract_entities")
    graph.add_edge("extract_entities", "execute_action")
    graph.add_edge("execute_action", "generate_reply")
    graph.add_edge("generate_reply", END)
    return graph.compile()


_CHATBOT_GRAPH = None

def run_chatbot_flow(user_message: str, chat_history: list = None) -> dict:
    global _CHATBOT_GRAPH
    if _CHATBOT_GRAPH is None:
        _CHATBOT_GRAPH = build_chatbot_graph()
        
    result = _CHATBOT_GRAPH.invoke({
        "user_message": user_message,
        "chat_history": chat_history or [],
        "detected_intent": "",
        "extracted_entities": {},
        "action_result": {},
        "navigation_action": "",
        "navigation_params": {},
        "final_reply": ""
    })
    
    # Return formatted response consistent with UI expectations, extending it with navigation
    return {
        "reply": result["final_reply"],
        "matched_post_ids": result.get("action_result", {}).get("matched_post_ids", []),
        "navigation_action": result.get("navigation_action"),
        "navigation_params": result.get("navigation_params")
    }
