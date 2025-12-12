"""FastAPI application exposing the /ask endpoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from panel_graph import panel_graph

app = FastAPI(title="AI Discussion Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    thread_id: str
    question: str
    attachments: list[str] | None = None


class AskResponse(BaseModel):
    thread_id: str
    summary: str
    panel_responses: dict[str, str]


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    attachments = req.attachments or []
    attachment_md = "\n".join(
        f"![user attachment {idx + 1}]({url})" for idx, url in enumerate(attachments)
    )
    question_text = req.question.strip() or "See attached images."
    if attachment_md:
        question_text = f"{question_text}\n\nAttached images:\n{attachment_md}"

    state = {
        "messages": [HumanMessage(content=question_text)],
        "panel_responses": {},
        "summary": None,
    }

    config = {"configurable": {"thread_id": req.thread_id}}
    result = panel_graph.invoke(state, config=config)

    return AskResponse(
        thread_id=req.thread_id,
        summary=result["summary"],
        panel_responses=result["panel_responses"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
