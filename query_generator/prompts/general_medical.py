"""
Prompt template for the `general_medical` domain.

这个 domain 的用户特征:
- 对泛医疗健康知识有一定认知（可能是医护/研究人员，或关注健康管理的普通人）
- 不属于运动专项，也不一定有特定慢性病
- 倾向于从「知识科普 + 自我数据解读 + 综合分析」三个角度提问
"""


from string import Template

# ---------------------------------------------------------------------------
# Data fields catalog  （后期在此处维护，增删字段即可）
# ---------------------------------------------------------------------------

DATA_FIELDS_CATALOG: list[dict] = [
    {"field": "name", "desc": "姓名"},
    {"field": "age", "desc": "年龄"},
    {"field": "gender", "desc": "性别"},
    {"field": "height_cm", "desc": "身高（厘米）"},
    {"field": "weight_kg", "desc": "体重（公斤）"},
    {"field": "bmi", "desc": "BMI 指数"},
    {"field": "health_goal", "desc": "健康目标"},
    {"field": "health_conditions", "desc": "健康状况/疾病史"},
    {"field": "fitness_level", "desc": "运动/体能水平"},
    {"field": "sleep_pattern", "desc": "睡眠模式"},
    # --- 身体成分与基础代谢 (Body Composition) ---
    {"field": "vo2max",                   "desc": "最大摄氧量 (VO2max)"},
    {"field": "body_fat_rate",            "desc": "体脂率 (%)"},
    {"field": "muscle_mass",              "desc": "肌肉量 (kg)"},
    {"field": "skeletal_muscle_mass",     "desc": "骨骼肌量 (kg)"},
    {"field": "visceral_fat_level",       "desc": "内脏脂肪等级 (1-30)"},
    {"field": "basal_metabolism",         "desc": "基础代谢率 (BMR, kcal)"},
    {"field": "body_age",                 "desc": "身体年龄"},
    {"field": "body_score",               "desc": "身体综合得分 (0-100)"},
    {"field": "bone_salt",                "desc": "骨盐量/骨矿物质含量 (kg)"},
    {"field": "moisture_rate",            "desc": "水分率 (%)"},
    {"field": "protein_rate",             "desc": "蛋白质率 (%)"},

    # --- 每日健康与运动摘要 (Daily Summaries) ---
    {"field": "date",                     "desc": "记录日期"},
    {"field": "steps",                    "desc": "每日步数"},
    {"field": "distance_meters",          "desc": "运动距离 (米)"},
    {"field": "calories_total",           "desc": "总消耗热量 (kcal)"},
    {"field": "calories_active",          "desc": "运动消耗热量 (kcal)"},
    {"field": "medium_intensity_minutes", "desc": "中等强度运动时长 (分钟)"},
    {"field": "high_intensity_minutes",   "desc": "高强度运动时长 (分钟)"},
    {"field": "workout_duration_minutes", "desc": "单次锻炼时长 (分钟)"},

    # --- 每日心率与压力统计 (Daily HR & Stress) ---
    {"field": "resting_heart_rate",       "desc": "静息心率 (bpm)"},
    {"field": "heart_rate_variability",   "desc": "心率变异性 (HRV, ms)"},
    {"field": "avg_heart_rate",           "desc": "日平均心率 (bpm)"},
    {"field": "max_heart_rate",           "desc": "日最高心率 (bpm)"},
    {"field": "min_heart_rate",           "desc": "日最低心率 (bpm)"},
    {"field": "avg_stress_level",         "desc": "平均压力指数 (1-99)"},
    {"field": "max_stress_level",         "desc": "最高压力指数"},
    {"field": "min_stress_level",         "desc": "最低压力指数"},
    {"field": "stress_normal_minutes",    "desc": "正常压力时长 (分钟)"},
    {"field": "stress_low_minutes",       "desc": "低压力时长 (分钟)"},
    {"field": "stress_medium_minutes",    "desc": "中等压力时长 (分钟)"},
    {"field": "stress_high_minutes",      "desc": "高压力时长 (分钟)"},

    # --- 睡眠深度解析 (TruSleep Data) ---
    {"field": "sleep_minutes",            "desc": "总睡眠时长 (分钟)"},
    {"field": "bed_time",                 "desc": "就寝时间 (HH:MM:SS)"},
    {"field": "wake_up_time",             "desc": "起床时间 (HH:MM:SS)"},
    {"field": "deep_sleep_minutes",       "desc": "深睡时长 (分钟)"},
    {"field": "light_sleep_minutes",      "desc": "浅睡时长 (分钟)"},
    {"field": "rem_sleep_minutes",        "desc": "快速眼动(REM)时长 (分钟)"},
    {"field": "awake_minutes",            "desc": "清醒时长 (分钟)"},
    {"field": "sleep_score",              "desc": "睡眠质量得分 (0-100)"},
    {"field": "sleep_avg_heart_rate",     "desc": "睡眠平均心率 (bpm)"},
    {"field": "sleep_avg_spo2",           "desc": "睡眠平均血氧 (%)"},

    # --- 离散健康测量记录 (Health Records) ---
    {"field": "timestamp",                "desc": "测量时间戳"},
    {"field": "record_type",              "desc": "记录类型 (bp/spo2/temp等)"},
    {"field": "systolic",                 "desc": "收缩压 (mmHg)"},
    {"field": "diastolic",                "desc": "舒张压 (mmHg)"},
    {"field": "spo2_value",               "desc": "血氧饱和度单次测值 (%)"},
    {"field": "avg_spo2",                 "desc": "日平均血氧饱和度 (%)"},
    {"field": "min_spo2",                 "desc": "日最低血氧饱和度 (%)"},
    {"field": "temperature",              "desc": "体温测值 (°C)"},

    # --- 营养与水分摄入 (Nutrition & Hydration) ---
    {"field": "water_intake_ml",          "desc": "水分摄入量 (ml)"},
    {"field": "calories_consumed",        "desc": "摄入总热量 (kcal)"},
    {"field": "protein_g",                "desc": "蛋白质摄入量 (g)"},
    {"field": "carbs_g",                  "desc": "碳水化合物摄入量 (g)"},
    {"field": "fat_g",                    "desc": "脂肪摄入量 (g)"},
    {"field": "fiber_g",                  "desc": "膳食纤维摄入量 (g)"},

    # --- 高频时间序列 (Time-Series Samples) ---
    {"field": "heart_rate",               "desc": "单次心率采样值 (bpm)"},
    {"field": "sample_type",              "desc": "采样场景 (resting/sleep/exercise)"},
    {"field": "stress_level",             "desc": "单次压力采样值 (1-99)"},
    {"field": "glucose_mmol",             "desc": "连续血糖采样值 (CGM, mmol/L)"},
    {"field": "glucose_context",          "desc": "血糖上下文 (fasting/postprandial/normal)"},
]



