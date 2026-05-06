import fs from "node:fs";
import path from "node:path";

const rootDir = path.resolve(process.cwd(), "src");
const targetExt = new Set([".js", ".ts", ".vue"]);
const forbiddenPatterns = [
  {
    name: "toISOString().slice(0, 10)",
    regex: /toISOString\(\)\.slice\(\s*0\s*,\s*10\s*\)/g,
  },
  {
    name: "toISOString().split('T')[0]",
    regex: /toISOString\(\)\.split\(\s*['"]T['"]\s*\)\s*\[\s*0\s*\]/g,
  },
];

const violations = [];

const walk = (dir) => {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath);
      continue;
    }
    const ext = path.extname(entry.name);
    if (!targetExt.has(ext)) continue;
    const content = fs.readFileSync(fullPath, "utf8");
    const lines = content.split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      for (const pattern of forbiddenPatterns) {
        if (pattern.regex.test(line)) {
          violations.push({
            file: fullPath,
            line: i + 1,
            pattern: pattern.name,
            text: line.trim(),
          });
        }
        pattern.regex.lastIndex = 0;
      }
    }
  }
};

if (!fs.existsSync(rootDir)) {
  console.error(`src directory not found: ${rootDir}`);
  process.exit(1);
}

walk(rootDir);

if (violations.length > 0) {
  console.error("UTC日付変換の禁止パターンを検出しました。formatISODateを使用してください。");
  for (const v of violations) {
    console.error(`- ${v.file}:${v.line} [${v.pattern}] ${v.text}`);
  }
  process.exit(1);
}

console.log("UTC日付変換の禁止パターンは検出されませんでした。");
