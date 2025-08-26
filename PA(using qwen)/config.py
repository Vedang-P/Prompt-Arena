import os


def get_sqlite_path() -> str:

	return os.getenv("PROMPT_ARENA_DB", os.path.abspath("story.db"))


def get_ollama_host() -> str:

	return os.getenv("OLLAMA_HOST", "http://localhost:11434")


def get_model_name() -> str:

	# Default to Qwen3 4B; set OLLAMA_MODEL to override if your local tag differs
	return os.getenv("OLLAMA_MODEL", "qwen3:4b")


DEFAULT_TOP_K = 5