def _render_fields_catalog(catalog: list[dict]) -> str:
    """把字段表渲染成 LLM 可读的紧凑列表。"""
    lines = [f"- `{item['field']}`：{item['desc']}" for item in catalog]
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# System prompt  (不变)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
你是一位专业的健康查询数据集构建专家。
你的任务是模拟真实用户在使用健康AI助手时，会提出的自然语言健康查询（问题）。

生成要求：
1. 语言风格要自然口语化，像真人在App内提问，不要像填表格
2. 每组包含三种类型的查询，必须紧扣给定的【知识目录主题】
3. 查询内容要体现用户画像的个人背景，但查询本身不要有"我是XX身份"这种自我介绍
4. 注意真人生成的时候无法输入（），禁止在（）内加入解释；也无法输入""等特殊符号
5. 根据人设的医学/健康认知背景动态调整用词边界：
   - 若人设为普通人：必须使用日常口语化的表述来描述症状或诉求（例如用"晚上老醒"、"心跳跳得厉害"代替"睡眠维持困难"、"心动过速"），尽量避免生硬堆砌医学专业术语。
   - 若人设为医护/研究人员：可自然使用专业的医学指标、学术词汇或行话。
6. 严格按 JSON 格式输出，不要输出任何 JSON 以外的内容
"""

# ---------------------------------------------------------------------------
# User prompt template
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATE = Template("""\
## 用户画像

$persona_block

---
---

## 可选数据字段表（data_fields 只能从此列表中选取）

