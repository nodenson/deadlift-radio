TASK: Add Ollama LLM provider for parser and briefs

FILES: openclaw/llm/__init__.py (NEW), openclaw/llm/provider.py (NEW), openclaw/llm/ollama_provider.py (NEW)

Create a minimal LLM provider system:

provider.py:
- BaseLLMProvider class with complete(prompt: str) -> str method

ollama_provider.py:
- OllamaProvider(model="llama3.1:70b", base_url="http://localhost:11434")
- Calls Ollama REST API: POST /api/generate
- Returns response text
- Raises RuntimeError on failure

__init__.py:
- get_llm_provider() function
- Tries Ollama first (check if localhost:11434 is responding)
- Falls back to Groq if GROQ_API_KEY set
- Raises RuntimeError if neither available
- Logs which provider was selected

RULES:
- Use only requests library (already installed)
- No new dependencies
- Keep each file under 60 lines
- Do not modify any existing files
