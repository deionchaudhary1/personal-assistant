"""Prompt templates for Ollama calls."""

PARSE_SYSTEM = (
    "You are a task-extraction assistant. The user gives messy, multi-line todo "
    "text. Extract a list of discrete tasks. Respond ONLY with JSON of the form "
    '{"drafts": [{"title": str, "description": str|null, "priority": '
    '"high"|"medium"|"low", "estimated_minutes": int, "due_date": '
    '"YYYY-MM-DD"|null}]}. '
    "Infer priority from urgency words (asap/urgent/important => high; someday/"
    "maybe => low; otherwise medium). Estimate a reasonable duration in minutes "
    "(default 30). Only set due_date if a concrete date is stated; otherwise null. "
    "Do not invent tasks that are not present."
)


def parse_user_prompt(text: str) -> str:
    from datetime import date

    today = date.today()
    return (
        f"Today's date is {today.isoformat()} ({today.strftime('%A')}). "
        "Resolve relative deadlines like 'by friday' to the next such date "
        "on or after today; never produce a past date.\n\n"
        f"Todo text:\n{text}\n\nReturn the JSON now."
    )


ESTIMATE_SYSTEM = (
    "You estimate how many minutes a single task will take. Respond ONLY with "
    'JSON of the form {"estimated_minutes": int}. Be realistic; typical tasks '
    "are 15-120 minutes."
)


def estimate_user_prompt(title: str, description: str) -> str:
    desc = description or ""
    return f"Task title: {title}\nDescription: {desc}\n\nReturn the JSON now."


QA_SYSTEM = (
    "You answer the user's question using ONLY the provided context snippets from "
    "their documents. If the answer is not in the context, say you don't have "
    "that information. Be concise."
)


def qa_user_prompt(question: str, context: str) -> str:
    return (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above."
    )
