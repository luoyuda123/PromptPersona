"""模型条目、内置候选库与列表操作。

只做数据与校验，不发请求；网络调用在 providers.py。
"""

from __future__ import annotations

import uuid

from . import i18n

SOURCE_AUTO = "auto"
SOURCE_MANUAL = "manual"

ALL_LANGS = list(i18n.LANG_CODES)

# 内置候选库：只用于「自动检索」时给用户挑选，所有条目都是 OpenAI 兼容接口。
CATALOG = [
    {
        "name": "GPT-4o（OpenAI）",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "langs": ALL_LANGS,
    },
    {
        "name": "DeepSeek Chat",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "langs": ["zh", "zh-tw", "en", "ja", "ko", "fr", "ru", "es", "de", "ar"],
    },
    {
        "name": "通义千问 Qwen-Plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "langs": ["zh", "zh-tw", "en", "ja", "ko", "ru", "ar"],
    },
    {
        "name": "Kimi（Moonshot）",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "langs": ["zh", "zh-tw", "en"],
    },
    {
        "name": "Gemini 2.0 Flash（兼容接口）",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "langs": ALL_LANGS,
    },
    {
        "name": "OpenRouter Claude 3.5 Sonnet",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-3.5-sonnet",
        "langs": ALL_LANGS,
    },
    {
        "name": "Groq Llama 3.3 70B",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "langs": ["en", "es", "fr", "de", "pt"],
    },
    {
        "name": "本地 Ollama（qwen2.5:7b）",
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
        "langs": ["zh", "zh-tw", "en"],
    },
]

ENTRY_DEFAULTS = {
    "id": "",
    "name": "",
    "base_url": "",
    "api_key": "",
    "model": "",
    "local_path": "",
    "source": SOURCE_MANUAL,
    "enabled": True,
    "langs": [],
}


def new_entry(**fields) -> dict:
    entry = dict(ENTRY_DEFAULTS)
    entry.update({key: value for key, value in fields.items() if key in ENTRY_DEFAULTS})
    entry["id"] = entry["id"] or uuid.uuid4().hex[:8]
    entry["langs"] = list(entry["langs"] or [])
    entry["api_key"] = str(entry["api_key"] or "")
    entry["local_path"] = str(entry["local_path"] or "")
    entry["name"] = str(entry["name"] or "").strip() or str(entry["model"] or "").strip()
    entry["base_url"] = str(entry["base_url"] or "").strip()
    entry["model"] = str(entry["model"] or "").strip()
    entry["enabled"] = bool(entry["enabled"])
    entry["source"] = entry["source"] if entry["source"] in (SOURCE_AUTO, SOURCE_MANUAL) else SOURCE_MANUAL
    return entry


def catalog_for(lang: str) -> list:
    """按界面语言筛出候选；langs 里含 all 或当前编码即算匹配。"""
    items = []
    for item in CATALOG:
        supported = item["langs"]
        if "all" in supported or lang in supported:
            items.append({
                "name": item["name"],
                "base_url": item["base_url"],
                "model": item["model"],
                "langs": list(supported),
            })
    return items


def validate(entry: dict) -> tuple:
    """返回 (是否通过, 错误文案键)。文案键由界面负责翻译。"""
    if not entry.get("model"):
        return False, "model_required"
    base = str(entry.get("base_url") or "").strip()
    if not base:
        return False, "base_required"
    if not (base.startswith("http://") or base.startswith("https://")):
        return False, "base_invalid"
    return True, ""


def is_duplicate(entries: list, entry: dict) -> bool:
    for item in entries:
        if item.get("base_url", "").rstrip("/") == entry.get("base_url", "").rstrip("/") \
                and item.get("model", "") == entry.get("model", ""):
            return True
    return False


def move(entries: list, index: int, delta: int) -> list:
    """上移 / 下移；越界时原样返回。"""
    target = index + delta
    if 0 <= index < len(entries) and 0 <= target < len(entries):
        entries[index], entries[target] = entries[target], entries[index]
    return entries


def enabled(entries: list) -> list:
    return [item for item in entries if item.get("enabled")]
