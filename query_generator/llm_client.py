"""
LLM client for query generation.
Standalone - does not reuse the main project's llm.py.
Uses the same proxy + API configuration pattern.
"""

import json
import os
import time
import urllib3

import httpx
from openai import OpenAI

# ---------------------------------------------------------------------------
# Proxy & SSL config (mirrors main project setup)
# ---------------------------------------------------------------------------

PROXY = "http://proxysg.huawei.com:8080"
os.environ["HTTP_PROXY"] = PROXY
os.environ["HTTPS_PROXY"] = PROXY
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# API config (hardcoded, same pattern as main project)
# ---------------------------------------------------------------------------

API_KEY = "856ea640-6940-4a21-bc36-d0901fb184bd"
BASE_URL = "https://ark.cn-beijing.volces.com/api/coding/v3"
DEFAULT_MODEL = "deepseek-v3.2"

# Retry config
RETRY_DELAY_BASE = 2    # seconds, exponential backoff base
RETRY_DELAY_MAX  = 30   # seconds, cap


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class LLMClient:
    def __init__(self):
        http_client = httpx.Client(
            verify=False,
            trust_env=True,
            timeout=120.0,
        )
        self.client = OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY,
            http_client=http_client,
        )
        self.model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 4096,
        json_mode: bool = True,
        task_desc: str = "LLM call",
    ) -> str:
        """
        Send a chat request with infinite retry (exponential backoff).

        Returns:
            Raw content string from the model.
        """
        params: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
        }
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        retry = 0
        while True:
            try:
                resp = self.client.chat.completions.create(**params)
                return resp.choices[0].message.content
            except Exception as e:
                retry += 1
                delay = min(RETRY_DELAY_BASE * (2 ** (retry - 1)), RETRY_DELAY_MAX)
                print(f"  ⚠️  [{task_desc}] 第{retry}次失败: {str(e)[:60]} "
                      f"→ {delay}s 后重试...")
                time.sleep(delay)

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 4096,
        task_desc: str = "LLM call",
    ) -> dict:
        """
        Like chat() but automatically parses JSON response.
        Strips markdown fences if present before parsing.
        """
        raw = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            task_desc=task_desc,
        )
        # Strip ```json ... ``` fences if model wraps output
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(cleaned)


# Singleton helper
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
