const fs = require('fs');
const path = require('path');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, VerticalAlign, LevelFormat, PageNumber } = require(path.join(__dirname, '..', '.claude', 'skills', 'docx', 'node_modules', 'docx'));

// ─── Shared styles & helpers ───
const FONT = '微软雅黑';
const FONT_EN = 'Arial';
const COLOR = '333333';
const HEADING_COLOR = '1a1a1a';
const ACCENT = '2B579A';

const styles = {
  default: { document: { run: { font: FONT, size: 21, color: COLOR } } },
  paragraphStyles: [
    { id: 'Title', name: 'Title', basedOn: 'Normal',
      run: { size: 36, bold: true, color: HEADING_COLOR, font: FONT },
      paragraph: { spacing: { before: 120, after: 200 }, alignment: AlignmentType.CENTER } },
    { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 30, bold: true, color: ACCENT, font: FONT },
      paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
    { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 26, bold: true, color: HEADING_COLOR, font: FONT },
      paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
    { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 23, bold: true, color: '444444', font: FONT },
      paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
  ]
};

const numbering = {
  config: [
    { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] },
    { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] },
  ]
};

const border = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const cellBorders = { top: border, bottom: border, left: border, right: border };
const headerShading = { fill: 'E8EEF4', type: ShadingType.CLEAR };

function p(text, opts = {}) {
  const runs = [];
  // Parse **bold** and `code`
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  for (const part of parts) {
    if (part.startsWith('**') && part.endsWith('**')) {
      runs.push(new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, size: 21 }));
    } else if (part.startsWith('`') && part.endsWith('`')) {
      runs.push(new TextRun({ text: part.slice(1, -1), font: 'Consolas', size: 19, color: '8B0000' }));
    } else if (part) {
      runs.push(new TextRun({ text: part, font: FONT, size: 21, ...opts }));
    }
  }
  return new Paragraph({ spacing: { before: 60, after: 60 }, children: runs });
}

function h1(text) { return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font: FONT })] }); }
function h2(text) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: FONT })] }); }
function h3(text) { return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text, font: FONT })] }); }

function bullet(text) {
  const runs = [];
  const parts = text.split(/(\*\*.*?\*\*)/g);
  for (const part of parts) {
    if (part.startsWith('**') && part.endsWith('**')) {
      runs.push(new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, size: 21 }));
    } else if (part) {
      runs.push(new TextRun({ text: part, font: FONT, size: 21 }));
    }
  }
  return new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { before: 40, after: 40 }, children: runs });
}

function num(text, ref = 'numbers') {
  return new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { before: 40, after: 40 },
    children: [new TextRun({ text, font: FONT, size: 21 })] });
}

function table(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a, b) => a + b, 0);
  const mkCell = (text, isHeader, width) => {
    const runs = [];
    const parts = String(text).split(/(\*\*.*?\*\*)/g);
    for (const part of parts) {
      if (part.startsWith('**') && part.endsWith('**')) {
        runs.push(new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, size: 18 }));
      } else if (part) {
        runs.push(new TextRun({ text: part, font: FONT, size: 18, bold: isHeader }));
      }
    }
    return new TableCell({
      borders: cellBorders,
      width: { size: width, type: WidthType.DXA },
      shading: isHeader ? headerShading : undefined,
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({ spacing: { before: 40, after: 40 }, children: runs })]
    });
  };
  return new Table({
    columnWidths: colWidths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => mkCell(h, true, colWidths[i])) }),
      ...rows.map(row => new TableRow({ children: row.map((c, i) => mkCell(c, false, colWidths[i])) }))
    ]
  });
}

function meta(version, date, project) {
  return [
    new Paragraph({ spacing: { before: 60, after: 40 }, children: [
      new TextRun({ text: '文档版本', bold: true, font: FONT, size: 20 }),
      new TextRun({ text: `: ${version}    `, font: FONT, size: 20 }),
      new TextRun({ text: '编写日期', bold: true, font: FONT, size: 20 }),
      new TextRun({ text: `: ${date}`, font: FONT, size: 20 }),
    ]}),
    new Paragraph({ spacing: { before: 40, after: 40 }, children: [
      new TextRun({ text: '负责人', bold: true, font: FONT, size: 20 }),
      new TextRun({ text: ': [姓名]    ', font: FONT, size: 20 }),
      new TextRun({ text: '项目', bold: true, font: FONT, size: 20 }),
      new TextRun({ text: `: ${project}`, font: FONT, size: 20 }),
    ]}),
  ];
}

function spacer() { return new Paragraph({ spacing: { before: 80, after: 80 }, children: [] }); }

function makeFooter() {
  return new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
    new TextRun({ text: '第 ', font: FONT, size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 }),
    new TextRun({ text: ' 页', font: FONT, size: 18 }),
  ]})]});
}

