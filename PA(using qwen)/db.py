import os
import sqlite3
import re
from typing import List, Dict, Tuple

from config import get_sqlite_path


def _normalize_text(text: str) -> str:

	return re.sub(r"\s+", " ", text or "").strip()


def _infer_old_clue_to_content(row: Tuple) -> str:

	# Old schema appears to include columns: character, user_message, clue_text
	# We combine them into a single content field for the new schema
	character, user_message, clue_text = row
	parts = []
	if character:
		parts.append(f"Character: {character}")
	if user_message:
		parts.append(f"Message: {user_message}")
	if clue_text:
		parts.append(f"Clue: {clue_text}")
	return _normalize_text(" | ".join(parts))


def ensure_db() -> None:

	story_db_path = get_sqlite_path()
	if os.path.exists(story_db_path):
		return

	legacy_path = os.path.abspath("prompt_arena_story.db")
	if not os.path.exists(legacy_path):
		# Nothing to do; we will create an empty DB with correct schema
		_conn = sqlite3.connect(story_db_path)
		with _conn:
			_conn.execute("CREATE TABLE IF NOT EXISTS clues (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)")
		_conn.close()
		return

	# Migrate from legacy DB to the expected schema
	src = sqlite3.connect(legacy_path)
	src.row_factory = sqlite3.Row
	columns = []
	with src:
		cur = src.execute("PRAGMA table_info(clues)")
		columns = [r[1] for r in cur.fetchall()]

	dst = sqlite3.connect(story_db_path)
	with dst:
		dst.execute("CREATE TABLE IF NOT EXISTS clues (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT)")

	with src, dst:
		if "content" in columns:
			for rid, content in src.execute("SELECT id, content FROM clues"):
				dst.execute("INSERT INTO clues(id, content) VALUES(?, ?)", (rid, _normalize_text(content)))
		else:
			# Try mapping legacy triple columns to a single content
			select_cols = []
			for name in ("character", "user_message", "clue_text"):
				if name in columns:
					select_cols.append(name)
			if len(select_cols) >= 2:
				placeholders = ", ".join(select_cols)
				for row in src.execute(f"SELECT {placeholders} FROM clues"):
					content = _infer_old_clue_to_content(tuple(row))
					dst.execute("INSERT INTO clues(content) VALUES(?)", (content,))

	src.close()
	dst.close()


def _tokenize(text: str) -> List[str]:

	return [t for t in re.split(r"[^a-zA-Z0-9]+", (text or "").lower()) if t]


def _score_content_against_query(content: str, query_terms: List[str]) -> int:

	text = (content or "").lower()
	score = 0
	for term in query_terms:
		# Basic frequency scoring; add small boost for whole-word occurrences
		freq = text.count(term)
		if freq:
			score += freq
			if re.search(rf"\b{re.escape(term)}\b", text):
				score += 1
	return score


def query_db(question: str, top_k: int = 5) -> Tuple[str, List[Dict[str, str]]]:

	ensure_db()
	path = get_sqlite_path()
	terms = _tokenize(question)
	if not terms:
		return "", []

	like_filters = " OR ".join(["content LIKE ?" for _ in terms])
	params = [f"%{t}%" for t in terms]

	conn = sqlite3.connect(path)
	conn.row_factory = sqlite3.Row

	candidates: List[Tuple[int, str]] = []
	with conn:
		for row in conn.execute(
			f"SELECT id, content FROM clues WHERE {like_filters} LIMIT 200",
			params,
		):
			candidates.append((row["id"], row["content"]))

	if not candidates:
		# Fallback: sample some rows to avoid empty context
		with conn:
			for row in conn.execute("SELECT id, content FROM clues LIMIT 20"):
				candidates.append((row["id"], row["content"]))

	conn.close()

	scored: List[Tuple[int, int, str]] = []
	for cid, content in candidates:
		scored.append((cid, _score_content_against_query(content, terms), content))

	scored.sort(key=lambda x: x[1], reverse=True)
	selected = [(cid, content) for cid, score, content in scored[: top_k]]

	sources: List[Dict[str, str]] = []
	for cid, content in selected:
		sources.append({"id": str(cid), "content": content})

	context_text = "\n\n".join([s[1] for s in selected])
	return context_text, sources


