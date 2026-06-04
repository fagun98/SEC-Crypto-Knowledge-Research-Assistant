"""Smoke test: python -m chat_agent 'What are broker-dealer custody rules for crypto?'"""

from __future__ import annotations

import json
import sys

from chat_agent.env import load_dotenv_env

load_dotenv_env()

from langgraph_agent import run_chat_turn


def main() -> None:
    query = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "What are the SEC custody requirements for broker-dealers holding crypto assets?"
    )
    print(f"Query: {query}\n")
    answer = run_chat_turn(query)
    print("=== Retrieval debug ===")
    print(json.dumps(answer.retrieval_debug, indent=2))
    print("\n=== HTML answer (first 2000 chars) ===")
    print(answer.html[:2000])
    if answer.error:
        print(f"\nError: {answer.error}")


if __name__ == "__main__":
    main()