// ─── Doc 1: 测试策略 ───
function buildDoc1() {
  return [
    new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: 'AI 数据自动化生态系统', font: FONT })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: '测试策略与测试设计文档', font: FONT, size: 28, bold: true, color: '555555' })] }),
    ...meta('v3.0', '2026-03-27', '健康查询数据自动化生成-聚类-审查生态系统'),
    spacer(),

    h1('1. 测试背景与目标'),
    h2('1.1 项目概述'),
    p('本人围绕已有的健康查询基准数据库，构建了一套**端到端的 AI 数据自动化生态系统**，覆盖从 Prompt 驱动的数据合成、多源数据清洗与场景适配、UMAP+HDBSCAN 聚类调优，到统一质量审查的全链路。'),
    p('本系统的核心价值不在于单个模块，而在于**生成 → 聚类 → 审查的一条龙自动化数据管理能力**。'),
    spacer(),

    h2('1.2 数据成果总览'),
    table(['数据来源', '原始/生成数量', '去重/清洗后', '特性描述'],
      [['LLM 自动合成', '49,200', '48,895', '结构化强，覆盖通用/显性/隐性个性化'],
       ['谷歌数据场景适配', '4,170', '7,424', '多维度生态改写，适配华为 Watch'],
       ['现网数据分类抽样', '4,111 (抽样)', '—', '真实性强，长尾与口语化表达'],
       ['**总计**', '**57,481**', '**56,319**', '**多源异构**']],
      [2200, 1800, 1800, 3560]),
    spacer(),

    h2('1.3 Domain 可插拔架构'),
    p('本系统设计了 **Domain 可插拔架构**，每个 Domain 都是独立的数据生成维度，拥有独立的 Prompt 模板，可持续生成且随时扩展新维度：'),
    table(['Domain', '独立 Prompt 文件', '估计规模', '可扩展性'],
      [['general_medical', 'prompts/general_medical.py', '~500 条', '可持续追加，扩展新知识主题'],
       ['health', 'prompts/health.py', '~500 条', '支持 topic_count 多子域'],
       ['sports', 'prompts/sports.py', '~500 条', 'LLM 内联 persona，可扩展运动项目'],
       ['sports_health', 'prompts/sports_health.py', '~500 条', '跨域 persona 适配'],
       ['red_team', 'prompts/red_team.py', '~500 条', '4 类攻击，可扩展新攻击类型']],
      [2000, 2800, 1200, 3360]),
    spacer(),
    p('**新 Domain 接入流程（零代码扩展）**：'),
    num('prompts/ 新建 prompt 文件 → 实现 build_messages()'),
    num('output_db.py 注册表 DDL → _DOMAIN_TABLE_MAP'),
    num('generator.py 注册 → _DOMAIN_PROMPT_MAP'),
    num('Checker 自动适配 → 无需额外代码'),
    p('→ 新 Domain 即刻可用，**生成 + 审查全链路自动打通**'),
    spacer(),

    h2('1.4 测试目标'),
    table(['目标', '说明'],
      [['生态系统端到端有效性', '验证 生成→聚类→审查 全链路自动化运转'],
       ['架构可扩展性', '验证新 Domain 可零代码接入全链路'],
       ['审查流程效率', '验证 Checker 自动化审查对人力的节省效果'],
       ['LLM 合成数据质量', '确保各 Domain 生成 Query 质量达标'],
       ['聚类调优效果', '验证 9 轮参数调优后噪声率和准确率达标'],
       ['场景适配完整性', '验证谷歌数据多维度改写无遗漏'],
       ['系统稳定性', '验证并发生成、断点续传、失败重试的可靠性']],
      [3000, 6360]),

    h1('2. 测试范围'),
    h2('2.2 测试范围矩阵'),
    table(['模块', '单元测试', '集成测试', '数据质量测试', '压力测试'],
      [['5 个 Domain Prompt', '✅', '—', '✅', '—'],
       ['generator.py (自动合成)', '—', '✅', '✅', '✅'],
       ['checker.py (统一审查)', '—', '✅', '✅', '—'],
       ['聚类参数调优', '—', '✅', '✅', '—'],
       ['谷歌场景适配', '—', '✅', '✅', '—'],
       ['端到端全链路', '—', '✅', '✅', '—']],
      [2600, 1300, 1300, 1800, 1300]),

    h1('3. 测试策略'),
    h2('3.1 生态系统端到端测试策略'),
    p('核心测试策略是验证**生成→聚类→审查**的一条龙闭环：Prompt 设计 → LLM 批量生成 → 聚类分析 → Checker 审查 → 反馈 Prompt 优化。'),

    h2('3.2 LLM 数据合成质量测试策略'),
    p('全量生成规则：**1 个类别 30 条 Query（10 通用 + 10 显性个性化 + 10 隐性个性化）**'),
    h3('阶段一：Prompt 约束内嵌'),
    bullet('**三类型结构约束**: 每类别严格 10+10+10'),
    bullet('**字段合规约束**: data_fields 从预定义目录选取'),
    bullet('**人设一致性约束**: query 与 persona 属性匹配'),
    bullet('**知识主题锚定**: query 围绕指定 topic 生成'),
    h3('阶段二：Checker 自动审查（核心流程价值）'),
    bullet('自动读取任意 Domain 的 Prompt 约束作为审查标准'),
    bullet('抽样 100 条即可定位主要问题类型（等效数小时人工审查）'),
    bullet('6 维度缺陷分类 + 三维度聚合报告 → 直接指导 Prompt 优化'),
    bullet('**新 Domain 零额外代码即可审查**'),
    h3('阶段三：聚类验证'),
    p('对数据进行聚类后通过 LLM 逐簇验证主题一致性，作为第二重质量保障。'),

    h2('3.3 聚类参数调优策略'),
    p('本人负责聚类参数的系统性调优，共执行 **9 轮实验**，探索 6 个参数维度：'),
    table(['版本', 'n_comp', 'min_dist', 'min_clust', 'min_samp', 'eps', '簇数', '噪声率'],
      [['初始', '64', '0.0', '5', '3', '0.03', '2,054', '~30%'],
       ['方案A', '64', '0.05', '3', '1', '0.06', '3,595', '~16%'],
       ['**v1**', '**64**', '**0.0**', '**3**', '**1**', '**0.08**', '**1,899**', '**~8%**'],
       ['v2', '12', '0.12', '3', '1', '0.18', '883', '~5%'],
       ['**v3**', '**12**', '**0.0**', '**3**', '**1**', '**0.08**', '**1,823**', '**~8%**']],
      [900, 1100, 1100, 1300, 1300, 900, 1100, 1100]),
    spacer(),

    h2('3.4 谷歌数据多维度场景适配策略'),
    p('改写**不是机械的关键词替换**，而是从 5 个维度审视竞品生态语境后的语义等价适配：'),
    table(['维度', '审视角度'],
      [['品牌生态绑定', '识别与 Google/Fitbit 产品绑定的表述'],
       ['AI 功能命名', '竞品 AI 功能 vs 华为对应功能的差异'],
       ['专有指标体系', '分析竞品独有指标的定义与计算逻辑，映射通用/华为指标'],
       ['健康评估模型', '理解竞品评估模型含义，找到华为生态等价概念'],
       ['隐含场景语境', 'LLM 辅助识别非直接命名的竞品关联场景']],
      [2400, 6960]),

    h1('4. 测试设计'),
    h2('4.1 端到端全链路测试用例'),
    table(['用例ID', '测试点', '验证方法', '通过标准'],
      [['E2E-001', '生成→审查闭环', '对任一 Domain 生成后立即 Checker 审查', '报告自动生成'],
       ['E2E-002', '新 Domain 接入', '新建 prompt + 注册后运行生成+审查', '零额外代码全链路打通'],
       ['E2E-003', '审查→优化闭环', 'Checker 发现问题后修改 Prompt 重新生成', '正常率提升'],
       ['E2E-004', '聚类→审查交叉验证', '对同一数据集分别用聚类和 Checker 验证', '两种方法问题互补']],
      [1200, 2200, 3400, 2560]),

    h2('4.2 各 Domain Prompt 生成测试用例'),
    table(['用例ID', 'Domain', 'Prompt 文件', '验证方法'],
      [['DP-001', 'general_medical', 'prompts/general_medical.py', '生成 ~500 条，Checker 抽样审查'],
       ['DP-002', 'health', 'prompts/health.py', '生成 ~500 条，验证 topic_count 多子域'],
       ['DP-003', 'sports', 'prompts/sports.py', '验证 LLM 内联 persona 质量'],
       ['DP-004', 'sports_health', 'prompts/sports_health.py', '验证跨域 persona 适配'],
       ['DP-005', 'red_team', 'prompts/red_team.py', '验证 4 类攻击覆盖'],
       ['DP-006', '新 Domain', '新建 prompt 文件', '零代码接入全链路']],
      [1000, 1800, 3000, 3560]),

    h2('4.3 批量生成数据完整性用例'),
    table(['用例ID', '测试点', '验证方法'],
      [['DI-001', '知识目录', '220 类 × 30 条 = 6,600'],
       ['DI-002', '运动板块', '1,043 类（160 单项 + 883 跨项）× 30 = 31,290'],
       ['DI-003', '健康板块', '377 类（C13,1 + C13,2 + C13,3）× 30 = 11,310'],
       ['DI-004', '类型均衡', '通用:显性:隐性 = 10:10:10 严格均衡'],
       ['DI-005', '去重效果', '49,200 → 48,895（去重率 0.62%）']],
      [1200, 2000, 6160]),

    h1('5. 测试环境'),
    table(['环境项', '配置'],
      [['OS', 'Linux / Windows'], ['Python', '3.10+ (via uv)'], ['数据库', 'SQLite 3.x'],
       ['LLM API', 'deepseek-v3.2 (OpenAI-compatible)'], ['并发框架', 'asyncio + semaphore'],
       ['聚类工具', 'UMAP + HDBSCAN (CLI)'], ['审查模型', '同 LLM API，temperature=0.3']],
      [2400, 6960]),

    h1('6. 风险与缓解'),
    table(['风险', '缓解措施'],
      [['LLM 输出不稳定', 'Checker 自动审查 + 温度控制(0.3)'],
       ['API 限流/超时', '指数退避重试 + checkpoint 断点续传'],
       ['数据字段幻觉', 'Prompt 硬约束 + Checker 格式违规检测'],
       ['聚类大簇', '参数调优（v1/v3）+ 二次聚类'],
       ['新 Domain 质量不稳', 'Checker 自适应审查，首轮即定位问题']],
      [2800, 6560]),
  ];
}

