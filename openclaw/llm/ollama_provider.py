import requests
from .provider import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    def __init__(self, model="llama3.1:70b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def complete(self, prompt: str) -> str:
        try:
            response = requests.post(f"{self.base_url}/api/generate", json={"model": self.model, "prompt": prompt})
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            raise RuntimeError(f"Failed to call Ollama API: {e}")
