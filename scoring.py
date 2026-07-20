"""
scoring.py

AI-based newsworthiness scorer and summarizer for pipeline items.

Uses an OpenAI model to rate each item 1–5 for newsworthiness AND generate a
concise plain-English summary — both in a single API call to keep cost and
latency down.

Degrades gracefully: if OPENAI_API_KEY is unset or the call fails for any
reason, it returns a null score and empty text instead of raising, so the
pipeline and web UI keep working without an API key.

Scale:
  5 — Break immediately / investigate urgently
      (public safety, major crimes, disasters, systemic scandals)
  4 — High public interest
      (major legal action, corporate misconduct, significant policy impact)
  3 — Moderate interest
      (regulation, notable tech / business / political developments)
  2 — Lower interest
      (personnel changes, scheduled events, routine reports)
  1 — Routine / administrative
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_MODEL = "gpt-4o-mini"

_PROMPT = """You are a research assistant for a journalist monitoring news sources across any beat.

Given one news item, do two things:

1. Rate its newsworthiness on a scale of 1–5:
     5 = Break immediately / investigate urgently (public safety, major crime, disaster, systemic scandal)
     4 = High public interest (major legal action, corporate misconduct, significant policy impact)
     3 = Moderate interest (regulation, notable tech / business / political development)
     2 = Lower interest (personnel change, scheduled event, routine report)
     1 = Routine / administrative

2. Write a one- to two-sentence, plain-English summary of what happened and why it matters.

Title: {title}
Summary: {summary}

Respond with JSON only — no other text:
{{"score": <integer 1-5>, "reason": "<one sentence justifying the score>", "summary": "<1-2 sentence summary>"}}"""


_client = None


def _get_client():
    """Return a cached OpenAI client, or None if no API key is configured."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        _client = OpenAI(api_key=api_key)
    return _client


def analyze_item(title: str, summary: str = "") -> dict:
    """
    Ask the model to score and summarize one item in a single call.

    Returns {"score": int|None, "reason": str, "summary": str}.
    Never raises: returns score=None with empty strings when the API key is
    absent or the call fails for any reason.
    """
    client = _get_client()
    if client is None:
        return {"score": None, "reason": "", "summary": ""}

    try:
        resp = client.chat.completions.create(
            model=_MODEL,
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": _PROMPT.format(
                title=title, summary=summary or title
            )}],
        )
        result = json.loads(resp.choices[0].message.content)
        score = result.get("score")
        return {
            "score":   int(score) if score is not None else None,
            "reason":  result.get("reason", ""),
            "summary": result.get("summary", ""),
        }
    except Exception as e:
        print(f"    ! analysis failed: {e}")
        return {"score": None, "reason": "", "summary": ""}