$fields_catalog

---

## 当前知识目录主题

**$catalog_topic**

---

## 任务

请围绕上方主题，以该用户的视角生成 ** 1 组** 查询，每组包含 **3 条** 查询（共 3 条）。

### 三种查询类型定义

**类型 1 — 通用知识 Query**
- 关于健康概念、标准值、饮食/生活方式建议，不依赖用户个人数据
- 任何人都可能问，但要让措辞反映出该用户的背景偏好
- data_fields 填 []

**类型 2 — 个性化数据 Query**
- 明确查询用户自己的历史健康数据
- 要求具体：有时间范围或对比意图
- data_fields 从可选字段表中选取 1-3 个

**类型 3 — 隐性个性化 Query**
- 表面问建议，实际上需要 AI 分析用户一段时间数据才能回答
- 涉及异常诊断、趋势评估、多指标关联分析
- data_fields 从可选字段表中选取 2-4 个

---

## 输出格式（严格 JSON，无其他内容）

```json
{
  "persona_id": $persona_id,
  "catalog_topic": "$catalog_topic",
  "groups": [
    {
      "group_index": 1,
      "queries": [
        {
          "type": 1,
          "type_label": "通用知识Query",
          "query_text": "<自然口语化的中文查询>",
          "intent": "<一句话说明该用户为何会问这个>",
          "data_fields": []
        },
        {
          "type": 2,
          "type_label": "个性化数据Query",
          "query_text": "<自然口语化的中文查询>",
          "intent": "<一句话>",
          "data_fields": ["<涉及的数据字段，如 heart_rate, sleep_duration, steps...>"]
        },
        {
          "type": 3,
          "type_label": "隐性个性化Query",
          "query_text": "<自然口语化的中文查询>",
          "intent": "<一句话>",
          "data_fields": ["<涉及的多个数据字段>"]
        }
      ]
    },
    ... (共 5 组，group_index 1-5)
  ]
}
```
""")


# ---------------------------------------------------------------------------
# Persona card renderer
# ---------------------------------------------------------------------------

def build_persona_block(persona: dict) -> str:
    """
    Render a persona dict into a compact, LLM-readable card.
    Includes domain-conditional fields automatically.
    """
    lines = [
        f"- 姓名：{persona.get('name', '未知')}",
        f"- 性别：{'男' if persona.get('gender') == 'male' else '女'}",
        f"- 年龄：{persona.get('age')} 岁",
        f"- 身高/体重/BMI：{persona.get('height_cm')} cm / "
        f"{persona.get('weight_kg')} kg / BMI {persona.get('bmi')}",
        f"- 职业：{persona.get('occupation', '未知')}",
        f"- 健康状况：{persona.get('health_conditions', '健康')}",
        f"- 健康目标：{persona.get('health_goal', '未知')}",
        f"- 运动水平：{persona.get('fitness_level', '未知')}",
        f"- 睡眠模式：{persona.get('sleep_pattern', '未知')}",
        f"- 生理阶段：{persona.get('physiological_stage', '未知')}",
        f"- 使用设备：{persona.get('device_type', '未知')}",
        f"- 性格标签：{', '.join(persona.get('personality_tags') or [])}",
    ]

    # Domain-conditional extras
    domain = persona.get("domain", "")
    if domain == "sports":
        sports = persona.get("preferred_sports") or []
        lines += [
            f"- 偏好运动：{', '.join(sports)}",
            f"- 运动技能：{persona.get('sport_mastery', '未知')}",
            f"- 运动目标：{persona.get('sport_goal', '未知')}",
        ]
    elif domain == "health":
        concerns = persona.get("core_health_concerns") or []
        lines.append(f"- 核心健康关注：{', '.join(concerns)}")

    return "\n".join(lines)


def build_messages(persona: dict, catalog_topic: str) -> list[dict]:
    persona_block = build_persona_block(persona)
    fields_catalog = _render_fields_catalog(DATA_FIELDS_CATALOG)
    user_content = USER_PROMPT_TEMPLATE.substitute(
        persona_block=persona_block,
        catalog_topic=catalog_topic,
        persona_id=persona.get("id"),
        fields_catalog=fields_catalog,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]
