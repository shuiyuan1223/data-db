"""
Prompt template for the `health` domain.

这个 domain 的用户特征:
- 核心关注个人日常健康管理，如心脏、睡眠、血压、血糖、体重等
- catalog_topic 支持单领域（如"睡眠健康"）和多领域组合（如"心脏健康_睡眠健康"）
- 提问风格覆盖三类：知识科普、历史数据查询、跨维度综合分析
"""

from string import Template

# ---------------------------------------------------------------------------
# 健康数据字典
# ---------------------------------------------------------------------------

HEALTH_DATA_MARKDOWN = """
### 1. 心脏健康
- `heart_rate`：动态心率（实时采样值）
- `resting_heart_rate`：静息心率（每日）
- `avg_heart_rate` / `max_heart_rate` / `min_heart_rate`：日均/最高/最低心率
- `heart_rate_variability`：心率变异性 HRV（通常睡眠期间测量）
- `high_heart_rate_count` / `low_heart_rate_count`：心率过高/过低次数

### 2. 睡眠健康
- `sleep_minutes`：夜间总睡眠时长（分钟）
- `sleep_score`：睡眠质量得分（0-100）
- `deep_sleep_minutes` / `light_sleep_minutes` / `rem_sleep_minutes`：深睡/浅睡/REM 时长
- `awake_minutes`：清醒时长
- `bed_time` / `wake_up_time`：就寝/起床时间
- `sleep_avg_heart_rate`：睡眠平均心率
- `sleep_avg_spo2`：睡眠平均血氧

### 3. 午睡/零星小睡
- `nap_duration_minutes`：零星小睡总时长（分钟）

### 4. 血压与血氧
- `systolic` / `diastolic`：收缩压 / 舒张压（mmHg）
- `spo2_value`：单次血氧饱和度测值（%）
- `avg_spo2` / `min_spo2`：日均/最低血氧饱和度

### 5. 情绪与压力
- `avg_stress_level` / `max_stress_level`：平均/最高压力指数（1-99）
- `stress_low_minutes` / `stress_medium_minutes` / `stress_high_minutes`：低/中/高压力时长
- `emotion_pleasant_count` / `emotion_calm_count` / `emotion_unpleasant_count`：愉悦/平静/不愉悦情绪次数

### 6. 体温监测
- `temperature`：体温测值（°C）
- `skin_temperature`：腕部皮肤温度

### 7. 饮食与代谢（减脂管理）
- `weight_kg`：体重（kg）
- `bmi`：BMI 指数
- `body_fat_rate`：体脂率（%）
- `muscle_mass`：肌肉量（kg）
- `visceral_fat_level`：内脏脂肪等级（1-30）
- `basal_metabolism`：基础代谢率 BMR（kcal）
- `calories_total` / `calories_active`：总消耗热量 / 运动消耗热量
- `calories_consumed`：摄入总热量（kcal）
- `protein_g` / `carbs_g` / `fat_g`：蛋白质/碳水/脂肪摄入量（g）
- `water_intake_ml`：水分摄入量（ml）

### 8. 步数/活动量 & 活力三环
- `steps`：每日步数
- `distance_meters`：运动距离（米）
- `medium_intensity_minutes`：中等强度运动时长（分钟）
- `high_intensity_minutes`：高强度运动时长（分钟）
- `active_hours`：保持活动状态的小时数

### 9. 女性生理健康
- `menstrual_phase`：生理周期阶段（月经期/卵泡期/排卵期/黄体期）
- `menstrual_flow`：月经量（少/中/多）
- `dysmenorrhea_level`：痛经程度
- `physical_symptoms`：身体症状记录（头痛/胸胀等）

### 10. 微体检/综合报告
- `body_score`：身体综合得分（0-100）
- `body_age`：身体年龄
- `vo2max`：最大摄氧量（VO2max）
- `bone_salt`：骨盐量（kg）
- `moisture_rate`：水分率（%）
- `protein_rate`：蛋白质率（%）
"""


# ---------------------------------------------------------------------------
# Data fields catalog
# ---------------------------------------------------------------------------

