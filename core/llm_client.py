import os
import json
from typing import List, Dict, Any
import anthropic
from openai import OpenAI


MODELS = {
    "claude": "claude-opus-4-6",
    "qwen3.5-72b": "qwen3.5-72b",
    "qwen3.5-32b": "qwen3.5-32b",
    "qwen3-max": "qwen3-max-2026-01-23",
    "qwen3-235b-a22b": "qwen3-235b-a22b",
    "qwen3-32b": "qwen3-32b",
    "qwen3-14b": "qwen3-14b",
    "qwen3-8b": "qwen3-8b",
    "qwen-max": "qwen-max",
    "qwen-plus": "qwen-plus",
    "qwen-turbo": "qwen-turbo",
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
    "GLM-4.7": "ep-20260525134343-gks56",
}

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
VOLCENGINE_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


class LLMClient:
    def __init__(self, model_key: str = "qwen-plus"):
        self.model_key = model_key
        self._anthropic_client = None
        self._qwen_client = None
        self._deepseek_client = None
        self._volcengine_client = None
    
    @property
    def anthropic_client(self) -> anthropic.Anthropic:
        if self._anthropic_client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            kwargs = {"api_key": api_key} if api_key else {}
            base_url = os.getenv("ANTHROPIC_BASE_URL")
            if base_url:
                kwargs["base_url"] = base_url
            self._anthropic_client = anthropic.Anthropic(**kwargs)
        return self._anthropic_client
    
    @property
    def qwen_client(self) -> OpenAI:
        if self._qwen_client is None:
            api_key = os.getenv("DASHSCOPE_API_KEY", "")
            self._qwen_client = OpenAI(api_key=api_key, base_url=DASHSCOPE_BASE_URL)
        return self._qwen_client
    
    @property
    def deepseek_client(self) -> OpenAI:
        if self._deepseek_client is None:
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            self._deepseek_client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        return self._deepseek_client
    
    @property
    def volcengine_client(self) -> OpenAI:
        if self._volcengine_client is None:
            api_key = os.getenv("VOLCENGINE_API_KEY", "")
            self._volcengine_client = OpenAI(api_key=api_key, base_url=VOLCENGINE_BASE_URL)
        return self._volcengine_client
    
    def call(self, messages: List[Dict[str, str]], max_tokens: int = 2048) -> str:
        if self.model_key == "claude":
            return self._call_claude(messages, max_tokens)
        elif self.model_key.startswith("deepseek"):
            return self._call_deepseek(messages, max_tokens)
        elif self.model_key.startswith("doubao") or self.model_key.startswith("ep-"):
            return self._call_volcengine(messages, max_tokens)
        else:
            return self._call_qwen(messages, max_tokens)
    
    def _call_claude(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        response = self.anthropic_client.messages.create(
            model="claude-opus-4-6",
            max_tokens=max_tokens,
            messages=messages
        )
        return response.content[0].text
    
    def _call_qwen(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        response = self.qwen_client.chat.completions.create(
            model=self.model_key,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def _call_deepseek(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        response = self.deepseek_client.chat.completions.create(
            model=self.model_key,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def _call_volcengine(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        response = self.volcengine_client.chat.completions.create(
            model=self.model_key,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def call_json(self, messages, max_tokens=8192):
        response_text = self.call(messages, max_tokens)
        json_str = self._extract_json_str(response_text)

        # 第一次：直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 第二次：清洗后解析
        cleaned = self._clean_json_str(json_str)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 第三次：修复截断
        fixed = self._try_fix_truncated_json(cleaned)
        if fixed is not None:
            return fixed

        raise ValueError(f"LLM返回的JSON格式无效\n原始响应: {response_text[:2000]}")

    @staticmethod
    def _extract_json_str(text: str) -> str:
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()

    @staticmethod
    def _clean_json_str(json_str: str) -> str:
        """清洗 LLM 返回的常见 JSON 格式问题"""
        import re
        # 修复多余引号和空格: " "key" -> "key"
        json_str = re.sub(r'"\s*"(\w+)"', r'"\1"', json_str)
        # 修复 key 前后多余空格: " key" / "key " -> "key"
        json_str = re.sub(r'"(\s+)(\w+)"\s*:', r'"\2":', json_str)
        json_str = re.sub(r'"(\w+)(\s+)"\s*:', r'"\1":', json_str)
        # 去掉尾部逗号: ,} -> }  ,] -> ]
        json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
        return json_str

    @staticmethod
    def _try_fix_truncated_json(json_str: str):
        """尝试修复被截断的 JSON"""
        last_brace = json_str.rfind("}")
        if last_brace == -1:
            return None
        truncated = json_str[:last_brace + 1]
        open_brackets = truncated.count("[") - truncated.count("]")
        open_braces = truncated.count("{") - truncated.count("}")
        fixed = truncated + "}" * open_braces + "]" * open_brackets
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None
