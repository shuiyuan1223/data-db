const fs = require('fs');
const path = require('path');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        ShadingType, VerticalAlign, LevelFormat, PageNumber } = require(path.join(__dirname, '..', '.claude', 'skills', 'docx', 'node_modules', 'docx'));

const FONT = '微软雅黑';
const ACCENT = '2B579A';

const styles = {
  default: { document: { run: { font: FONT, size: 21, color: '333333' } } },
  paragraphStyles: [
    { id: 'Title', name: 'Title', basedOn: 'Normal',
      run: { size: 36, bold: true, color: '1a1a1a', font: FONT },
      paragraph: { spacing: { before: 120, after: 200 }, alignment: AlignmentType.CENTER } },
    { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 30, bold: true, color: ACCENT, font: FONT },
      paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
    { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 26, bold: true, color: '1a1a1a', font: FONT },
      paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
    { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 23, bold: true, color: '444444', font: FONT },
      paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
  ]
};

const numbering = { config: [
  { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] },
  { reference: 'nums', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] },
]};

function richRuns(text, size = 21, baseOpts = {}) {
  const runs = [];
  const parts = text.split(/(\*\*.*?\*\*|`[^`]+`)/g);
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith('**') && part.endsWith('**'))
      runs.push(new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, size, ...baseOpts }));
    else if (part.startsWith('`') && part.endsWith('`'))
      runs.push(new TextRun({ text: part.slice(1, -1), font: 'Consolas', size: size - 2, color: '8B0000' }));
    else
      runs.push(new TextRun({ text: part, font: FONT, size, ...baseOpts }));
  }
  return runs;
}

const bdr = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const cb = { top: bdr, bottom: bdr, left: bdr, right: bdr };
const hdrShade = { fill: 'E8EEF4', type: ShadingType.CLEAR };

function parseTable(lines) {
  const rows = [];
  for (const l of lines) {
    const cells = l.trim().split('|').slice(1, -1).map(c => c.trim());
    if (cells.every(c => /^[-:]+$/.test(c))) continue;
    rows.push(cells);
  }
  return rows;
}

function mkTable(rows) {
  if (!rows.length) return null;
  const nc = Math.max(...rows.map(r => r.length));
  const total = 9360;
  const cw = Array(nc).fill(Math.floor(total / nc));
  cw[nc - 1] = total - cw.slice(0, -1).reduce((a, b) => a + b, 0);

  return new Table({
    columnWidths: cw,
    rows: rows.map((row, ri) => new TableRow({
      tableHeader: ri === 0,
      children: Array.from({ length: nc }, (_, ci) => {
        const txt = (row[ci] || '').trim();
        return new TableCell({
          borders: cb, width: { size: cw[ci], type: WidthType.DXA },
          shading: ri === 0 ? hdrShade : undefined,
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ spacing: { before: 30, after: 30 }, children: richRuns(txt, 18, ri === 0 ? { bold: true } : {}) })]
        });
      })
    }))
  });
}

function mdToChildren(md) {
  const lines = md.split('\n');
  const children = [];
  let i = 0;
  let tableBuf = [];
  let inTable = false;
  let inCode = false;
  let codeBuf = [];

  const flushTable = () => {
    if (!tableBuf.length) return;
    const t = mkTable(parseTable(tableBuf));
    if (t) children.push(t);
    tableBuf = []; inTable = false;
  };

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim().startsWith('```')) {
      if (inCode) {
        children.push(new Paragraph({ spacing: { before: 60, after: 60 }, indent: { left: 240 },
          children: [new TextRun({ text: codeBuf.join('\n'), font: 'Consolas', size: 17, color: '555555' })] }));
        codeBuf = []; inCode = false;
      } else {
        flushTable();
        inCode = true;
      }
      i++; continue;
    }
    if (inCode) { codeBuf.push(line); i++; continue; }

    if (line.trim().startsWith('|')) { inTable = true; tableBuf.push(line); i++; continue; }
    if (inTable) flushTable();

    if (line.trim() === '---' || line.trim() === '***' || !line.trim()) { i++; continue; }

    // Title (# )
    const h1m = line.match(/^# (.+)/);
    if (h1m) {
      children.push(new Paragraph({ heading: HeadingLevel.TITLE, children: richRuns(h1m[1].replace(/\*\*/g, ''), 36, { bold: true }) }));
      i++; continue;
    }
    // H1 (## )
    const h2m = line.match(/^## (.+)/);
    if (h2m) {
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: h2m[1].replace(/\*\*/g, ''), font: FONT })] }));
      i++; continue;
    }
    // H2 (### )
    const h3m = line.match(/^### (.+)/);
    if (h3m) {
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: h3m[1].replace(/\*\*/g, ''), font: FONT })] }));
      i++; continue;
    }
    // H3 (#### )
    const h4m = line.match(/^#### (.+)/);
    if (h4m) {
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: h4m[1].replace(/\*\*/g, ''), font: FONT })] }));
      i++; continue;
    }

    // Blockquote
    if (line.trim().startsWith('>')) {
      const txt = line.trim().replace(/^>\s*/, '');
      children.push(new Paragraph({ spacing: { before: 60, after: 60 }, indent: { left: 240 },
        children: richRuns(txt, 20, { italics: true, color: '666666' }) }));
      i++; continue;
    }

    // Numbered list
    const nm = line.match(/^\s*(\d+)\.\s+(.*)/);
    if (nm) {
      children.push(new Paragraph({ numbering: { reference: 'nums', level: 0 }, spacing: { before: 40, after: 40 },
        children: richRuns(nm[2]) }));
      i++; continue;
    }

    // Bullet list
    const bm = line.match(/^\s*[-*+]\s+(.*)/);
    if (bm) {
      children.push(new Paragraph({ numbering: { reference: 'bullets', level: 0 }, spacing: { before: 40, after: 40 },
        children: richRuns(bm[1]) }));
      i++; continue;
    }

    // Regular paragraph
    children.push(new Paragraph({ spacing: { before: 60, after: 60 }, children: richRuns(line.trim()) }));
    i++;
  }
  if (inTable) flushTable();
  return children;
}

async function convert(mdPath) {
  const md = fs.readFileSync(mdPath, 'utf-8');
  const doc = new Document({
    styles, numbering,
    sections: [{
      properties: { page: { margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ text: '— ', font: FONT, size: 18 }),
        new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 }),
        new TextRun({ text: ' —', font: FONT, size: 18 }),
      ]})]})},
      children: mdToChildren(md),
    }]
  });
  const outPath = mdPath.replace('.md', '.docx');
  fs.writeFileSync(outPath, await Packer.toBuffer(doc));
  console.log(`  ✅ ${path.basename(outPath)}`);
}

async function main() {
  const dir = __dirname;
  for (const f of ['测试策略与测试设计文档.md', '模型性能测试报告.md', '优化分析文档.md']) {
    await convert(path.join(dir, f));
  }
}
main().catch(console.error);
