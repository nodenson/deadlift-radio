import os
import requests
from .ollama_provider import OllamaProvider

def get_llm_provider():
    try:
        response = requests.get("http://localhost:11434")
        if response.ok and "Ollama is running" in response.text:
            print("Selected provider: Ollama")
            return OllamaProvider()
    except Exception as e:
        print(f"Failed to connect to Ollama: {e}")

    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        print("Selected provider: Groq")
        # Placeholder for GroqProvider (not implemented)
        return None

    raise RuntimeError("No available LLM provider found")
