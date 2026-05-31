/**
 * AX 데이터팀 표준 회의록 .docx 생성기
 *
 * 사용법:
 *   node tools/generate.js --data <meeting_data.json>
 *
 * meeting_data.json 구조:
 *   { subtitle, date, location, attendees, topic, filename, out_path,
 *     blocks: [
 *       { title, type: 'bullets', subsections: [{ subtitle|null, items: [[text,level], ...] }] },
 *       { title, type: 'numbered', items: [str, ...] },
 *       ... 등장 순서대로
 *     ],
 *     appendix: [str, ...] }
 *
 * - blocks 를 등장 순서 그대로 렌더 → 섹션 순서·제목 자유
 * - 각 섹션 사이에 빈 단락(여백) 삽입
 */

const fs   = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, VerticalAlign,
  LevelFormat
} = require('docx');

// ── 데이터 로드 ──────────────────────────────────────────────
const args = process.argv.slice(2);
const di = args.indexOf('--data');
if (di === -1 || !args[di + 1]) {
  console.error('사용법: node generate.js --data <meeting_data.json>');
  process.exit(1);
}
const D = JSON.parse(fs.readFileSync(args[di + 1], 'utf8'));

// ── 스타일 ───────────────────────────────────────────────────
const FONT = '맑은 고딕';
const cb   = { style: BorderStyle.SINGLE, size: 4, color: '999999' };
const cbs  = { top: cb, bottom: cb, left: cb, right: cb };

const hCell = (text, w = 1800) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders: cbs,
  shading: { fill: 'D5E8F0', type: ShadingType.CLEAR },
  verticalAlign: VerticalAlign.CENTER,
  margins: { top: 100, bottom: 100, left: 120, right: 120 },
  children: [new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, bold: true, font: FONT, size: 22 })] })]
});
const bCell = (text, w = 7560) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders: cbs,
  verticalAlign: VerticalAlign.CENTER,
  margins: { top: 100, bottom: 100, left: 160, right: 120 },
  children: [new Paragraph({ children: [new TextRun({ text, font: FONT, size: 22 })] })]
});
// 섹션 대제목 — before 여백 넉넉히 (섹션 간 여백 ①)
const secTitle = t => new Paragraph({ spacing: { before: 400, after: 160 },
  children: [new TextRun({ text: t, font: FONT, size: 24, bold: true })] });
const subTitle = t => new Paragraph({ spacing: { before: 160, after: 60 },
  children: [new TextRun({ text: t, font: FONT, size: 22, bold: true })] });
const bullet  = (t, lv = 0) => new Paragraph({
  numbering: { reference: 'bullets', level: lv },
  spacing:   { before: 20, after: 20, line: 300 },
  children:  [new TextRun({ text: t, font: FONT, size: 22 })] });
const numItem = t => new Paragraph({
  numbering: { reference: 'agreed', level: 0 },
  spacing:   { before: 40, after: 40, line: 320 },
  children:  [new TextRun({ text: t, font: FONT, size: 22 })] });
// 섹션 간 여백용 빈 단락 (섹션 간 여백 ②)
const gap = () => new Paragraph({ spacing: { before: 0, after: 120 }, children: [] });

// ── 본문 빌드 ────────────────────────────────────────────────
const children = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: '회 의 록', bold: true, font: FONT, size: 36 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [new TextRun({ text: D.subtitle || '', font: FONT, size: 28 })] }),

  new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [1800, 7560],
    rows: [
      new TableRow({ children: [hCell('회의일시'), bCell(D.date || '')] }),
      new TableRow({ children: [hCell('회의장소'), bCell(D.location || '')] }),
      new TableRow({ children: [hCell('참석자'),   bCell(D.attendees || '')] }),
      new TableRow({ children: [hCell('회의주제'), bCell(D.topic || '')] }),
    ]
  }),
  gap(),
];

// 본문 섹션 — 등장 순서대로 (섹션 순서·제목 자유)
for (const blk of (D.blocks || [])) {
  children.push(secTitle(blk.title));
  if (blk.type === 'numbered') {
    for (const t of (blk.items || [])) children.push(numItem(t));
  } else {
    for (const sub of (blk.subsections || [])) {
      if (sub.subtitle) children.push(subTitle(sub.subtitle));
      for (const [t, lv] of (sub.items || [])) children.push(bullet(t, lv || 0));
    }
  }
  children.push(gap());   // 섹션 사이 여백
}

// 종결부
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 },
  children: [new TextRun({ text: '- 이상 -', font: FONT, size: 22 })] }));

// Appendix (항목이 있을 때만)
if ((D.appendix || []).length) {
  children.push(new Paragraph({ spacing: { before: 200, after: 120 },
    children: [new TextRun({ text: 'Appendix: 첨부 자료', bold: true, font: FONT, size: 22 })] }));
  for (const t of D.appendix) children.push(bullet(t, 0));
}

// ── 문서 생성 ────────────────────────────────────────────────
const doc = new Document({
  styles:   { default: { document: { run: { font: FONT, size: 22 } } } },
  numbering:{ config: [
    { reference: 'bullets', levels: [
      { level: 0, format: LevelFormat.BULLET, text: '○', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 360, hanging: 280 } } } },
      { level: 1, format: LevelFormat.BULLET, text: '-',  alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 280 } } } },
      { level: 2, format: LevelFormat.BULLET, text: '·',  alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 1080, hanging: 280 } } } },
    ]},
    { reference: 'agreed', levels: [{
      level: 0, format: LevelFormat.DECIMAL, text: '%1.',
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 480, hanging: 320 } } }
    }]},
  ]},
  sections: [{ properties: { page: {
    size: { width: 11906, height: 16838 },
    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
  }}, children }]
});

Packer.toBuffer(doc).then(buf => {
  const outPath = D.out_path || path.join(__dirname, '..', 'outputs', D.filename || 'minutes.docx');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  console.log('OK:' + outPath);
});