DATA_FIELDS_CATALOG: list[dict] = [
    {"field": "heart_rate",                 "desc": "动态心率（实时采样）"},
    {"field": "resting_heart_rate",         "desc": "静息心率（每日）"},
    {"field": "avg_heart_rate",             "desc": "日均心率"},
    {"field": "max_heart_rate",             "desc": "日最高心率"},
    {"field": "min_heart_rate",             "desc": "日最低心率"},
    {"field": "heart_rate_variability",     "desc": "心率变异性 HRV"},
    {"field": "high_heart_rate_count",      "desc": "心率过高次数"},
    {"field": "low_heart_rate_count",       "desc": "心率过低次数"},
    {"field": "sleep_minutes",              "desc": "夜间总睡眠时长（分钟）"},
    {"field": "sleep_score",               "desc": "睡眠质量得分（0-100）"},
    {"field": "deep_sleep_minutes",         "desc": "深睡时长"},
    {"field": "light_sleep_minutes",        "desc": "浅睡时长"},
    {"field": "rem_sleep_minutes",          "desc": "REM 时长"},
    {"field": "awake_minutes",              "desc": "清醒时长"},
    {"field": "bed_time",                   "desc": "就寝时间"},
    {"field": "wake_up_time",               "desc": "起床时间"},
    {"field": "sleep_avg_heart_rate",       "desc": "睡眠平均心率"},
    {"field": "sleep_avg_spo2",             "desc": "睡眠平均血氧"},
    {"field": "nap_duration_minutes",       "desc": "零星小睡时长（分钟）"},
    {"field": "systolic",                   "desc": "收缩压（mmHg）"},
    {"field": "diastolic",                  "desc": "舒张压（mmHg）"},
    {"field": "spo2_value",                 "desc": "单次血氧饱和度（%）"},
    {"field": "avg_spo2",                   "desc": "日均血氧饱和度"},
    {"field": "min_spo2",                   "desc": "日最低血氧饱和度"},
    {"field": "avg_stress_level",           "desc": "平均压力指数（1-99）"},
    {"field": "max_stress_level",           "desc": "最高压力指数"},
    {"field": "stress_low_minutes",         "desc": "低压力时长"},
    {"field": "stress_medium_minutes",      "desc": "中等压力时长"},
    {"field": "stress_high_minutes",        "desc": "高压力时长"},
    {"field": "emotion_pleasant_count",     "desc": "愉悦情绪次数"},
    {"field": "emotion_calm_count",         "desc": "平静情绪次数"},
    {"field": "emotion_unpleasant_count",   "desc": "不愉悦情绪次数"},
    {"field": "temperature",                "desc": "体温（°C）"},
    {"field": "skin_temperature",           "desc": "腕部皮肤温度"},
    {"field": "weight_kg",                  "desc": "体重（kg）"},
    {"field": "bmi",                        "desc": "BMI 指数"},
    {"field": "body_fat_rate",              "desc": "体脂率（%）"},
    {"field": "muscle_mass",                "desc": "肌肉量（kg）"},
    {"field": "visceral_fat_level",         "desc": "内脏脂肪等级"},
    {"field": "basal_metabolism",           "desc": "基础代谢率（kcal）"},
    {"field": "calories_total",             "desc": "总消耗热量（kcal）"},
    {"field": "calories_active",            "desc": "运动消耗热量（kcal）"},
    {"field": "calories_consumed",          "desc": "摄入总热量（kcal）"},
    {"field": "protein_g",                  "desc": "蛋白质摄入量（g）"},
    {"field": "carbs_g",                    "desc": "碳水摄入量（g）"},
    {"field": "fat_g",                      "desc": "脂肪摄入量（g）"},
    {"field": "water_intake_ml",            "desc": "水分摄入量（ml）"},
    {"field": "steps",                      "desc": "每日步数"},
    {"field": "distance_meters",            "desc": "运动距离（米）"},
    {"field": "medium_intensity_minutes",   "desc": "中等强度运动时长"},
    {"field": "high_intensity_minutes",     "desc": "高强度运动时长"},
    {"field": "active_hours",               "desc": "保持活动状态的小时数"},
    {"field": "menstrual_phase",            "desc": "生理周期阶段"},
    {"field": "menstrual_flow",             "desc": "月经量"},
    {"field": "dysmenorrhea_level",         "desc": "痛经程度"},
    {"field": "physical_symptoms",          "desc": "身体症状记录"},
    {"field": "body_score",                 "desc": "身体综合得分（0-100）"},
    {"field": "body_age",                   "desc": "身体年龄"},
    {"field": "vo2max",                     "desc": "最大摄氧量（VO2max）"},
    {"field": "bone_salt",                  "desc": "骨盐量（kg）"},
    {"field": "moisture_rate",              "desc": "水分率（%）"},
    {"field": "protein_rate",               "desc": "蛋白质率（%）"},
]


