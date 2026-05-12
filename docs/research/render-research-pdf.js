const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const root = path.resolve(__dirname, "..", "..");
const mdPath = path.join(__dirname, "research.md");
const htmlPath = path.join(__dirname, "research.html");
const pdfPath = path.join(__dirname, "research.pdf");

const chromeCandidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\EdgeCore\\148.0.3967.54\\msedge.exe",
];

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[`*_]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}

function inlineMarkdown(text) {
  const code = [];
  let escaped = escapeHtml(text).replace(/`([^`]+)`/g, (_, value) => {
    code.push(`<code>${value}</code>`);
    return `@@CODE${code.length - 1}@@`;
  });

  escaped = escaped
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/&lt;(https?:\/\/.+?)&gt;/g, (_, url) => {
      const href = url.replace(/&amp;/g, "&");
      return `<a href="${href}">${url}</a>`;
    })
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2">$1</a>');

  return escaped.replace(/@@CODE(\d+)@@/g, (_, index) => code[Number(index)]);
}

function isTableStart(lines, index) {
  return (
    lines[index] &&
    lines[index].trim().startsWith("|") &&
    lines[index + 1] &&
    /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1])
  );
}

function splitTableRow(line) {
  const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

function renderTable(rows) {
  const header = splitTableRow(rows[0]);
  const bodyRows = rows.slice(2).map(splitTableRow);
  return [
    '<div class="table-wrap"><table>',
    "<thead><tr>",
    ...header.map((cell) => `<th>${inlineMarkdown(cell)}</th>`),
    "</tr></thead>",
    "<tbody>",
    ...bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join("")}</tr>`),
    "</tbody></table></div>",
  ].join("");
}

function renderList(items) {
  const parsed = items.map((item) => {
    const match = /^(\s*)([-*]|\d+\.)\s+(.+)$/.exec(item);
    return {
      indent: match[1].length,
      ordered: /\d+\./.test(match[2]),
      text: match[3],
    };
  });

  function renderLevel(start, indent) {
    const tag = parsed[start].ordered ? "ol" : "ul";
    const parts = [`<${tag}>`];
    let current = start;

    while (current < parsed.length) {
      const item = parsed[current];
      if (item.indent < indent) break;
      if (item.indent > indent) {
        const child = renderLevel(current, item.indent);
        parts.push(child.html);
        current = child.next;
        continue;
      }

      parts.push(`<li>${inlineMarkdown(item.text)}`);
      current += 1;

      if (current < parsed.length && parsed[current].indent > indent) {
        const child = renderLevel(current, parsed[current].indent);
        parts.push(child.html);
        current = child.next;
      }

      parts.push("</li>");
    }

    parts.push(`</${tag}>`);
    return { html: parts.join(""), next: current };
  }

  return renderLevel(0, parsed[0].indent).html;
}

function parseBlocks(lines, toc) {
  const html = [];
  let sectionOpen = false;
  let index = 0;

  function closeSection() {
    if (sectionOpen) {
      html.push("</section>");
      sectionOpen = false;
    }
  }

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    const heading = /^(#{1,4})\s+(.+)$/.exec(trimmed);
    if (heading) {
      const level = heading[1].length;
      const text = heading[2].trim();
      const id = slugify(text);

      if (level === 1) {
        index += 1;
        continue;
      }

      if (level === 2) {
        closeSection();
        sectionOpen = true;
        toc.push({ id, text });
        html.push(`<section id="${id}"><h2 class="section-title">${inlineMarkdown(text)}</h2>`);
      } else {
        html.push(`<h${level} id="${id}">${inlineMarkdown(text)}</h${level}>`);
      }
      index += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const quoteLines = [];
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        quoteLines.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      html.push(`<div class="source">${parseBlocks(quoteLines, []).join("")}</div>`);
      continue;
    }

    if (isTableStart(lines, index)) {
      const rows = [];
      while (index < lines.length && lines[index].trim().startsWith("|")) {
        rows.push(lines[index]);
        index += 1;
      }
      html.push(renderTable(rows));
      continue;
    }

    if (/^\s*(?:[-*]|\d+\.)\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\s*(?:[-*]|\d+\.)\s+/.test(lines[index])) {
        items.push(lines[index]);
        index += 1;
      }
      html.push(renderList(items));
      continue;
    }

    const paragraph = [trimmed];
    index += 1;
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,4})\s+/.test(lines[index].trim()) &&
      !lines[index].trim().startsWith(">") &&
      !isTableStart(lines, index) &&
      !/^\s*(?:[-*]|\d+\.)\s+/.test(lines[index])
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
  }

  closeSection();
  return html;
}

function buildHtml(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const titleLine = lines.find((line) => line.startsWith("# "));
  const title = titleLine ? titleLine.replace(/^#\s+/, "").trim() : "Research";
  const toc = [];
  const body = parseBlocks(lines, toc).join("\n");
  const nav = toc.map((item) => `<a href="#${item.id}">${inlineMarkdown(item.text)}</a>`).join("\n");

  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    :root {
      --bg: #f7f8f3;
      --page: #ffffff;
      --ink: #20241c;
      --muted: #626b5a;
      --line: #dfe5d5;
      --accent: #5d7d1f;
      --accent-dark: #31550f;
      --accent-soft: #eef5df;
      --warning-bg: #fff7df;
      --shadow: 0 18px 50px rgba(32, 36, 28, 0.08);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard", "Noto Sans KR", sans-serif;
      line-height: 1.72;
      word-break: keep-all;
    }
    a { color: var(--accent-dark); text-decoration: none; overflow-wrap: anywhere; }
    a:hover { text-decoration: underline; }
    .layout {
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      min-height: 100vh;
    }
    aside {
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
      background: #fbfcf7;
      border-right: 1px solid var(--line);
      padding: 28px 22px;
    }
    .brand { margin-bottom: 26px; }
    .eyebrow {
      color: var(--accent-dark);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .brand h1 {
      margin: 8px 0 0;
      font-size: 20px;
      line-height: 1.32;
    }
    nav { display: flex; flex-direction: column; gap: 4px; }
    nav a {
      display: block;
      padding: 8px 10px;
      border-radius: 8px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.35;
    }
    nav a:hover {
      background: var(--accent-soft);
      color: var(--accent-dark);
      text-decoration: none;
    }
    main { padding: 44px 28px 72px; }
    .page {
      width: min(1120px, 100%);
      margin: 0 auto;
      background: var(--page);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
      padding: 54px 58px 64px;
    }
    header {
      padding-bottom: 28px;
      border-bottom: 2px solid var(--line);
      margin-bottom: 34px;
    }
    header h2 {
      margin: 10px 0 14px;
      font-size: 42px;
      line-height: 1.15;
    }
    .summary {
      margin: 0;
      color: var(--muted);
      font-size: 17px;
    }
    .source {
      margin: 18px 0;
      padding: 16px 18px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fbfcf8;
      color: var(--muted);
      font-size: 14px;
    }
    section { margin-top: 44px; }
    h2.section-title {
      margin: 0 0 18px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
      font-size: 26px;
      line-height: 1.28;
    }
    h3 {
      margin: 28px 0 12px;
      font-size: 19px;
    }
    p { margin: 0 0 14px; }
    ul, ol { margin: 10px 0 18px 22px; padding: 0; }
    li { margin: 6px 0; }
    code {
      padding: 2px 6px;
      border-radius: 6px;
      background: #eef1e8;
      color: #374127;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 0.92em;
    }
    .table-wrap {
      overflow-x: auto;
      margin: 16px 0 24px;
      border: 1px solid var(--line);
      border-radius: 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
      background: #fff;
    }
    th, td {
      padding: 13px 14px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
      font-size: 14px;
    }
    th {
      background: #f1f6e9;
      color: #263716;
      font-weight: 800;
      white-space: nowrap;
    }
    tr:last-child td { border-bottom: 0; }
    .footer-note {
      margin-top: 40px;
      padding-top: 22px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 14px;
    }
    @media (max-width: 980px) {
      .layout { display: block; }
      aside {
        position: static;
        height: auto;
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }
      nav { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
      main { padding: 20px 12px 48px; }
      .page { border-radius: 12px; padding: 34px 22px 42px; }
      table { min-width: 680px; }
    }
    @media print {
      @page { size: A4; margin: 14mm 12mm; }
      body { background: #fff; }
      .layout { display: block; }
      aside { display: none; }
      main { padding: 0; }
      .page {
        border: 0;
        box-shadow: none;
        padding: 0;
        width: 100%;
      }
      header h2 { font-size: 34px; }
      section { break-inside: avoid; }
      .table-wrap { overflow: visible; break-inside: auto; }
      table { min-width: 0; table-layout: fixed; }
      th, td { font-size: 10.5px; padding: 7px 8px; overflow-wrap: anywhere; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <div class="brand">
        <div class="eyebrow">Lemon Aid</div>
        <h1>${escapeHtml(title)}</h1>
      </div>
      <nav aria-label="문서 목차">
        ${nav}
      </nav>
    </aside>
    <main>
      <article class="page">
        <header>
          <div class="eyebrow">Research Document</div>
          <h2>${escapeHtml(title)}</h2>
          <p class="summary">Lemon Aid 기획, 데이터 설계, AI Agent, OCR/이미지 처리, 알고리즘, UI/UX 판단에 사용한 근거 자료를 팀 검토용으로 정리한 문서입니다.</p>
        </header>
        ${body}
        <p class="footer-note">Source: docs/research/research.md</p>
      </article>
    </main>
  </div>
</body>
</html>`;
}

function fileUrl(filePath) {
  return `file:///${filePath.replace(/\\/g, "/").replace(/ /g, "%20")}`;
}

function findChrome() {
  return chromeCandidates.find((candidate) => fs.existsSync(candidate));
}

const markdown = fs.readFileSync(mdPath, "utf8");
fs.writeFileSync(htmlPath, buildHtml(markdown), "utf8");

const chrome = findChrome();
if (!chrome) {
  console.error("Chrome or Edge executable was not found.");
  process.exit(1);
}

const result = spawnSync(
  chrome,
  [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--disable-extensions",
    `--print-to-pdf=${pdfPath}`,
    "--print-to-pdf-no-header",
    fileUrl(htmlPath),
  ],
  { cwd: root, encoding: "utf8" }
);

if (result.status !== 0) {
  process.stderr.write(result.stderr || result.stdout || "PDF generation failed.");
  process.exit(result.status || 1);
}

console.log(`Wrote ${path.relative(root, htmlPath)}`);
console.log(`Wrote ${path.relative(root, pdfPath)}`);
