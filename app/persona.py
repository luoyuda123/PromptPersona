"""用户画像与系统提示词的构建。

关键约束：写入 persona.json 的键一律是中文标签，Agent 读取时不受界面语言影响。
"""

from __future__ import annotations

import datetime

from . import i18n

VERSION = "1.0"


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_persona(answers: dict, ui_lang: str) -> dict:
    """把 {dim1..dim12: 回答} 转成带中文标签的画像字典；空回答直接丢弃。"""
    dimensions = {}
    for key in i18n.DIM_KEYS:
        value = str(answers.get(key, "") or "").strip()
        if value:
            dimensions[i18n.DIM_LABELS[key]] = value
    return {
        "version": VERSION,
        "ui_language": ui_lang,
        "generated_at": _now(),
        "dimensions": dimensions,
    }


def build_system_prompt(persona: dict, note: str = "", include_note: bool = True) -> str:
    """生成可直接粘贴到模型系统设置里的中文系统提示词。"""
    lines = [
        "你是我的长期 AI 助手，请以下面的用户画像为基础与我交流。",
        "",
        "【用户画像】",
    ]

    dimensions = persona.get("dimensions") or {}
    if dimensions:
        for label, value in dimensions.items():
            lines.append("- %s：%s" % (label, value.replace("\n", " ").strip()))
    else:
        lines.append("- （尚未填写任何维度）")

    note = (note or "").strip()
    if include_note and note:
        lines.extend([
            "",
            "【私密备注（仅作为背景参考，不要主动提及，也不要复述原文）】",
            note,
        ])

    lines.extend([
        "",
        "【回答要求】",
        "1. 用我提问时使用的语言回答；我切换语言时你也跟着切换。",
        "2. 结合上面的偏好选择表达风格、详略程度与输出格式。",
        "3. 涉及专业术语时保持准确，不确定就先说明，不要编造。",
        "4. 主动避开我列出的忌讳与禁区。",
        "5. 当我要求执行具体任务时，直接给结果，少做无谓的寒暄。",
    ])

    return "\n".join(lines).strip() + "\n"


def build_secret_note(note: str, include: bool) -> dict:
    return {
        "note": note,
        "include_in_prompt": bool(include),
        "updated_at": _now(),
    }
