"""OpenAI 兼容接口调用与多模型执行策略。

只用标准库 urllib，无第三方依赖；任何异常都转成 {ok: False, error}，不抛给界面。
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 45


def _endpoint(base_url: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def chat(entry: dict, messages: list, timeout: int = TIMEOUT, max_tokens: int = None) -> dict:
    """发一次 chat/completions 请求，返回 {ok, text} 或 {ok: False, error}。"""
    payload = {
        "model": entry.get("model", ""),
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }
    if max_tokens:
        payload["max_tokens"] = int(max_tokens)

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key = str(entry.get("api_key") or "").strip()
    if key:
        headers["Authorization"] = "Bearer " + key

    try:
        request = urllib.request.Request(
            _endpoint(entry.get("base_url")),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            detail = error.read().decode("utf-8", "replace")
            parsed = json.loads(detail)
            if isinstance(parsed, dict):
                inner = parsed.get("error")
                if isinstance(inner, dict):
                    detail = inner.get("message") or detail
                elif isinstance(inner, str):
                    detail = inner
                elif parsed.get("message"):
                    detail = parsed["message"]
        except (ValueError, OSError):
            pass
        return {"ok": False, "error": "HTTP %s: %s" % (error.code, str(detail)[:400])}
    except (socket.timeout, TimeoutError):
        return {"ok": False, "error": "超时（%ss）" % timeout}
    except urllib.error.URLError as error:
        return {"ok": False, "error": "无法连接：%s" % (error.reason,)}
    except (ValueError, OSError) as error:
        return {"ok": False, "error": "请求失败：%s" % (error,)}
    except Exception as error:  # 兜底，绝不让界面崩溃
        return {"ok": False, "error": "未知错误：%s" % (error,)}

    try:
        parsed = json.loads(body)
        text = parsed["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return {"ok": False, "error": "响应格式不是 OpenAI 兼容结构：%s" % body[:300]}

    if isinstance(text, list):
        # 部分供应商返回分段内容数组
        text = "".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in text)
    return {"ok": True, "text": str(text).strip()}


def test_connection(entry: dict, timeout: int = 20) -> dict:
    return chat(
        entry,
        [{"role": "user", "content": "Reply with the single word: ok"}],
        timeout=timeout,
        max_tokens=8,
    )


def _one(entry: dict, messages: list) -> dict:
    result = chat(entry, messages)
    result.update({"name": entry.get("name") or entry.get("model"), "model": entry.get("model")})
    return result


def run(messages: list, entries: list, strategy: str, rotate_index: int = 0) -> tuple:
    """按策略执行，返回 (结果列表, 下一次轮询下标)。

    strategy: primary / poll / parallel
    """
    results = []
    if not entries:
        return results, rotate_index

    if strategy == "parallel":
        with ThreadPoolExecutor(max_workers=min(len(entries), 8)) as pool:
            futures = [pool.submit(_one, entry, messages) for entry in entries]
            for future in futures:
                results.append(future.result())
        return results, rotate_index

    if strategy == "poll":
        index = rotate_index % len(entries)
        results.append(_one(entries[index], messages))
        return results, (index + 1) % len(entries)

    results.append(_one(entries[0], messages))
    return results, rotate_index
