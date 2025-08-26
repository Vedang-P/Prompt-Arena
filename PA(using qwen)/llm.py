import json
import requests
from typing import List, Dict

from config import get_ollama_host, get_model_name


SYSTEM_PROMPT = (
	"You are the Game Master for a mystery set at MIST University. "
	"Use the provided context clues faithfully. If unsure, say what is unknown. "
	"Help the player reason step-by-step but keep answers concise and actionable."
)


def _build_messages(question: str, context_text: str) -> List[Dict[str, str]]:

	context_section = (
		"Context (retrieved clues):\n" + (context_text.strip() or "<no context found>")
	)
	user_prompt = (
		f"{context_section}\n\n"
		"Player question: "
		f"{question.strip()}\n\n"
		"Instructions: Answer using only the context when possible. "
		"Cite specific clues if relevant. If context seems insufficient, say what to check next."
	)
	return [
		{"role": "system", "content": SYSTEM_PROMPT},
		{"role": "user", "content": user_prompt},
	]


def ask_llm(question: str, context_text: str) -> str:

	url = f"{get_ollama_host().rstrip('/')}/api/chat"
	body = {
		"model": get_model_name(),
		"messages": _build_messages(question, context_text),
		"stream": False,
	}
	resp = requests.post(url, data=json.dumps(body), headers={"Content-Type": "application/json"}, timeout=120)
	resp.raise_for_status()
	data = resp.json()
	# Ollama chat returns either {message: {content}} or {choices: [{message: {content}}]} depending on version
	if "message" in data and isinstance(data["message"], dict):
		return data["message"].get("content", "")
	choices = data.get("choices") or []
	if choices and isinstance(choices, list):
		msg = choices[0].get("message", {})
		return msg.get("content","")
	return ""


