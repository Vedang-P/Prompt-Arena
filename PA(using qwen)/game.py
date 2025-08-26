from typing import Tuple, List, Dict

from config import DEFAULT_TOP_K
from db import query_db
from llm import ask_llm


def play_game() -> None:

	print("Prompt Arena - Mystery at MIST University")
	print("Type 'exit' or 'quit' to end. Ask anything about the case.")
	while True:
		try:
			question = input("\nYou> ").strip()
		except (EOFError, KeyboardInterrupt):
			print("\nGoodbye!")
			break

		if not question:
			continue
		if question.lower() in {"exit", "quit"}:
			print("Goodbye!")
			break

		context_text, sources = query_db(question, top_k=DEFAULT_TOP_K)
		answer = ask_llm(question, context_text)

		print("\nGM>")
		print(answer or "(No answer)")

		if sources:
			print("\n[Retrieved clues]")
			for s in sources:
				cid = s.get("id", "?")
				content = s.get("content", "").strip()
				preview = content[:120] + ("…" if len(content) > 120 else "")
				print(f"- #{cid}: {preview}")


