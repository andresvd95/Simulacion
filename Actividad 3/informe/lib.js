// Utilidades para construir el informe en Word (docx-js).
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
  TableCell, WidthType, BorderStyle, ShadingType, ImageRun, Footer, PageNumber,
  LevelFormat,
} = require("docx");

const FONT = "Times New Roman";
const MONO = "Courier New";
const LINE = 360; // interlineado 1.5
const TEXT_W = 9360; // ancho útil: carta con márgenes de 1 pulgada (DXA)

// Marcado en línea: **negrita**, *cursiva*, _{subíndice}, ^{superíndice}
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|_\{[^}]+\}|\^\{[^}]+\})/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (t.startsWith("*")) out.push(new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, ...base }));
    else if (t.startsWith("_{")) out.push(new TextRun({ text: t.slice(2, -1), subScript: true, font: FONT, ...base }));
    else out.push(new TextRun({ text: t.slice(2, -1), superScript: true, font: FONT, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}

const P = (text, opts = {}) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE, after: 60 },
    indent: opts.noIndent ? undefined : { firstLine: 360 },
    children: runs(text, { size: 22 }),
  });

const H1 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    keepNext: true,
    spacing: { before: 240, after: 120, line: 276 },
    children: [new TextRun({ text, bold: true, font: FONT, size: 24 })],
  });

const H2 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_2,
    keepNext: true,
    spacing: { before: 180, after: 80, line: 276 },
    children: [new TextRun({ text, bold: true, italics: true, font: FONT, size: 22 })],
  });

const BUL = (items) =>
  items.map(
    (t) =>
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        alignment: AlignmentType.JUSTIFIED,
        spacing: { line: LINE, after: 20 },
        children: runs(t, { size: 22 }),
      })
  );

const EQ = (text) =>
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 100, after: 100, line: 276 },
    children: runs(text, { size: 22 }),
  });

const CAP = (text) =>
  new Paragraph({
    alignment: AlignmentType.CENTER,
    keepNext: false,
    spacing: { before: 60, after: 160, line: 240 },
    children: runs(text, { size: 18 }),
  });

const CAP_TOP = (text) =>
  new Paragraph({
    alignment: AlignmentType.CENTER,
    keepNext: true,
    spacing: { before: 160, after: 60, line: 240 },
    children: runs(text, { size: 18 }),
  });

const CODE = (lines) =>
  lines.map(
    (l, i) =>
      new Paragraph({
        spacing: { line: 240, after: 0 },
        indent: { left: 280 },
        keepNext: i < lines.length - 1,
        shading: { type: ShadingType.CLEAR, fill: "F3F3F3" },
        children: [new TextRun({ text: l === "" ? " " : l, font: MONO, size: 16 })],
      })
  );

function TABLE(headers, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (text, w, head, idx) =>
    new TableCell({
      width: { size: w, type: WidthType.DXA },
      borders,
      margins: { top: 40, bottom: 40, left: 80, right: 80 },
      shading: head ? { type: ShadingType.CLEAR, fill: "E8E8E8" } : undefined,
      children: [
        new Paragraph({
          alignment: idx === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
          spacing: { line: 240, after: 0 },
          children: runs(String(text), { size: 17, bold: head }),
        }),
      ],
    });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true, i)) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false, i)) })),
    ],
  });
}

function FIG(path, widthIn, caption) {
  const buf = fs.readFileSync(path);
  const w = buf.readUInt32BE(16);
  const h = buf.readUInt32BE(20);
  const wpx = Math.round(widthIn * 96);
  const hpx = Math.round((wpx * h) / w);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      keepNext: true,
      spacing: { before: 120, after: 40, line: 240 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: hpx },
        altText: { title: caption.slice(0, 60), description: caption, name: "figura" } })],
    }),
    CAP(caption),
  ];
}

function buildDocument(children) {
  return new Document({
    creator: "",
    features: { updateFields: true },
    title: "Simulación de las cajas del Banco de Colombia",
    styles: {
      default: { document: { run: { font: FONT, size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 24, bold: true }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font: FONT, size: 22, bold: true, italics: true }, paragraph: { spacing: { before: 180, after: 80 }, keepNext: true, outlineLevel: 1 } },
      ],
    },
    numbering: {
      config: [{
        reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 540, hanging: 270 } } } }],
      }],
    },
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      footers: {
        default: new Footer({
          children: [new Paragraph({ alignment: AlignmentType.CENTER,
            children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })] })],
        }),
      },
      children,
    }],
  });
}

module.exports = { P, H1, H2, BUL, EQ, CAP, CAP_TOP, CODE, TABLE, FIG, runs, buildDocument, Packer, Paragraph, TextRun, AlignmentType, TEXT_W, FONT };