// ─── Doc 2: 模型性能测试报告 ───
function buildDoc2() {
  return [
    new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: 'AI 数据自动化生态系统', font: FONT })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: '模型性能测试报告', font: FONT, size: 28, bold: true, color: '555555' })] }),
    ...meta('v4.0', '2026-03-27', '健康查询数据自动化生成-聚类-审查生态系统'),
    spacer(),

    h1('1. 测试概述'),
    h2('1.1 系统定位'),
    p('本人围绕已有的健康查询基准数据库，构建了一套**端到端 AI 数据自动化生态系统**，核心能力是：'),
    num('Prompt 驱动的多 Domain 数据合成：5 个独立 Domain，各有专属 Prompt 模板，各约 500 条，可持续生成扩展'),
    num('多源数据清洗与场景适配：谷歌数据 5 维度生态改写 + 现网数据分类抽样'),
    num('统一质量审查闭环：Checker 自适应任意 Domain，抽样即定位问题，反馈 Prompt 优化'),

    h2('1.2 数据成果总览'),
    table(['数据来源', '数量', '特性'],
      [['LLM 自动合成（3 大板块 + 5 个 Domain）', '49,200 + 各 Domain ~500', '结构化，三维度类型体系'],
       ['谷歌数据场景适配', '4,170→7,424', '5 维度生态改写'],
       ['现网数据分类抽样', '589,289→4,111', '真实长尾数据'],
       ['**合计**', '**56,319** (去重后)', '**多源异构**']],
      [3600, 2800, 2960]),

    h1('2. 多 Domain Prompt 生成性能'),
    h2('2.1 Domain 可插拔架构'),
    p('每个 Domain 拥有**独立的 Prompt 模板文件**，是独立的数据生成维度：'),
    table(['Domain', 'Prompt 文件', '人设来源', '规模', '特色能力'],
      [['general_medical', 'prompts/general_medical.py', 'benchmark.db (过滤)', '~500', '100+ 数据字段目录硬约束'],
       ['health', 'prompts/health.py', 'benchmark.db (过滤)', '~500', 'topic_count 多子域支持'],
       ['sports', 'prompts/sports.py', 'LLM 内联生成', '~500', '无需外部 persona'],
       ['sports_health', 'prompts/sports_health.py', 'benchmark.db (全量)', '~500', '跨域健康+运动融合'],
       ['red_team', 'prompts/red_team.py', '无人设', '~500', '4 类攻击维度']],
      [1800, 2400, 1800, 800, 2560]),

    h2('2.2 批量生成板块性能'),
    table(['板块', '类别类型', '标签数量', '生成规则', 'Query 总数'],
      [['知识目录', '树状知识节点', '220', '30 条/类', '6,600'],
       ['运动', '单项(160)+跨项(883)', '1,043', '30 条/类', '31,290'],
       ['健康', 'C(13,1)+C(13,2)+C(13,3)', '377', '30 条/类', '11,310'],
       ['**合计**', '', '**1,640**', '', '**49,200**']],
      [1600, 2400, 1400, 1400, 1400]),
    p('**去重效果**: 49,200 → 48,895（损失仅 0.62%），验证了三维度类型设计的去重有效性'),

    h2('2.3 三维度 Query 类型分布'),
    p('每个类别严格生成 10 通用 + 10 显性个性化 + 10 隐性个性化：'),
    bullet('**通用**: 不涉及个人数据'),
    bullet('**显性个性化**: 直接意图涉及个人数据'),
    bullet('**隐性个性化**: 隐含意图涉及个人数据'),
    p('分布均衡度 = 1:1:1（100% 严格均衡）'),

    h1('3. Checker 自动审查机制与闭环优化'),
    new Paragraph({ spacing: { before: 80, after: 80 }, indent: { left: 240 }, children: [
      new TextRun({ text: '说明：', bold: true, font: FONT, size: 20, color: '666666', italics: true }),
      new TextRun({ text: '本章展示的审查结果为小样本抽样（100 条），目的不在于给出统计意义上的质量结论，而是验证审查机制本身的有效性——即 Checker 能否在极少样本下快速定位问题类型、高风险主题，并直接指导 Prompt 迭代优化。这套机制可零代码应用于任意 Domain、任意规模的数据。', font: FONT, size: 20, color: '666666', italics: true }),
    ]}),

    h2('3.1 审查机制的核心设计'),
    p('Checker 是本生态系统的**质量闭环引擎**，核心价值不在于审查多少条数据，而在于：'),
    num('自动读取 Domain Prompt 约束 → 生成审查标准'),
    num('小样本抽样审查 → 快速定位问题类型和高风险主题'),
    num('结构化报告（三维聚合）→ 直接映射 Prompt 优化方向'),
    num('修改 Prompt → 重新生成 → 再审查 → 正常率持续提升'),

    h2('3.2 机制效率对比'),
    table(['对比项', '传统人工审查', 'Checker 自动审查'],
      [['审查 100 条耗时', '数小时', '数分钟'],
       ['新 Domain 接入', '编写专用审查规则', '零代码自适应'],
       ['审查标准一致性', '依赖审查人员经验', '自动与 Prompt 约束同步'],
       ['报告结构化程度', '自由文本', '三维度自动聚合'],
       ['优化方向指引', '模糊', '直接映射 Prompt 修改点'],
       ['可扩展性', '人力线性增长', '任意 Domain/规模复用']],
      [2800, 3280, 3280]),

    h2('3.3 机制验证：general_medical 抽样审查示例'),
    p('以下为 general_medical Domain 的**小样本抽样审查示例**（100 条），用于验证审查机制的缺陷发现能力。'),
    p('**配置**: 随机抽样 100 条，分 4 批审查（batch_size=30），temperature=0.3'),
    h3('总体结果'),
    table(['指标', '值'],
      [['抽样审查数', '100 条（从全量中随机抽取）'],
       ['正常 Query', '81 条 (81.0%)'],
       ['标记有问题', '19 条 (19.0%)']],
      [2400, 6960]),

    h3('机制验证一：按 Query 类型定位问题分布'),
    table(['Query 类型', '审查数', '问题数', '问题率', '机制定位结论'],
      [['专业知识 Query', '34', '6', '17.6%', '术语专业度需按 persona 背景控制'],
       ['用户数据查询 Query', '33', '9', '**27.3%**', '**类型标注边界需在 Prompt 中强化**'],
       ['知识计算 Query', '33', '3', '**9.1%**', '质量最稳定，Prompt 可作为标杆']],
      [2200, 1000, 1000, 1000, 4160]),

    h3('机制验证二：按知识主题定位高风险区域'),
    table(['知识主题', '问题率', '机制定位结论'],
      [['运动损伤预防与康复', '4/15 (26.7%)', '**最高风险，需优先优化**'],
       ['有氧训练与心肺功能提升', '3/14 (21.4%)', '术语专业度偏高'],
       ['运动营养与能量补给策略', '3/15 (20.0%)', '部分 query 主题偏移'],
       ['睡眠与运动恢复的关系', '2/12 (16.7%)', '可接受'],
       ['运动心率区间与训练强度管理', '2/14 (14.3%)', '可接受'],
       ['体脂管理与运动减脂效率', '2/15 (13.3%)', '可接受'],
       ['力量训练原则与肌肉恢复', '2/15 (13.3%)', '可接受']],
      [3200, 1600, 4560]),

    h3('机制验证三：问题类型 → Prompt 优化方向'),
    table(['问题类型', '数量', '占比', 'Prompt 优化方向'],
      [['语言不自然', '9', '47.4%', '→ 增加术语层次控制，与 persona 背景匹配'],
       ['类型不匹配', '6', '31.6%', '→ 强化三种 Query 类型的边界定义'],
       ['逻辑矛盾', '3', '15.8%', '→ 加强 query 与主题的锚定约束'],
       ['重复/相似', '1', '5.3%', '→ 增加多样性约束']],
      [1600, 800, 800, 6160]),

    h2('3.4 审查机制结论'),
    table(['结论', '说明'],
      [['**小样本即有效**', '100 条抽样即清晰定位 3 类主要问题和 1 个高风险主题'],
       ['**问题→优化直接映射**', '每类问题直接对应 Prompt 具体修改方向'],
       ['**任意 Domain 可复现**', '同样机制即时应用于 health/sports/red_team 等任意 Domain'],
       ['**闭环持续优化**', '审查 → Prompt 修改 → 重新生成 → 再审查 → 正常率持续提升'],
       ['**人力成本极低**', '一次审查数分钟，替代数小时人工逐条检查']],
      [2800, 6560]),

    h1('4. 谷歌数据场景适配报告'),
    h2('4.1 多维度适配（非机械替换）'),
    table(['维度', '审视角度', '适配示例'],
      [['品牌生态', '产品绑定表述', 'Fitbit → Huawei Watch'],
       ['AI 功能命名', '竞品 vs 华为 AI 功能差异', 'Fitbit LLM → Huawei Assistant'],
       ['专有指标体系', '分析指标定义与计算逻辑', 'Active Zone Minutes → Intensity Activity Minutes'],
       ['评估模型差异', '找到华为生态等价概念', 'Readiness Score → Recovery Status'],
       ['隐含场景语境', 'LLM 辅助识别隐含竞品关联', '睡眠算法描述 → 华为睡眠监测场景']],
      [1800, 3000, 4560]),

    h1('5. 现网数据抽样报告'),
    table(['指标', '值'],
      [['原始数据池', '589,289 条'], ['分类抽样', '221 类 × 20 条/类'],
       ['实际抽样', '4,111 条'], ['满额类别', '88.7% (196/221)']],
      [2400, 6960]),
    p('覆盖领域：健康管理（睡眠/饮食/环境）、医疗症状（高血压/糖尿病/孕产）、大众运动（跑步/健身/瑜伽）、心理健康（焦虑/抑郁/正念）等。'),

    h1('6. 结论'),
    h2('6.1 综合评价'),
    table(['维度', '评价', '等级'],
      [['生态系统完整性', '生成→审查全链路自动化闭环', '优秀'],
       ['架构可扩展性', '5 个 Domain 各有独立 Prompt，新 Domain 零代码接入', '优秀'],
       ['审查机制有效性', '小样本即定位问题，直接映射 Prompt 优化方向', '优秀'],
       ['数据合成质量', '去重率 0.62%，三维度类型 1:1:1 均衡', '良好'],
       ['审查效率', '100 条/数分钟，替代数小时人工审查', '优秀'],
       ['场景适配', '5 维度生态改写，非机械替换', '良好']],
      [2200, 5160, 1000]),

    h2('6.2 闭环优化路径'),
    num('术语层次控制 → 语言不自然(47.4%)问题下降 → 正常率提升'),
    num('类型边界强化 → 类型不匹配(31.6%)问题下降'),
    num('主题锚定加强 → 逻辑矛盾(15.8%)问题下降'),
    num('各 Domain 全覆盖审查 → 利用同一机制建立全局质量基线'),
  ];
}

