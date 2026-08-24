from dotenv import load_dotenv
import json
from typing import cast
import anthropic
from anthropic.types import ContentBlockParam, MessageParam, ToolParam

from firebase_watcher.pull_metrics import read_ops

load_dotenv()

TOOLS: list[ToolParam] = [
    {
        "name": "read_ops",
        "description": (
            "Fetch Firestore document read counts for the Squish app from Cloud "
            "Monitoring. Returns a mapping of operation type (QUERY, LOOKUP, "
            "NOT_FOUND) to timestamped counts. Use a large bucket_seconds for an "
            "overview and a small one to zoom into a specific spike."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "hours": {
                    "type": "integer",
                    "description": "How far back to look, in hours. Max 720.",
                },
                "bucket_seconds": {
                    "type": "integer",
                    "description": "Bucket size: 3600 for hourly, 60 for per-minute.",
                },
            },
            "required": [],
        },
    }
]



client = anthropic.Anthropic()

def dispatch(name: str, args: dict):
    if name != "read_ops":
       raise ValueError(f"unknown tool: {name}")

    data = read_ops(**args)

    out = {}
    for op, points in data.items():
       out[op] = {}
       for ts, count in points.items():
          if count:
             out[op][ts.isoformat()] = count
    return out


def run(question: str, max_turns: int = 8) -> str:
   messages: list[MessageParam] = [{"role": "user", "content": question}]

   for _ in range(max_turns):
      resp = client.messages.create(
         model="claude-sonnet-5",
         max_tokens=4000,
         tools=TOOLS,
         messages=messages,
      )
      messages.append({
         "role": "assistant",
         "content": cast(list[ContentBlockParam], resp.content),
      })

      if resp.stop_reason != "tool_use":
         return "".join(b.text for b in resp.content if b.type == "text")

      results = []
      for block in resp.content:
         if block.type != "tool_use":
            continue
         print(f" -> {block.name}({block.input})")
         try:
            out = dispatch(block.name, block.input)
            results.append({
               "type": "tool_result",
               "tool_use_id": block.id,
               "content": json.dumps(out)
            })
         except Exception as e:
            results.append({
               "type": "tool_result",
               "tool_use_id": block.id,
               "content": f"{type(e).__name__}: {e}",
               "is_error": True
            })

      messages.append({"role": "user", "content": results})

   return "Hit the turn limit without a final answer.."

print(run("What's driving Firestore reads in the last 24 hours? "
          "Start with an overview, then zoom into the busiest period."))