def _render_fields_catalog(catalog: list[dict]) -> str:
    lines = [f"- `{item['field']}`：{item['desc']}" for item in catalog]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
你是一位专业的健康查询数据集构建专家。
你的任务是模拟真实用户在使用健康AI助手时，会提出的自然语言健康查询（问题）。

生成要求：
1. 语言风格要自然口语化，像真人在App内提问，不要像填表格
2. 每组包含三种类型的查询，必须紧扣给定的【关注健康领域】
3. 查询内容要体现用户画像的个人背景，但查询本身不要有"我是XX身份"这种自我介绍
4. 注意真人生成的时候无法输入（），禁止在（）内加入解释；也无法输入""等特殊符号
5. 根据人设的医学/健康认知背景动态调整用词边界：
   - 若人设为普通人：必须使用日常口语化的表述（例如用"晚上老醒"、"心跳跳得厉害"代替"睡眠维持困难"、"心动过速"），避免生硬堆砌医学术语
   - 若人设为医护/研究人员：可自然使用专业的医学指标和行话
6. 严格按 JSON 格式输出，不要输出任何 JSON 以外的内容
"""

# ---------------------------------------------------------------------------
# User prompt template
# ---------------------------------------------------------------------------

USER_PROMPT_TEMPLATE = Template("""\
## 用户画像

$persona_block

---

## 当前关注健康领域

**$catalog_topic**

> 若为组合领域（以 _ 分隔），请确保生成的 Query 覆盖所有子领域，各子领域均有体现。

---

## 健康数据字典（AI可调用的数据范围）

$health_data_md

---

## 可选数据字段表（data_fields 只能从此列表中选取）

$fields_catalog

---

## 任务

请围绕上方关注领域，以该用户的视角生成 **5 组** 查询，每组包含 **3 条** 查询（共 15 条）。

### 三种查询类型定义

**类型 1 — 通用知识 Query**
- 关于健康概念、标准值、饮食/生活方式建议，不依赖用户个人数据
- 任何人都可能问，但措辞要反映该用户的背景和关注点
- data_fields 填 []

**类型 2 — 个性化数据 Query**
- 明确查询用户自己的历史健康数据
- 要求具体：有时间范围或对比意图
- data_fields 从可选字段表中选取 1-3 个

**类型 3 — 隐性个性化 Query**
- 表面问建议，实际上需要 AI 分析用户一段时间的多维数据才能回答
- 涉及异常诊断、趋势评估、多指标关联分析
- data_fields 从可选字段表中选取 2-4 个

**质量要求**：
- 口语化，可适当使用语气词
- 逻辑一致：画像是老年高血压患者，就不要问痛经的问题
- 严禁出现英文 Query
- 句子长度要多样：5-10字的简短句、11-25字的中等句、26-50字的长句都要有
- 5 组之间应有显著多样性，避免重复提问

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
          "data_fields": ["<字段名>"]
        },
        {
          "type": 3,
          "type_label": "隐性个性化Query",
          "query_text": "<自然口语化的中文查询>",
          "intent": "<一句话>",
          "data_fields": ["<字段1>", "<字段2>", "..."]
        }
      ]
    }
    // ... 共 5 组，group_index 1-5
  ]
}
```
""")


# ---------------------------------------------------------------------------
# Persona card renderer
# ---------------------------------------------------------------------------

def build_persona_block(persona: dict) -> str:
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
    concerns = persona.get("core_health_concerns") or []
    if concerns:
        lines.append(f"- 核心健康关注：{', '.join(concerns)}")
    return "\n".join(lines)


def build_messages(persona: dict, catalog_topic: str) -> list[dict]:
    persona_block  = build_persona_block(persona)
    fields_catalog = _render_fields_catalog(DATA_FIELDS_CATALOG)
    user_content   = USER_PROMPT_TEMPLATE.substitute(
        persona_block  = persona_block,
        catalog_topic  = catalog_topic,
        health_data_md = HEALTH_DATA_MARKDOWN,
        fields_catalog = fields_catalog,
        persona_id     = persona.get("id"),
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]