// ─── Doc 3: 优化分析文档 ───
function buildDoc3() {
  return [
    new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: 'AI 数据自动化生态系统', font: FONT })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: '优化分析文档', font: FONT, size: 28, bold: true, color: '555555' })] }),
    ...meta('v3.0', '2026-03-27', '健康查询数据自动化生成-聚类-审查生态系统'),
    spacer(),

    h1('1. 优化概述'),
    p('本文档记录本人围绕已有健康查询基准数据库，构建端到端 AI 数据自动化生态系统过程中的全部优化工作。系统的核心价值是**生成 → 聚类 → 审查的一条龙自动化数据管理能力**。'),
    p('**生态系统数据全景**:'),
    bullet('LLM 自动合成: 49,200 条（1,640 类 × 30 条）+ 5 个 Domain 各约 500 条'),
    bullet('谷歌数据场景适配: 4,170 → 7,424 条'),
    bullet('现网数据分类抽样: 589,289 → 4,111 条'),
    bullet('总计: 56,319 条多源异构数据'),

    h1('2. Prompt 工程优化'),
    h2('2.1 三维度 Query 类型体系'),
    p('**问题**: 单一类型 query 无法覆盖不同个性化层次。'),
    p('**优化方案**: 每类别生成 10 通用 + 10 显性个性化 + 10 隐性个性化 = 30 条'),
    p('**效果**: 49,200 条类型分布 1:1:1 严格均衡，去重率仅 0.62%'),

    h2('2.2 运动 Sparse 组合策略'),
    p('**问题**: 仅单项运动无法覆盖多运动场景。'),
    p('**优化方案**: 单项(160) + 基于运动科学类间关系的跨项组合(883) = 1,043 标签'),
    p('**效果**: 31,290 条运动 query，覆盖有氧+力量、球类跨项等真实多运动场景'),

    h2('2.3 健康特征组合数学'),
    p('**问题**: 单指标 query 无法覆盖多指标关联的复杂健康查询。'),
    p('**优化方案**: 13 个基础健康特征 → C(13,1) + C(13,2) + C(13,3) = 377 标签'),
    p('**效果**: 11,310 条健康 query，双/三特征组合占比 96.5%'),

    h2('2.4 数据字段目录硬约束'),
    p('**问题**: LLM"字段幻觉"——生成不在目录中的虚假健康数据字段。'),
    p('**优化方案**: 在 `general_medical.py` 中定义 100+ 数据字段目录，嵌入 SYSTEM_PROMPT 硬约束。'),
    p('**效果**: Checker "格式违规" 缺陷率显著下降'),

    h2('2.5 五个 Domain 独立 Prompt 体系'),
    p('**问题**: 不同数据维度需要差异化的生成策略。'),
    table(['Domain', 'Prompt 文件', '独特设计'],
      [['general_medical', 'prompts/general_medical.py', '100+ 数据字段目录硬约束'],
       ['health', 'prompts/health.py', 'topic_count 多子域主题'],
       ['sports', 'prompts/sports.py', 'LLM 内联 persona（无需外部人设）'],
       ['sports_health', 'prompts/sports_health.py', '跨域 persona 健康+运动融合'],
       ['red_team', 'prompts/red_team.py', '4 类独立攻击维度']],
      [2000, 3000, 4360]),
    p('**效果**: 每个 Domain 各约 500 条，可独立持续生成，互不影响'),

    h2('2.6 Checker 审查驱动的 Prompt 迭代'),
    table(['Checker 发现', '占比', 'Prompt 优化方向'],
      [['语言不自然', '47.4%', '约束术语层次与 persona 背景匹配'],
       ['类型不匹配', '31.6%', '强化三种 Query 类型的边界定义'],
       ['逻辑矛盾', '15.8%', '加强 query 与指定主题的锚定'],
       ['重复/相似', '5.3%', '增加多样性约束']],
      [2000, 1200, 6160]),
    p('**闭环价值**: 审查 → 定位问题 → 修改 Prompt → 重新生成 → 再审查 → 正常率持续提升'),

    h1('3. 谷歌数据多维度场景适配优化'),
    p('谷歌数据集中的 query 深度嵌入 Google/Fitbit 生态，**不能简单做关键词替换**，需要从多个维度理解竞品生态语境。'),
    h2('3.2 五维度审视角度'),
    table(['维度', '审视角度', '分析与适配'],
      [['品牌生态绑定', '识别产品绑定表述', 'Fitbit → Huawei Watch，确保逻辑自洽'],
       ['AI 功能命名', '区分 AI 功能差异', 'Fitbit LLM → Huawei Assistant'],
       ['专有指标体系', '分析指标定义与计算逻辑', 'AZM → Intensity Activity Minutes'],
       ['健康评估模型', '找到等价概念', 'Readiness Score → Recovery Status'],
       ['隐含场景语境', 'LLM 辅助发现隐含关联', '睡眠算法 → 华为睡眠监测场景']],
      [1800, 2400, 5160]),
    p('**效果**: 4,170 条 → 7,424 条，5 个维度系统性适配'),

    h1('4. UMAP+HDBSCAN 聚类参数调优'),
    p('本人在团队提供的聚类框架基础上，负责参数的系统性调优。目标是在**噪声率、簇数量、簇粒度**三者之间找到最优平衡。'),
    h2('4.2 调优全过程（9 轮实验）'),
    table(['阶段', '关键调整', '结果', '发现'],
      [['初始基线', 'eps=0.03, min_samples=3', '2,054簇, ~30%噪声', '噪声过多'],
       ['降噪探索A', 'eps↑0.06, min_samples↓1', '3,595簇, ~16%噪声', 'min_samples=1 是关键'],
       ['v1 (推荐)', 'min_dist=0.0, eps=0.08', '1,899簇, ~8%噪声', '最佳高维方案'],
       ['v2', 'n_comp=12, eps=0.18', '883簇, ~5%噪声', '大簇需细分'],
       ['v3 (推荐)', 'n_comp=12, min_dist=0.0', '1,823簇, ~8%噪声', '低维均衡方案']],
      [1600, 2600, 2600, 2560]),

    h2('4.3 参数影响规律'),
    table(['参数', '降低 →', '增加 →'],
      [['epsilon', '更多噪声', '更少噪声'],
       ['min_samples', '更少噪声', '更多噪声'],
       ['min_cluster_size', '更少噪声', '更多噪声'],
       ['min_dist', '点聚集，边界模糊', '点分散，识别清晰']],
      [2400, 3280, 3280]),

    h2('4.5 调优成果'),
    table(['指标', '优化前', '优化后', '改进'],
      [['噪声率', '~30%', '~8%', '**-73%**'],
       ['全局准确率', '—', '67.2%', '基线建立']],
      [2000, 2400, 2400, 2560]),

    h1('5. 统一审查框架优化'),
    p('面对 49,200+ 条生成数据 + 5 个独立 Domain，传统人工逐条审查完全不可行。'),
    p('**核心优化**: Checker 自动从 `_DOMAIN_PROMPT_MAP` 读取任意 Domain 的 Prompt 约束，注入审查 prompt：'),
    bullet('**零配置审查**: 任意 Domain 注册后即可审查'),
    bullet('**约束自动同步**: 审查标准与 Prompt 约束一致'),
    bullet('**抽样定位**: 100 条即定位主要问题'),
    bullet('**结构化报告**: 按类型/主题/问题三维聚合'),

    h1('6. 架构可扩展性优化'),
    p('**Domain 可插拔设计** — 新增任何数据维度的边际成本趋近于零：'),
    num('prompts/ 新建 prompt 文件'),
    num('output_db.py 注册表 DDL'),
    num('generator.py 注册映射'),
    num('Checker 自动适配'),
    p('→ **全链路自动打通: 生成 → 聚类 → 审查**'),
    table(['优化项', '方案', '效果'],
      [['并发生成', 'asyncio + semaphore', '支持 49,200 条大批量'],
       ['断点续传', 'checkpoint 机制', '中断后 <5s 恢复'],
       ['指数退避', '2s→30s cap', 'API 限流自动恢复'],
       ['失败记录', 'failed_tasks 表', '异常完整可溯']],
      [2000, 3000, 4360]),

    h1('7. 优化效果总结'),
    table(['指标', '初始/优化前', '最终/优化后', '改进'],
      [['聚类噪声率', '~30%', '~8%', '**-73%**'],
       ['聚类全局准确率', '—', '67.2%', '基线建立'],
       ['LLM 去重损失率', '—', '0.62%', '极低'],
       ['运动类别覆盖', '单项 160', '单项+组合 1,043', '**+552%**'],
       ['健康类别覆盖', '单特征 13', '单+双+三 377', '**+2,800%**'],
       ['新 Domain 接入成本', '数百行代码', '1 prompt + 2 行注册', '**趋近于零**'],
       ['新 Domain 审查成本', '编写审查规则', '零代码自适应', '**-100%**'],
       ['Checker 正常率', '—', '81%', '首轮即定位']],
      [2200, 2200, 2400, 2560]),

    h1('附录 A. 能力对照表'),
    table(['能力描述项', '本项目对应工作', '关键数据'],
      [['训练数据预处理', 'Persona 清洗；现网 589,289 条分类抽样', '4,111 条抽样'],
       ['数据合成', '5 Domain 独立 Prompt 驱动 LLM 自动合成', '49,200 + 各~500'],
       ['数据增强', '运动 Sparse 组合、健康组合数学', '+552%~2800%'],
       ['数据自动标注', 'query_type 自动标注、聚类标签', '1:1:1 均衡'],
       ['数据清洗', 'Checker 审查 + 谷歌适配 + 去重', '81%，0.62%'],
       ['特征分析', '聚类质量分布、Checker 三维问题分布', '67.2%'],
       ['Prompt 数据处理', '5 Domain Prompt + 可插拔架构', '零代码接入'],
       ['知识解析加工切片', '220 知识节点、13 健康特征组合', '1,640 类'],
       ['数据加噪', 'red_team 4 类攻击 Prompt', '~500 条'],
       ['Beta/线上清洗', '谷歌 5 维度场景适配', '4,170→7,424'],
       ['聚类参数调优', 'UMAP+HDBSCAN 9 轮调优', '30%→8%'],
       ['端到端自动化', '生成→聚类→审查一条龙', '全链路']],
      [2000, 4400, 2960]),
  ];
}

// ─── Generate all 3 docs ───
async function generate() {
  const configs = [
    { name: '测试策略与测试设计文档', builder: buildDoc1 },
    { name: '模型性能测试报告', builder: buildDoc2 },
    { name: '优化分析文档', builder: buildDoc3 },
  ];

  for (const { name, builder } of configs) {
    const doc = new Document({
      styles,
      numbering,
      sections: [{
        properties: { page: { margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 } } },
        footers: { default: makeFooter() },
        children: builder(),
      }]
    });
    const buffer = await Packer.toBuffer(doc);
    const outPath = path.join(__dirname, `${name}.docx`);
    fs.writeFileSync(outPath, buffer);
    console.log(`✅ ${name}.docx`);
  }
}

generate().catch(console.error);
