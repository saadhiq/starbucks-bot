import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence
import operator

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient


import gspread
from google.oauth2.service_account import Credentials




load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile")

@tool
def create_order(drink: str, size: str, milk: str, temperature: str) -> str:
    """Places a Starbucks order once drink, size, milk and temperature are collected."""
    return f"Order created: {size} {drink} with {milk} milk and {temperature} temperature."

# Bind the tool to the LLM
llm_with_tools = llm.bind_tools([create_order])


@tool
def get_menu(query: str) -> str:
    """Gets menu information including drinks, sizes and prices from the Starbucks menu sheet.
    Use this when the user asks about menu items, prices, or available options."""
    
    # Read from environment variable instead of file
    creds_json = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    
    client = gspread.authorize(creds)
    
    # Replace with your actual Google Sheet ID
    sheet = client.open_by_key("1ppPRM0kWpfStCNdnNhj3twBJX3lS7n_vk1VEtVtKcks").sheet1
    data = sheet.get_all_records()
    
    # Convert to readable text for LLM
    menu_text = "Starbucks Menu:\n"
    for row in data:
        menu_text += f"- {row['Drink']} ({row['Size']}): {row['Price']} | Milk options: {row['Milk Options']}\n"
    
    return menu_text


def agent_node(state):
    system = SystemMessage(content= """ You are a friendly Starbucks barista.
    Your job is to collect the following details from the customer:
    - drink (e.g. latte, cappuccino, espresso)
    - size (small, medium, large)
    - milk (whole, oat, almond, soy)
    - temperature (hot, iced)
    
    Ask for missing details one at a time, naturally.
    Only call create_order when you have ALL four details. """)

    response = llm_with_tools.invoke([system] + list(state["messages"]))

    return {"messages":[response]}


# Step 1 — Define State
class OrderState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# Step 2 — Define tool node
tool_node = ToolNode([create_order, get_menu])

# Step 3 — Define routing logic
def should_continue(state):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# Step 4 — Build the graph
graph = StateGraph(OrderState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")

# app = graph.compile()
# print("Graph compiled successfully!")

# print("Agent node ready")

# MongoDB memory
# client = MongoClient(os.getenv("MONGODB_URI"))

client = MongoClient(
    os.getenv("MONGODB_URI"),
    tls=True,
    tlsAllowInvalidCertificates=True
)


checkpointer = MongoDBSaver(client)
app = graph.compile(checkpointer=checkpointer)

# print("Welcome to Starbucks! Type 'quit' to exit.\n")

# conversation_history = []

# while True:
#     user_input = input("You: ")
    
#     if user_input.lower() == "quit":
#         break
    
#     conversation_history.append(HumanMessage(content=user_input))
    
#     result = app.invoke({"messages": conversation_history})
    
#     conversation_history = list(result["messages"])
    
#     last_message = result["messages"][-1]
#     print(f"Barista: {last_message.content}\n")

print("Agent ready")
