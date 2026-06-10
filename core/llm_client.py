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
}

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class LLMClient:
    def __init__(self, model_key: str = "qwen-plus"):
        self.model_key = model_key
        self._anthropic_client = None
        self._qwen_client = None
    
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
    
    def call(self, messages: List[Dict[str, str]], max_tokens: int = 2048) -> str:
        if self.model_key == "claude":
            return self._call_claude(messages, max_tokens)
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
    
    def call_json(self, messages: List[Dict[str, str]], max_tokens: int = 8192) -> Any:
        response_text = self.call(messages, max_tokens)
        json_str = self._extract_json_str(response_text)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复截断的 JSON（补全缺失的括号和引号）
            fixed = self._try_fix_truncated_json(json_str)
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
    def _try_fix_truncated_json(json_str: str):
        """尝试修复被截断的 JSON 数组/对象"""
        import re
        # 去掉末尾不完整的字符串（未闭合的引号）
        # 找最后一个完整的 JSON 对象结束位置
        last_brace = json_str.rfind("}")
        if last_brace == -1:
            return None
        truncated = json_str[:last_brace + 1]
        
        # 计算未闭合的括号
        open_brackets = truncated.count("[") - truncated.count("]")
        open_braces = truncated.count("{") - truncated.count("}")
        
        # 补全闭合
        fixed = truncated
        fixed += "}" * open_braces
        fixed += "]" * open_brackets
        
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None
