import json
from typing import TypedDict

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from Agents.prompt_congif import PROMPT_TEMPLATES, TEMPLATE_LANGUAGE_DETECT

model = ChatOllama(model="llama3.2:3b-instruct-q4_K_M", streaming=True)

class GraphState(TypedDict):
    question: str
    language: str
    response: str
    context: str

conversation_states = {}

def build_graph(template_str: str):
    prompt_detect = ChatPromptTemplate.from_template(TEMPLATE_LANGUAGE_DETECT)
    detect_chain = prompt_detect | model

    prompt_response = ChatPromptTemplate.from_template(template_str)
    response_chain = prompt_response | model

    def detect_language_node(state: GraphState) -> GraphState:
        try:
            resp = detect_chain.invoke({"question": state["question"]}).content
            lang = json.loads(resp)["language"]
            print("Idioma", lang)
            return {
                "question": state["question"],
                "language": lang,
                "response": "",
                "context": state["context"]
            }
        except Exception as e:
            print(f"[ERROR] No se pudo detectar el idioma. Respuesta recibida: {resp}")
            return {
                    "question": state["question"],
                    "language": "español",
                    "response": "",
                    "context": state["context"]
                }

    def generate_response_node(state: GraphState) -> GraphState:
        resp = response_chain.invoke({
            "question": state["question"],
            "language": state["language"],
            "context": state["context"]
        }).content
        print("Respuesta", resp)
        return {
            "question": state["question"],
            "language": state["language"],
            "response": resp,
            "context": state["context"] + "\n" + resp
        }

    graph = StateGraph(GraphState)
    graph.add_node("detectar_idioma", detect_language_node)
    graph.add_node("responder", generate_response_node)
    graph.set_entry_point("detectar_idioma")
    graph.add_edge("detectar_idioma", "responder")
    graph.add_edge("responder", END)

    return graph.compile(checkpointer=InMemorySaver())

def generate_conversation_stream(message: str, thread_id: str, prompt_key: str):
    template_str = PROMPT_TEMPLATES[prompt_key]
    app = build_graph(template_str)
    config = {"configurable": {"thread_id": thread_id}}

    state = conversation_states.get(thread_id, {
        "question": message,
        "language": "",
        "response": "",
        "context": ""
    })
    state["question"] = message

    responses = []
    for step in app.stream(state, config=config, stream_mode="values"):
        responses.append(step)
    if responses:
        conversation_states[thread_id] = responses[-1]
        return responses[-1]["response"]
    return "No response"
