from typing import TypedDict

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from Agents.prompt_congif import PROMPT_TEMPLATES

model = ChatOllama(model="llama3.2:3b-instruct-q4_K_M", streaming=True)

class GraphState(TypedDict):
    question: str
    language: str
    response: str
    context: str
    prompt_key: str

conversation_states = {}

prompt_fermin_response = ChatPromptTemplate.from_template(PROMPT_TEMPLATES["Fermin"])
response_fermin_chain = prompt_fermin_response | model

prompt_russian_response = ChatPromptTemplate.from_template(PROMPT_TEMPLATES["Novia Rusa"])
response_russian_chain = prompt_russian_response | model


# Nodo que selecciona qué template usar según el prompt_key
def seleccionar_template_node(state: GraphState) -> GraphState:
    prompt_key = state.get("prompt_key", "Fermin")
    
    if prompt_key == "Fermin":
        selected_chain = response_fermin_chain
    elif prompt_key == "Novia Rusa":
        selected_chain = response_russian_chain
    else:
        raise ValueError(f"Prompt key no reconocido: {prompt_key}")

    resp = selected_chain.invoke({
        "question": state["question"],
        "language": state["language"],
        "context": state["context"]
    }).content
    print("Respuesta", resp)

    return {
        "question": state["question"],
        "language": state["language"],
        "response": resp,
        "context": state["context"] + "\n" + resp,
        "prompt_key": prompt_key
    }

# Crear grafo principal
graph = StateGraph(GraphState)

# Nodo único de selección + respuesta
graph.add_node("seleccionar_template", seleccionar_template_node)

# Configurar flujo del grafo
graph.set_entry_point("seleccionar_template")
graph.add_edge("seleccionar_template", END)

# Compilar grafo
app = graph.compile(checkpointer=InMemorySaver())

def generate_conversation_stream(message: str, thread_id: str, prompt_key: str, language: str):
    config = {"configurable": {"thread_id": thread_id}}

    state = conversation_states.get(thread_id, {
        "question": message,
        "language": language,
        "response": "",
        "context": "",
        "prompt_key": prompt_key
    })
    state["question"] = message

    responses = []
    for step in app.stream(state, config=config, stream_mode="values"):
        responses.append(step)
    if responses:
        conversation_states[thread_id] = responses[-1]
        return responses[-1]["response"]
    return "No response"
