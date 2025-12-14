# Backend Architecture & LangChain Integration

This document describes the backend architecture of the Multi-Agent Chat application, focusing on the FastAPI implementation and LangGraph orchestration.

## Overview

The backend is built using **FastAPI** and utilizes **LangGraph** (built on top of LangChain) to orchestrate a multi-agent discussion panel. The system allows users to ask questions to a configurable panel of AI agents (panelists) and receive a consolidated summary from a moderator agent.

## Core Components

### 1. FastAPI Application (`main.py`)

The entry point of the backend is a FastAPI application that exposes the following endpoints:

*   **`POST /ask`**: The primary endpoint for initiating a discussion.
    *   **Input**: `AskRequest` containing:
        *   `thread_id`: Unique identifier for the conversation thread.
        *   `question`: The user's query.
        *   `attachments`: Optional list of image URLs.
        *   `panelists`: Configuration for the agents (ID, name, provider, model).
        *   `provider_keys`: API keys for the different LLM providers.
    *   **Process**:
        1.  Constructs the initial state with the user's question (and attachments if any).
        2.  Invokes the `panel_graph` with the state and configuration.
        3.  Returns the conversation summary and individual panelist responses.
    *   **Output**: `AskResponse` (thread ID, summary, individual responses).

*   **`POST /providers/{provider}/models`**: Helper endpoint to fetch available models.
    *   **Input**: Provider name (path param) and API key (body).
    *   **Output**: List of available models for the specified provider.

### 2. LangGraph Orchestration (`panel_graph.py`)

The core logic resides in a `StateGraph` which defines the flow of the conversation.

#### State (`PanelState`)
The graph maintains a shared state containing:
*   `messages`: A list of messages (Human, AI, System) representing the conversation history.
*   `panel_responses`: A dictionary mapping panelist names to their responses.
*   `summary`: The final consolidated answer from the moderator.

#### Graph Nodes

1.  **`panelists` Node**:
    *   **Function**: `panelist_sequence_node`
    *   **Behavior**: Iterates through the configured list of panelists.
    *   **Execution**: Each panelist is invoked sequentially. They receive the current conversation history and generate a response.
    *   **Update**: The response is appended to the `messages` history and stored in `panel_responses`.

2.  **`moderator` Node**:
    *   **Function**: `moderator_node`
    *   **Behavior**: Acts as the synthesizer.
    *   **Execution**: Receives all responses from the panelists. It uses a specific prompt to consolidate the answers, highlighting agreements and disagreements.
    *   **Model**: Currently uses `gpt-4o` as the fixed moderator model.
    *   **Update**: Generates the final `summary`.

#### Workflow
The graph follows a linear flow:
`START` -> `panelists` -> `moderator` -> `END`

#### Providers & Clients
The system supports multiple LLM providers via a factory pattern (`PROVIDER_FACTORIES`):
*   **OpenAI**: Uses `ChatOpenAI`.
*   **Gemini**: Uses `ChatGoogleGenerativeAI`.
*   **Claude**: Uses `ChatAnthropic`.
*   **Grok**: Uses a custom `GrokChatRunner` (via `httpx`).

### 3. Checkpointing
The graph supports persistence to allow continuing conversations (though the current `/ask` endpoint is stateless per request, the infrastructure exists).
*   **Postgres**: Tries to use `PostgresSaver` if a connection string is available.
*   **Memory**: Falls back to `MemorySaver` for local/ephemeral usage.
