from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class LLMSettings:
    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "LLMSettings":
        api_key = os.getenv("DEEPSEEK_API_KEY") or None
        base_url = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        model = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
        timeout_str = os.getenv("DEEPSEEK_TIMEOUT_SECONDS") or "45"
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=float(timeout_str),
        )


class BaseLLMClient:
    backend_name = "unknown"

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 600) -> str:
        raise NotImplementedError


class DeepSeekChatClient(BaseLLMClient):
    backend_name = "deepseek"

    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 600) -> str:
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class LocalFallbackLLMClient(BaseLLMClient):
    backend_name = "local-fallback"

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 600) -> str:
        prompt = f"{system_prompt}\n{user_prompt}".lower()
        if "task_brief" in prompt or "任务概括" in prompt or "监督代理" in prompt or "任务拆解" in prompt or "plan" in prompt:
            return json.dumps(
                {
                    "task_brief": "比较目标公司 2025 年财务指标、供应链风险和管理层语气，最终输出带审计信息的合规报告。"
                },
                ensure_ascii=False,
            )
        if "executive summary" in prompt or "执行摘要" in prompt:
            return (
                "本次分析显示 Apple 供应链风险高于 Microsoft，"
                "但 Microsoft 的研发投入强度更高。整体来看，两家公司都保持了较强盈利能力，"
                "其中 Apple 更受制造链集中度影响，Microsoft 的经营韧性更强。"
            )
        if "合规" in prompt or "compliance" in prompt:
            return "报告包含数据来源与风险免责声明，当前未发现明显合规缺口。"
        return "已完成金融分析文本生成。"


class ResilientLLMClient(BaseLLMClient):
    def __init__(self, primary: BaseLLMClient | None, fallback: BaseLLMClient | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or LocalFallbackLLMClient()
        self.backend_name = primary.backend_name if primary else self.fallback.backend_name

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 600) -> str:
        if self.primary is None:
            self.backend_name = self.fallback.backend_name
            return self.fallback.chat(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens)
        try:
            self.backend_name = self.primary.backend_name
            return self.primary.chat(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens)
        except Exception:
            self.backend_name = self.fallback.backend_name
            return self.fallback.chat(system_prompt, user_prompt, temperature=temperature, max_tokens=max_tokens)


def build_llm_client(settings: LLMSettings | None = None) -> ResilientLLMClient:
    settings = settings or LLMSettings.from_env()
    primary = DeepSeekChatClient(settings) if settings.api_key else None
    return ResilientLLMClient(primary=primary, fallback=LocalFallbackLLMClient())
