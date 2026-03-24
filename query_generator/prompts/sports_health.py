# query_generator/prompts/sports_health.py
"""
运动健康 domain 的 prompt 模板。

Query 三类定义：
  Type 1 — 专业知识 Query    运动科学、训练原理、营养补剂等通用知识，不依赖个人数据
  Type 2 — 用户数据查询 Query 用户主动查询自己的运动/健康历史记录
  Type 3 — 知识计算 Query    需要结合用户数据进行量化推算（心率区间、热量消耗、VO2max 等）
"""

from __future__ import annotations


# --------------------------------------------------------------------------- #
#  Persona 渲染                                                                #
# --------------------------------------------------------------------------- #

def build_persona_block(persona: dict) -> str:
    """将 persona dict 渲染为 LLM 可读的文本卡片（运动健康视角）。"""
    lines = [
        f"姓名：{persona.get('name', '未知')}",
        f"性别：{'男' if persona.get('gender') == 'male' else '女'}",
        f"年龄：{persona.get('age', '?')} 岁",
        f"身高：{persona.get('height_cm', '?')} cm　体重：{persona.get('weight_kg', '?')} kg　BMI：{persona.get('bmi', '?')}",
        f"运动等级：{persona.get('fitness_level', '未知')}",
        f"健康目标：{persona.get('health_goal', '无')}",
        f"健康状况：{persona.get('health_conditions', '无')}",
        f"生理阶段：{persona.get('physiological_stage', '无')}",
        f"职业：{persona.get('occupation', '未知')}",
        f"睡眠模式：{persona.get('sleep_pattern', '未知')}",
        f"使用设备：{persona.get('device_type', '未知')}",
    ]

    # sports domain 专属字段
    preferred = persona.get("preferred_sports")
    if preferred:
        lines.append(f"偏好运动：{preferred}")

    mastery = persona.get("sport_mastery")
    if mastery:
        lines.append(f"运动技能等级：{mastery}")

    sport_goal = persona.get("sport_goal")
    if sport_goal:
        lines.append(f"运动目标：{sport_goal}")

    personality = persona.get("personality_tags")
    if personality:
        lines.append(f"性格标签：{personality}")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  Messages 构建                                                               #
# --------------------------------------------------------------------------- #

_SYSTEM_PROMPT = """\
你是一位专业的运动健康 AI 助手测试数据生成专家。
你的任务是：基于给定的用户画像（Persona）和运动健康知识目录主题，生成真实、多样的用户查询数据集。

【输出格式要求】
- 严格输出 JSON，不添加任何 Markdown 标记或解释文字
- 顶层字段：persona_id、catalog_topic、groups
- groups 是一个数组，包含 5 个 group 对象
- 每个 group 包含 group_index（1-5）和 queries 数组
- 每个 queries 数组恰好包含 3 条，对应 3 种类型（type 1/2/3 各一条）

【三种 Query 类型定义】
类型 1 — 专业知识 Query
  定义：运动科学、训练原理、营养学、损伤预防等通用知识，不依赖用户个人历史数据。
  要点：措辞体现该用户的运动水平与背景，但任何人都可以提问。
  示例：「负重深蹲之后应该间隔多久才能再练同一肌群？」

类型 2 — 用户数据查询 Query
  定义：用户主动查询自己在可穿戴设备或健康平台上记录的运动、生理历史数据。
  要点：明确、具体，通常带有时间范围或对比意图。
  示例：「我上个月每次跑步的平均配速是多少？和上上个月比有没有进步？」

类型 3 — 知识计算 Query
  定义：用户希望 AI 根据其个人数据进行量化推算或评估，需要结合运动公式/模型。
  典型计算场景：目标心率区间、本次运动热量消耗、VO2max 估算、训练负荷指数、恢复建议等。
  示例：「根据我昨天的心率数据，帮我算一下我在各心率区间分别待了多长时间。」

【质量要求】
- 5 个 group 的 query 主题角度要有差异，避免重复
- 每条 query 的 query_text 用自然的中文口语，符合该用户背景
- intent 说明该用户提出此问题的真实动机（1-2 句）
- data_fields 列出回答此 query 需要访问的健康/运动数据字段（类型 1 可为空数组）
"""

_USER_TEMPLATE = """\
请为以下用户画像，围绕知识目录主题「{catalog_topic}」生成查询数据集。

【用户画像】
{persona_block}

【输出 JSON 模板】
{{
  "persona_id": {persona_id},
  "catalog_topic": "{catalog_topic}",
  "groups": [
    {{
      "group_index": 1,
      "queries": [
        {{
          "type": 1,
          "type_label": "专业知识Query",
          "query_text": "...",
          "intent": "...",
          "data_fields": []
        }},
        {{
          "type": 2,
          "type_label": "用户数据查询Query",
          "query_text": "...",
          "intent": "...",
          "data_fields": ["..."]
        }},
        {{
          "type": 3,
          "type_label": "知识计算Query",
          "query_text": "...",
          "intent": "...",
          "data_fields": ["..."]
        }}
      ]
    }}
    // ... 共 5 个 group
  ]
}}
"""


def build_messages(persona: dict, catalog_topic: str) -> list[dict]:
    """构建完整的 messages 列表，传给 LLMClient.chat_json()。"""
    persona_block = build_persona_block(persona)
    user_content = _USER_TEMPLATE.format(
        catalog_topic=catalog_topic,
        persona_block=persona_block,
        persona_id=persona.get("id", 0),
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
