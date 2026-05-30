from __future__ import annotations

import json
import logging
import os
from urllib import request as urllib_request


logger = logging.getLogger(__name__)


class LLMProvider:
    def enrich(self, system_prompt: str, data: dict) -> str | None:
        raise NotImplementedError


class DisabledProvider(LLMProvider):
    def enrich(self, system_prompt: str, data: dict) -> str | None:
        return None


class OpenAIProvider(LLMProvider):
    def __init__(self, config: dict):
        self.base_url = (
            os.getenv(config["base_url_env"], "").rstrip("/")
            or "https://api.openai.com/v1"
        )
        self.api_key = os.getenv(config["api_key_env"]) or ""
        self.model = os.getenv(config["model_env"]) or "gpt-4o-mini"

    def enrich(self, system_prompt: str, data: dict) -> str | None:
        if not self.api_key:
            logger.info(json.dumps({"event": "llm_skipped", "reason": "missing_api_key"}))
            return None

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                },
            ],
            "temperature": 0.3,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            text = result["choices"][0]["message"]["content"].strip()
            usage = result.get("usage", {})
            logger.info(
                json.dumps(
                    {
                        "event": "llm_success",
                        "model": self.model,
                        "input_tokens": usage.get("prompt_tokens"),
                        "output_tokens": usage.get("completion_tokens"),
                    }
                )
            )
            return text
        except Exception as exc:
            logger.warning(
                json.dumps({"event": "llm_failure", "error": str(exc)})
            )
            return None


def create_provider(config: dict) -> LLMProvider:
    provider_name = config.get("provider", "disabled")
    providers_config = config.get("providers", {})
    if provider_name == "openai" and "openai_compatible" in providers_config:
        return OpenAIProvider(providers_config["openai_compatible"])
    return DisabledProvider()
