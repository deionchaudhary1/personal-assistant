"""Prompt templates for Ollama calls."""

PARSE_SYSTEM = (
    "You are a task-extraction assistant. The user gives messy, multi-line todo "
    "text. Extract a list of discrete tasks. Respond ONLY with JSON of the form "
    '{"drafts": [{"title": str, "description": str|null, "priority": '
    '"high"|"medium"|"low", "due_date": '
    '"YYYY-MM-DD"|null}]}. '
    "Infer priority from urgency words (asap/urgent/important => high; someday/"
    "maybe => low; otherwise medium). Only set due_date if a concrete date is "
    "stated; otherwise null. Do not invent tasks that are not present."
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
