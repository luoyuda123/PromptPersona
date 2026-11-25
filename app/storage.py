"""本地文件存储：配置与画像产物，全部落在程序目录下的 JSON / TXT。

打包成单文件 exe 后，数据目录改为 exe 所在目录，保持「绿色便携」。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

CONFIG_FILE = "config.json"
PERSONA_FILE = "persona.json"
SECRET_FILE = "secret_note.json"
PROMPT_FILE = "persona_system.txt"


def app_dir() -> str:
    """返回数据目录：源码运行时是项目根目录，打包后是 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path_of(name: str) -> str:
    return os.path.join(app_dir(), name)


def load_json(name: str, default=None):
    """读取 JSON；文件缺失或损坏时返回 default，不抛异常。"""
    full = path_of(name)
    if not os.path.exists(full):
        return default
    try:
        with open(full, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def save_json(name: str, data) -> str:
    """原子写入 JSON（先写临时文件再替换），返回完整路径。"""
    full = path_of(name)
    directory = os.path.dirname(full)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=directory, delete=False, suffix=".tmp"
    )
    try:
        with handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(handle.name, full)
    except BaseException:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise
    return full


def save_text(name: str, text: str) -> str:
    full = path_of(name)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=os.path.dirname(full), delete=False, suffix=".tmp"
    )
    try:
        with handle:
            handle.write(text)
        os.replace(handle.name, full)
    except BaseException:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise
    return full


def read_text(name: str) -> str:
    full = path_of(name)
    if not os.path.exists(full):
        return ""
    with open(full, "r", encoding="utf-8") as handle:
        return handle.read()


DEFAULT_CONFIG = {
    "lang": "",
    "strategy": "primary",
    "models": [],
    "rotate_index": 0,
    "note": "",
    "include_note": True,
    "answers": {},
}


def load_config() -> dict:
    data = load_json(CONFIG_FILE, {})
    if not isinstance(data, dict):
        data = {}
    config = dict(DEFAULT_CONFIG)
    config.update({key: value for key, value in data.items() if key in DEFAULT_CONFIG})
    if not isinstance(config.get("models"), list):
        config["models"] = []
    if not isinstance(config.get("answers"), dict):
        config["answers"] = {}
    if config.get("strategy") not in ("poll", "parallel", "primary"):
        config["strategy"] = "primary"
    return config


def save_config(config: dict) -> str:
    return save_json(CONFIG_FILE, config)
